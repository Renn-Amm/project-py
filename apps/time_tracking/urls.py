from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.time_tracking.views import TimeEntryViewSet

router = DefaultRouter()
router.register(r"time-entries", TimeEntryViewSet, basename="time_entries")

urlpatterns = [
    path("", include(router.urls)),
]
