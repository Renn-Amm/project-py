from django.urls import path

from apps.feature_flags.evaluation_views import EvaluateView

urlpatterns = [
    path("evaluate/", EvaluateView.as_view(), name="evaluate"),
]
