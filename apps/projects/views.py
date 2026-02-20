from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import UserRole
from apps.projects.models import Project, ProjectMember
from apps.projects.serializers import ProjectMemberSerializer, ProjectSerializer


def _require_org(request):
    if not request.user.is_authenticated:
        return None
    return request.user.organization


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        org = _require_org(self.request)
        if not org:
            return Project.objects.none()
        return (
            Project.objects
            .filter(organization=org, memberships__user=self.request.user)
            .select_related("organization", "created_by")
            .distinct()
        )

    def perform_create(self, serializer):
        org = _require_org(self.request)
        serializer.save(organization=org, created_by=self.request.user)
        ProjectMember.objects.get_or_create(project=serializer.instance, user=self.request.user)

    @action(detail=True, methods=["post"], url_path="members")
    def add_member(self, request, pk=None):
        project = self.get_object()
        if request.user.role not in (UserRole.OWNER, UserRole.PROJECT_MANAGER):
            return Response({"error": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)

        if not ProjectMember.objects.filter(project=project, user=request.user).exists():
            return Response({"error": "Not a project member."}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get("user")
        if not user_id:
            return Response({"error": "user is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(
            type(request.user).objects,
            pk=user_id,
            organization=request.user.organization,
        )
        membership, _ = ProjectMember.objects.get_or_create(project=project, user=user)
        return Response(ProjectMemberSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"members/(?P<member_id>[^/.]+)")
    def remove_member(self, request, pk=None, member_id=None):
        project = self.get_object()
        if request.user.role not in (UserRole.OWNER, UserRole.PROJECT_MANAGER):
            return Response({"error": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)

        if not ProjectMember.objects.filter(project=project, user=request.user).exists():
            return Response({"error": "Not a project member."}, status=status.HTTP_403_FORBIDDEN)

        membership = get_object_or_404(
            ProjectMember,
            pk=member_id,
            project=project,
            user__organization=request.user.organization,
        )
        if membership.user_id == request.user.id:
            return Response({"error": "You cannot remove yourself."}, status=status.HTTP_400_BAD_REQUEST)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
