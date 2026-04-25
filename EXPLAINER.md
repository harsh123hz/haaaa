# EXPLAINER

## 1. The State Machine

The state machine lives in `backend/kyc/state_machine.py`. Views call `transition_submission`; they do not update `submission.state` directly.

```python
LEGAL_TRANSITIONS = {
    DRAFT: {SUBMITTED},
    SUBMITTED: {UNDER_REVIEW},
    UNDER_REVIEW: {APPROVED, REJECTED, MORE_INFO_REQUESTED},
    MORE_INFO_REQUESTED: {SUBMITTED},
    APPROVED: set(),
    REJECTED: set(),
}

def transition_submission(submission, target_state, actor, reason=""):
    current_state = submission.state
    legal_targets = LEGAL_TRANSITIONS.get(current_state, set())
    if target_state not in legal_targets:
        allowed = ", ".join(sorted(legal_targets)) or "none"
        raise InvalidTransition(
            f"Cannot transition from {current_state} to {target_state}. Legal next states: {allowed}."
        )
```

Illegal transitions are rejected before any database write. The API catches `InvalidTransition` and returns a `400` shaped as `{"errors": {"state": ["..."]}}`.

## 2. The Upload

Upload validation lives in `backend/kyc/upload_validation.py` and is called by `DocumentUploadSerializer.validate_file`.

```python
def validate_kyc_upload(uploaded_file):
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise serializers.ValidationError("File must be 5 MB or smaller.")

    extension = Path(uploaded_file.name or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise serializers.ValidationError("Only PDF, JPG, and PNG files are accepted.")

    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    detected_type = _detect_type(header)
    if detected_type is None:
        raise serializers.ValidationError("Only valid PDF, JPG, and PNG files are accepted.")

    expected_type = ALLOWED_EXTENSIONS[extension]
    if detected_type != expected_type:
        raise serializers.ValidationError(
            f"File extension does not match file contents. Expected {expected_type}."
        )
```

A 50 MB file fails on the first check and returns `400` with `File must be 5 MB or smaller.` The code also checks magic bytes, so a renamed executable or fake PDF is rejected even if the browser sends a friendly content type.

## 3. The Queue

The reviewer dashboard queue query lives in `backend/kyc/selectors.py`.

```python
def reviewer_queue_queryset():
    at_risk_cutoff = timezone.now() - timedelta(hours=24)
    return (
        KycSubmission.objects.filter(state__in=REVIEW_QUEUE_STATES)
        .select_related("merchant", "reviewer")
        .prefetch_related("documents")
        .annotate(
            at_risk=Case(
                When(queue_entered_at__lte=at_risk_cutoff, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        .order_by("queue_entered_at", "submitted_at", "id")
    )
```

I wrote it this way so the SLA flag is computed at read time instead of stored. `select_related` and `prefetch_related` keep the dashboard from doing one query per merchant/document, and the ordering makes the queue oldest first.

## 4. The Auth

Auth is token based. The role checks live in `backend/kyc/permissions.py`; merchant endpoints only operate on `request.user`.

```python
def get_or_create_merchant_submission(merchant):
    submission, _ = KycSubmission.objects.get_or_create(merchant=merchant)
    return submission
```

There is no merchant endpoint that accepts a submission id. A merchant can only read or edit the submission attached to the authenticated account from the token. Reviewer endpoints use `IsReviewer`, so merchant tokens cannot access the reviewer queue.

## 5. The AI Audit

Buggy AI draft:

```python
if uploaded_file.content_type not in ["application/pdf", "image/jpeg", "image/png"]:
    raise serializers.ValidationError("Invalid file type")
```

That is insecure because `content_type` is supplied by the client. A caller can upload arbitrary bytes while claiming `application/pdf`.

Replacement:

```python
header = uploaded_file.read(16)
uploaded_file.seek(0)
detected_type = _detect_type(header)
if detected_type is None:
    raise serializers.ValidationError("Only valid PDF, JPG, and PNG files are accepted.")
```

The replacement validates server-side file signatures and checks that the extension matches the detected type.

