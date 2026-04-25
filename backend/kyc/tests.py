from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Account, KycDocument, KycSubmission
from .state_machine import APPROVED, DRAFT, SUBMITTED


class KycTransitionTests(APITestCase):
    def setUp(self):
        self.merchant = Account.objects.create(
            username="merchant_a",
            email="merchant@example.com",
            role=Account.ROLE_MERCHANT,
            token="merchant-token",
        )
        self.reviewer = Account.objects.create(
            username="reviewer",
            email="reviewer@example.com",
            role=Account.ROLE_REVIEWER,
            token="reviewer-token",
        )

    def test_reviewer_gets_clear_400_for_illegal_approved_to_approved_transition(self):
        submission = KycSubmission.objects.create(
            merchant=self.merchant,
            state=APPROVED,
            personal_name="Asha Merchant",
            personal_email="merchant@example.com",
            phone="+91 90000 00000",
            business_name="Asha Studio",
            business_type="studio",
            expected_monthly_volume_usd=5000,
            decided_at=timezone.now(),
        )

        self.client.credentials(HTTP_AUTHORIZATION="Token reviewer-token")
        response = self.client.post(
            f"/api/v1/reviewer/submissions/{submission.id}/transition/",
            {"action": "approve", "reason": "Already checked"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot transition from approved to approved", str(response.data))

    def test_merchant_cannot_submit_without_required_documents(self):
        KycSubmission.objects.create(
            merchant=self.merchant,
            state=DRAFT,
            personal_name="Asha Merchant",
            personal_email="merchant@example.com",
            phone="+91 90000 00000",
            business_name="Asha Studio",
            business_type="studio",
            expected_monthly_volume_usd=5000,
        )

        self.client.credentials(HTTP_AUTHORIZATION="Token merchant-token")
        response = self.client.post("/api/v1/merchant/submission/submit/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("missing documents", str(response.data))

    def test_upload_rejects_extension_mismatch(self):
        submission = KycSubmission.objects.create(merchant=self.merchant, state=DRAFT)
        self.client.credentials(HTTP_AUTHORIZATION="Token merchant-token")
        fake_pdf = SimpleUploadedFile("pan.pdf", b"\xff\xd8\xff\xe0not really a pdf", content_type="application/pdf")

        response = self.client.post(
            "/api/v1/merchant/submission/documents/",
            {"document_type": "pan", "file": fake_pdf},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("extension does not match", str(response.data))

    def test_reviewer_can_start_submitted_review(self):
        submission = KycSubmission.objects.create(
            merchant=self.merchant,
            state=SUBMITTED,
            queue_entered_at=timezone.now(),
            submitted_at=timezone.now(),
        )
        KycDocument.objects.create(
            submission=submission,
            document_type="pan",
            file="kyc_documents/pan.pdf",
            original_filename="pan.pdf",
            content_type="application/pdf",
            size=20,
        )

        self.client.credentials(HTTP_AUTHORIZATION="Token reviewer-token")
        response = self.client.post(
            f"/api/v1/reviewer/submissions/{submission.id}/transition/",
            {"action": "start_review"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["state"], "under_review")

