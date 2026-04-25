from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from kyc.models import Account, KycDocument, KycSubmission
from kyc.state_machine import DRAFT, UNDER_REVIEW


class Command(BaseCommand):
    help = "Seed demo merchants, reviewer, submissions, and sample documents."

    def handle(self, *args, **options):
        draft_merchant = upsert_account(
            username="merchant_draft",
            email="draft@example.com",
            role=Account.ROLE_MERCHANT,
            token="merchant-draft-token",
        )
        review_merchant = upsert_account(
            username="merchant_review",
            email="review@example.com",
            role=Account.ROLE_MERCHANT,
            token="merchant-review-token",
        )
        reviewer = upsert_account(
            username="reviewer_isha",
            email="reviewer@example.com",
            role=Account.ROLE_REVIEWER,
            token="reviewer-token",
        )

        KycSubmission.objects.update_or_create(
            merchant=draft_merchant,
            defaults={
                "state": DRAFT,
                "personal_name": "Anaya Rao",
                "personal_email": "draft@example.com",
                "phone": "+91 90000 00001",
                "business_name": "Draft Creative Co",
                "business_type": "agency",
                "expected_monthly_volume_usd": 4500,
            },
        )

        queued_at = timezone.now() - timedelta(hours=26)
        under_review, _ = KycSubmission.objects.update_or_create(
            merchant=review_merchant,
            defaults={
                "state": UNDER_REVIEW,
                "personal_name": "Dev Mehta",
                "personal_email": "review@example.com",
                "phone": "+91 90000 00002",
                "business_name": "Mehta Motion Studio",
                "business_type": "studio",
                "expected_monthly_volume_usd": 12000,
                "reviewer": reviewer,
                "submitted_at": queued_at,
                "queue_entered_at": queued_at,
                "review_started_at": queued_at + timedelta(hours=1),
            },
        )

        seed_document(under_review, "pan", "pan.pdf", demo_pdf("PAN"))
        seed_document(under_review, "aadhaar", "aadhaar.pdf", demo_pdf("Aadhaar"))
        seed_document(under_review, "bank_statement", "bank_statement.pdf", demo_pdf("Bank statement"))

        self.stdout.write(self.style.SUCCESS("Seeded demo accounts:"))
        self.stdout.write("  merchant_draft / merchant-draft-token")
        self.stdout.write("  merchant_review / merchant-review-token")
        self.stdout.write("  reviewer_isha / reviewer-token")


def upsert_account(username, email, role, token):
    account, _ = Account.objects.update_or_create(
        username=username,
        defaults={"email": email, "role": role, "token": token},
    )
    return account


def seed_document(submission, document_type, filename, content):
    document, _ = KycDocument.objects.get_or_create(
        submission=submission,
        document_type=document_type,
        defaults={
            "original_filename": filename,
            "content_type": content_type_for(filename),
            "size": len(content),
        },
    )
    if document.file:
        document.file.delete(save=False)
    document.original_filename = filename
    document.content_type = content_type_for(filename)
    document.size = len(content)
    document.file.save(filename, ContentFile(content), save=False)
    document.save()


def content_type_for(filename):
    if filename.endswith(".pdf"):
        return "application/pdf"
    if filename.endswith(".png"):
        return "image/png"
    return "image/jpeg"


def demo_pdf(label):
    return f"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n% Demo {label}\n%%EOF\n".encode()
