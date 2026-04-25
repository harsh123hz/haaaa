from django.utils import timezone


DRAFT = "draft"
SUBMITTED = "submitted"
UNDER_REVIEW = "under_review"
APPROVED = "approved"
REJECTED = "rejected"
MORE_INFO_REQUESTED = "more_info_requested"

ALL_STATES = (
    DRAFT,
    SUBMITTED,
    UNDER_REVIEW,
    APPROVED,
    REJECTED,
    MORE_INFO_REQUESTED,
)

LEGAL_TRANSITIONS = {
    DRAFT: {SUBMITTED},
    SUBMITTED: {UNDER_REVIEW},
    UNDER_REVIEW: {APPROVED, REJECTED, MORE_INFO_REQUESTED},
    MORE_INFO_REQUESTED: {SUBMITTED},
    APPROVED: set(),
    REJECTED: set(),
}

REVIEW_QUEUE_STATES = {SUBMITTED, UNDER_REVIEW}
MERCHANT_EDITABLE_STATES = {DRAFT, MORE_INFO_REQUESTED}
REQUIRED_DOCUMENT_TYPES = {"pan", "aadhaar", "bank_statement"}
REQUIRED_SUBMISSION_FIELDS = (
    "personal_name",
    "personal_email",
    "phone",
    "business_name",
    "business_type",
    "expected_monthly_volume_usd",
)


class InvalidTransition(ValueError):
    pass


class ForbiddenTransition(PermissionError):
    pass


def validate_submission_ready(submission):
    missing_fields = [
        field
        for field in REQUIRED_SUBMISSION_FIELDS
        if getattr(submission, field) in ("", None)
    ]
    existing_documents = set(submission.documents.values_list("document_type", flat=True))
    missing_documents = sorted(REQUIRED_DOCUMENT_TYPES - existing_documents)

    if missing_fields or missing_documents:
        details = []
        if missing_fields:
            details.append("missing fields: " + ", ".join(missing_fields))
        if missing_documents:
            details.append("missing documents: " + ", ".join(missing_documents))
        raise InvalidTransition("Submission is not ready to submit; " + "; ".join(details) + ".")


def transition_submission(submission, target_state, actor, reason=""):
    current_state = submission.state
    legal_targets = LEGAL_TRANSITIONS.get(current_state, set())
    if target_state not in legal_targets:
        allowed = ", ".join(sorted(legal_targets)) or "none"
        raise InvalidTransition(
            f"Cannot transition from {current_state} to {target_state}. Legal next states: {allowed}."
        )

    if target_state == SUBMITTED:
        if actor.role != "merchant" or actor.id != submission.merchant_id:
            raise ForbiddenTransition("Only the owning merchant can submit this KYC record.")
        validate_submission_ready(submission)
    elif actor.role != "reviewer":
        raise ForbiddenTransition("Only a reviewer can move this submission through review states.")

    clean_reason = (reason or "").strip()
    if target_state in {APPROVED, REJECTED, MORE_INFO_REQUESTED} and not clean_reason:
        raise InvalidTransition(f"A reason is required when moving to {target_state}.")

    now = timezone.now()
    submission.state = target_state

    if target_state == SUBMITTED:
        submission.submitted_at = now
        submission.queue_entered_at = now
        submission.review_started_at = None
        submission.decided_at = None
        submission.reviewer = None
        submission.review_reason = ""
    elif target_state == UNDER_REVIEW:
        submission.reviewer = actor
        submission.review_started_at = now
    elif target_state in {APPROVED, REJECTED}:
        submission.reviewer = actor
        submission.decided_at = now
        submission.review_reason = clean_reason
    elif target_state == MORE_INFO_REQUESTED:
        submission.reviewer = actor
        submission.review_reason = clean_reason

    submission.save()
    _log_state_notification(submission, current_state, target_state, actor, clean_reason)
    return submission


def _log_state_notification(submission, from_state, to_state, actor, reason):
    from .models import NotificationEvent

    NotificationEvent.objects.create(
        merchant=submission.merchant,
        event_type=f"kyc_{to_state}",
        payload={
            "submission_id": submission.id,
            "from_state": from_state,
            "to_state": to_state,
            "actor": actor.username,
            "reason": reason,
        },
    )
