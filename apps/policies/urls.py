from django.urls import path

from apps.policies.views import (
    ApprovalQueueView,
    ApprovalRequestCreateView,
    ApproveRequestView,
    PolicyListView,
    PolicyToggleView,
    RejectRequestView,
)

urlpatterns = [
    path("", PolicyListView.as_view(), name="policy_list"),
    path("<int:pk>/toggle/", PolicyToggleView.as_view(), name="policy_toggle"),
    path("approvals/", ApprovalQueueView.as_view(), name="approval_queue"),
    path("approvals/create/", ApprovalRequestCreateView.as_view(), name="approval_create"),
    path("approvals/<int:pk>/approve/", ApproveRequestView.as_view(), name="approval_approve"),
    path("approvals/<int:pk>/reject/", RejectRequestView.as_view(), name="approval_reject"),
]
