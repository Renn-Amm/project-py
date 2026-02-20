from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Invitation, UserRole
from apps.accounts.permissions import IsAdminOrAbove
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return User.objects.none()


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrAbove]

    def get_queryset(self):
        if not self.request.user.organization:
            return User.objects.none()
        return User.objects.filter(organization=self.request.user.organization)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"error": "Invalid old password"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"message": "Password changed successfully"})


class LogoutView(APIView):
    """Blacklists the refresh token on logout to prevent reuse."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"error": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Logged out successfully."})


class InvitationCreateView(APIView):
    """Create an invitation. Only Owner or Project Manager can invite."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role not in (UserRole.OWNER, UserRole.PROJECT_MANAGER):
            return Response(
                {"error": "Only Owner or Project Manager can send invitations."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = InvitationCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        return Response(
            {
                "id": invitation.id,
                "email": invitation.email,
                "role": invitation.role,
                "token": invitation.token,
                "expires_at": invitation.expires_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class InvitationAcceptView(APIView):
    """Accept an invitation using the token. Public endpoint."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "organization": user.organization_id,
            },
            status=status.HTTP_201_CREATED,
        )


class InvitationListView(generics.ListAPIView):
    """List invitations for the user's organization."""

    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def get_queryset(self):
        org = getattr(self.request.user, "organization", None)
        if not org:
            return Invitation.objects.none()
        return Invitation.objects.filter(organization=org).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = [
            {
                "id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "is_valid": inv.is_valid,
                "is_used": inv.is_used,
                "is_expired": inv.is_expired,
                "created_at": inv.created_at.isoformat(),
                "expires_at": inv.expires_at.isoformat(),
            }
            for inv in qs[:100]
        ]
        return Response(data)
