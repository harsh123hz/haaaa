from datetime import timedelta

from django.db.models import BooleanField, Case, Value, When
from django.utils import timezone

from .models import KycSubmission
from .state_machine import REVIEW_QUEUE_STATES


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

