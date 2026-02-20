from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.projects.views import ProjectViewSet, SprintViewSet

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="projects")
router.register(r"sprints", SprintViewSet, basename="sprints")

urlpatterns = [
    path("", include(router.urls)),
]
