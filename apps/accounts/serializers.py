from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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
