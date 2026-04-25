from django.db import migrations, models
import django.db.models.deletion
import kyc.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("username", models.CharField(max_length=80, unique=True)),
                ("email", models.EmailField(blank=True, max_length=254)),
                (
                    "role",
                    models.CharField(
                        choices=[("merchant", "Merchant"), ("reviewer", "Reviewer")],
                        default="merchant",
                        max_length=20,
                    ),
                ),
                ("token", models.CharField(default=kyc.models.generate_token, max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="KycSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("under_review", "Under Review"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("more_info_requested", "More Info Requested"),
                        ],
                        default="draft",
                        max_length=32,
                    ),
                ),
                ("personal_name", models.CharField(blank=True, max_length=120)),
                ("personal_email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("business_name", models.CharField(blank=True, max_length=160)),
                (
                    "business_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("agency", "Agency"),
                            ("freelancer", "Freelancer"),
                            ("studio", "Studio"),
                            ("other", "Other"),
                        ],
                        max_length=40,
                    ),
                ),
                (
                    "expected_monthly_volume_usd",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
                ("review_reason", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("queue_entered_at", models.DateTimeField(blank=True, null=True)),
                ("review_started_at", models.DateTimeField(blank=True, null=True)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "merchant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kyc_submission",
                        to="kyc.account",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_reviews",
                        to="kyc.account",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="NotificationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=80)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("payload", models.JSONField(default=dict)),
                (
                    "merchant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="kyc.account",
                    ),
                ),
            ],
            options={"ordering": ["-timestamp"]},
        ),
        migrations.CreateModel(
            name="KycDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "document_type",
                    models.CharField(
                        choices=[
                            ("pan", "PAN"),
                            ("aadhaar", "Aadhaar"),
                            ("bank_statement", "Bank statement"),
                        ],
                        max_length=40,
                    ),
                ),
                ("file", models.FileField(upload_to="kyc_documents/")),
                ("original_filename", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=120)),
                ("size", models.PositiveIntegerField()),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="kyc.kycsubmission",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="kycdocument",
            constraint=models.UniqueConstraint(
                fields=("submission", "document_type"),
                name="unique_document_per_submission_type",
            ),
        ),
    ]
