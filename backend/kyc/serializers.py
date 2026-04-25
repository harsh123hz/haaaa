from datetime import timedelta
import uuid

from django.utils import timezone
from rest_framework import serializers

from .models import Account, KycDocument, KycSubmission, NotificationEvent
from .upload_validation import validate_kyc_upload


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "username", "email", "role", "token"]
        read_only_fields = ["id", "role", "token"]


class MerchantSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "username", "email", "token"]
        read_only_fields = ["id", "token"]

    def create(self, validated_data):
        return Account.objects.create(
            **validated_data,
            role=Account.ROLE_MERCHANT,
            token=uuid.uuid4().hex,
        )


class KycDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KycDocument
        fields = [
            "id",
            "document_type",
            "file",
            "original_filename",
            "content_type",
            "size",
            "uploaded_at",
        ]
        read_only_fields = fields


class KycSubmissionSerializer(serializers.ModelSerializer):
    documents = KycDocumentSerializer(many=True, read_only=True)
    merchant_username = serializers.CharField(source="merchant.username", read_only=True)
    reviewer_username = serializers.CharField(source="reviewer.username", read_only=True, default=None)

    class Meta:
        model = KycSubmission
        fields = [
            "id",
            "merchant_username",
            "state",
            "personal_name",
            "personal_email",
            "phone",
            "business_name",
            "business_type",
            "expected_monthly_volume_usd",
            "reviewer_username",
            "review_reason",
            "submitted_at",
            "queue_entered_at",
            "review_started_at",
            "decided_at",
            "created_at",
            "updated_at",
            "documents",
        ]
        read_only_fields = ["id", "merchant_username", "state", "reviewer_username", "review_reason"]


class MerchantSubmissionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KycSubmission
        fields = [
            "personal_name",
            "personal_email",
            "phone",
            "business_name",
            "business_type",
            "expected_monthly_volume_usd",
        ]

    def validate_expected_monthly_volume_usd(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Expected monthly volume must be positive.")
        return value


class DocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=KycDocument.DOCUMENT_TYPE_CHOICES)
    file = serializers.FileField(write_only=True)

    def validate_file(self, file):
        return validate_kyc_upload(file)

    def create(self, validated_data):
        submission = self.context["submission"]
        uploaded_file = validated_data["file"]
        document, created = KycDocument.objects.get_or_create(
            submission=submission,
            document_type=validated_data["document_type"],
            defaults={
                "original_filename": uploaded_file.name,
                "content_type": getattr(uploaded_file, "content_type", ""),
                "size": uploaded_file.size,
            },
        )

        if not created and document.file:
            document.file.delete(save=False)

        document.original_filename = uploaded_file.name
        document.content_type = getattr(uploaded_file, "content_type", "")
        document.size = uploaded_file.size
        document.file.save(uploaded_file.name, uploaded_file, save=False)
        document.save()
        return document


class ReviewerQueueItemSerializer(serializers.ModelSerializer):
    merchant_username = serializers.CharField(source="merchant.username", read_only=True)
    reviewer_username = serializers.CharField(source="reviewer.username", read_only=True, default=None)
    at_risk = serializers.SerializerMethodField()
    age_hours = serializers.SerializerMethodField()

    class Meta:
        model = KycSubmission
        fields = [
            "id",
            "merchant_username",
            "business_name",
            "business_type",
            "expected_monthly_volume_usd",
            "state",
            "reviewer_username",
            "submitted_at",
            "queue_entered_at",
            "age_hours",
            "at_risk",
        ]

    def get_at_risk(self, obj):
        if hasattr(obj, "at_risk"):
            return obj.at_risk
        return bool(obj.queue_entered_at and timezone.now() - obj.queue_entered_at > timedelta(hours=24))

    def get_age_hours(self, obj):
        if not obj.queue_entered_at:
            return 0
        return round((timezone.now() - obj.queue_entered_at).total_seconds() / 3600, 2)


class NotificationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationEvent
        fields = ["id", "event_type", "timestamp", "payload"]
