from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import KycSubmission
from .permissions import IsMerchant, IsReviewer
from .selectors import reviewer_queue_queryset
from .serializers import (
    AccountSerializer,
    DocumentUploadSerializer,
    KycDocumentSerializer,
    KycSubmissionSerializer,
    MerchantSignupSerializer,
    MerchantSubmissionUpdateSerializer,
    NotificationEventSerializer,
    ReviewerQueueItemSerializer,
)
from .state_machine import (
    APPROVED,
    MERCHANT_EDITABLE_STATES,
    MORE_INFO_REQUESTED,
    REJECTED,
    SUBMITTED,
    UNDER_REVIEW,
    ForbiddenTransition,
    InvalidTransition,
    transition_submission,
)


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = MerchantSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = serializer.save()
        return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    def get(self, request):
        return Response(AccountSerializer(request.user).data)


class MerchantSubmissionView(APIView):
    permission_classes = [IsMerchant]

    def get(self, request):
        submission = get_or_create_merchant_submission(request.user)
        return Response(KycSubmissionSerializer(submission, context={"request": request}).data)

    def patch(self, request):
        submission = get_or_create_merchant_submission(request.user)
        ensure_merchant_can_edit(submission)
        serializer = MerchantSubmissionUpdateSerializer(submission, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(KycSubmissionSerializer(submission, context={"request": request}).data)


class MerchantDocumentUploadView(APIView):
    permission_classes = [IsMerchant]

    def post(self, request):
        submission = get_or_create_merchant_submission(request.user)
        ensure_merchant_can_edit(submission)
        serializer = DocumentUploadSerializer(data=request.data, context={"submission": submission})
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(
            KycDocumentSerializer(document, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MerchantSubmitView(APIView):
    permission_classes = [IsMerchant]

    def post(self, request):
        submission = get_or_create_merchant_submission(request.user)
        transition_or_raise(submission, SUBMITTED, request.user)
        return Response(KycSubmissionSerializer(submission, context={"request": request}).data)


class MerchantNotificationListView(APIView):
    permission_classes = [IsMerchant]

    def get(self, request):
        events = request.user.notifications.all()[:50]
        return Response(NotificationEventSerializer(events, many=True).data)


class ReviewerDashboardView(APIView):
    permission_classes = [IsReviewer]

    def get(self, request):
        queue_items = list(reviewer_queue_queryset())
        now = timezone.now()
        queue_ages = [
            (now - item.queue_entered_at).total_seconds()
            for item in queue_items
            if item.queue_entered_at
        ]
        avg_time_seconds = round(sum(queue_ages) / len(queue_ages)) if queue_ages else 0

        seven_days_ago = now - timedelta(days=7)
        decisions = KycSubmission.objects.filter(
            Q(state=APPROVED) | Q(state=REJECTED),
            decided_at__gte=seven_days_ago,
        )
        decision_count = decisions.count()
        approved_count = decisions.filter(state=APPROVED).count()
        approval_rate = round((approved_count / decision_count) * 100, 1) if decision_count else None

        return Response(
            {
                "metrics": {
                    "submissions_in_queue": len(queue_items),
                    "average_time_in_queue_seconds": avg_time_seconds,
                    "approval_rate_last_7_days": approval_rate,
                },
                "queue": ReviewerQueueItemSerializer(queue_items, many=True).data,
            }
        )


class ReviewerSubmissionDetailView(APIView):
    permission_classes = [IsReviewer]

    def get(self, request, submission_id):
        submission = get_reviewer_submission(submission_id)
        return Response(KycSubmissionSerializer(submission, context={"request": request}).data)


class ReviewerTransitionView(APIView):
    permission_classes = [IsReviewer]

    ACTION_TO_STATE = {
        "start_review": UNDER_REVIEW,
        "approve": APPROVED,
        "reject": REJECTED,
        "request_more_info": MORE_INFO_REQUESTED,
    }

    def post(self, request, submission_id):
        submission = get_reviewer_submission(submission_id)
        action = request.data.get("action")
        target_state = request.data.get("target_state") or self.ACTION_TO_STATE.get(action)
        if not target_state:
            raise serializers.ValidationError(
                {"action": ["Use one of: start_review, approve, reject, request_more_info."]}
            )

        reason = request.data.get("reason", "")
        transition_or_raise(submission, target_state, request.user, reason=reason)
        return Response(KycSubmissionSerializer(submission, context={"request": request}).data)


def get_or_create_merchant_submission(merchant):
    submission, _ = KycSubmission.objects.get_or_create(merchant=merchant)
    return submission


def ensure_merchant_can_edit(submission):
    if submission.state not in MERCHANT_EDITABLE_STATES:
        raise serializers.ValidationError(
            {"state": ["Only draft or more_info_requested submissions can be edited."]}
        )


def get_reviewer_submission(submission_id):
    try:
        return (
            KycSubmission.objects.select_related("merchant", "reviewer")
            .prefetch_related("documents")
            .get(id=submission_id)
        )
    except KycSubmission.DoesNotExist as exc:
        raise serializers.ValidationError({"submission_id": ["Submission not found."]}) from exc


def transition_or_raise(submission, target_state, actor, reason=""):
    try:
        return transition_submission(submission, target_state, actor, reason=reason)
    except (InvalidTransition, ForbiddenTransition) as exc:
        raise serializers.ValidationError({"state": [str(exc)]}) from exc
