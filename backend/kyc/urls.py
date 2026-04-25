from django.urls import path

from .views import (
    MeView,
    MerchantDocumentUploadView,
    MerchantNotificationListView,
    MerchantSubmissionView,
    MerchantSubmitView,
    ReviewerDashboardView,
    ReviewerSubmissionDetailView,
    ReviewerTransitionView,
    SignupView,
)


urlpatterns = [
    path("auth/signup/", SignupView.as_view(), name="signup"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("merchant/submission/", MerchantSubmissionView.as_view(), name="merchant-submission"),
    path("merchant/submission/documents/", MerchantDocumentUploadView.as_view(), name="merchant-documents"),
    path("merchant/submission/submit/", MerchantSubmitView.as_view(), name="merchant-submit"),
    path("merchant/notifications/", MerchantNotificationListView.as_view(), name="merchant-notifications"),
    path("reviewer/dashboard/", ReviewerDashboardView.as_view(), name="reviewer-dashboard"),
    path(
        "reviewer/submissions/<int:submission_id>/",
        ReviewerSubmissionDetailView.as_view(),
        name="reviewer-submission-detail",
    ),
    path(
        "reviewer/submissions/<int:submission_id>/transition/",
        ReviewerTransitionView.as_view(),
        name="reviewer-transition",
    ),
]

