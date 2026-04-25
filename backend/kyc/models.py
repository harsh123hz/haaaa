import uuid

from django.db import models

from .state_machine import ALL_STATES, DRAFT


def generate_token():
    return uuid.uuid4().hex


class Account(models.Model):
    ROLE_MERCHANT = "merchant"
    ROLE_REVIEWER = "reviewer"
    ROLE_CHOICES = (
        (ROLE_MERCHANT, "Merchant"),
        (ROLE_REVIEWER, "Reviewer"),
    )

    username = models.CharField(max_length=80, unique=True)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MERCHANT)
    token = models.CharField(max_length=64, unique=True, default=generate_token)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return f"{self.username} ({self.role})"


class KycSubmission(models.Model):
    STATE_CHOICES = tuple((state, state.replace("_", " ").title()) for state in ALL_STATES)
    BUSINESS_TYPE_CHOICES = (
        ("agency", "Agency"),
        ("freelancer", "Freelancer"),
        ("studio", "Studio"),
        ("other", "Other"),
    )

    merchant = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="kyc_submission")
    state = models.CharField(max_length=32, choices=STATE_CHOICES, default=DRAFT)

    personal_name = models.CharField(max_length=120, blank=True)
    personal_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    business_name = models.CharField(max_length=160, blank=True)
    business_type = models.CharField(max_length=40, choices=BUSINESS_TYPE_CHOICES, blank=True)
    expected_monthly_volume_usd = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    reviewer = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_reviews",
    )
    review_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    queue_entered_at = models.DateTimeField(null=True, blank=True)
    review_started_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"KYC #{self.id} - {self.merchant.username} - {self.state}"


class KycDocument(models.Model):
    TYPE_PAN = "pan"
    TYPE_AADHAAR = "aadhaar"
    TYPE_BANK_STATEMENT = "bank_statement"
    DOCUMENT_TYPE_CHOICES = (
        (TYPE_PAN, "PAN"),
        (TYPE_AADHAAR, "Aadhaar"),
        (TYPE_BANK_STATEMENT, "Bank statement"),
    )

    submission = models.ForeignKey(KycSubmission, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=40, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to="kyc_documents/")
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "document_type"], name="unique_document_per_submission_type"
            )
        ]

    def __str__(self):
        return f"{self.submission_id} - {self.document_type}"


class NotificationEvent(models.Model):
    merchant = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="notifications")
    event_type = models.CharField(max_length=80)
    timestamp = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField(default=dict)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.event_type} for {self.merchant.username}"
