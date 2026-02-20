from django.urls import path

from apps.performance.views import PerformanceScoreView, TeamPerformanceView

urlpatterns = [
    path("score/", PerformanceScoreView.as_view(), name="performance_score"),
    path("team/", TeamPerformanceView.as_view(), name="team_performance"),
]
