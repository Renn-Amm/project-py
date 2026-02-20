import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Invitation, UserRole
from apps.organizations.models import Organization

User = get_user_model()


class SecureTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that includes only safe, minimal claims.
    Never include email, name, or other PII in the token payload.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["organization_id"] = user.organization_id
        return token


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "organization",
            "is_active",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "is_active",
            "organization",
            "role",
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=10)
    organization_name = serializers.CharField(write_only=True, max_length=255)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "organization_name",
        ]
        read_only_fields = ["id"]

    def validate_email(self, value):
        return value.strip().lower()

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        organization_name = validated_data.pop("organization_name")
        organization = Organization.objects.create(name=organization_name)

        validated_data["role"] = "owner"
        validated_data["organization"] = organization
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=10)


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[
            (UserRole.PROJECT_MANAGER, "Project Manager"),
            (UserRole.DEVELOPER, "Developer"),
            (UserRole.REVIEWER, "Reviewer"),
            (UserRole.VIEWER, "Viewer"),
        ]
    )

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        request = self.context["request"]
        org = request.user.organization
        email = attrs["email"]

        # Cannot invite if active (unused, unexpired) invitation exists
        active = Invitation.objects.filter(
            organization=org,
            email=email,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).exists()
        if active:
            raise serializers.ValidationError(
                {"email": "An active invitation already exists for this email."}
            )

        # Cannot invite if user already in org
        if User.objects.filter(email=email, organization=org).exists():
            raise serializers.ValidationError(
                {"email": "This user is already a member of your organization."}
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        org = request.user.organization
        token = secrets.token_urlsafe(48)
        return Invitation.objects.create(
            email=validated_data["email"],
            role=validated_data["role"],
            organization=org,
            token=token,
            created_by=request.user,
            expires_at=timezone.now() + timedelta(hours=48),
        )


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=10)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")

    def validate_token(self, value):
        try:
            invitation = Invitation.objects.select_related("organization").get(token=value)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation token.")

        if not invitation.is_valid:
            if invitation.is_used:
                raise serializers.ValidationError("This invitation has already been used.")
            raise serializers.ValidationError("This invitation has expired.")

        self._invitation = invitation
        return value

    @transaction.atomic
    def create(self, validated_data):
        invitation = self._invitation
        user = User.objects.create_user(
            email=invitation.email,
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=invitation.role,
            organization=invitation.organization,
        )
        invitation.used_at = timezone.now()
        invitation.save(update_fields=["used_at"])
        return user
