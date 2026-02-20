from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    OWNER = "owner", "Owner"
    PROJECT_MANAGER = "project_manager", "Project Manager"
    DEVELOPER = "developer", "Developer"
    REVIEWER = "reviewer", "Reviewer"
    VIEWER = "viewer", "Viewer"


ROLE_HIERARCHY = {
    UserRole.OWNER: 4,
    UserRole.PROJECT_MANAGER: 3,
    UserRole.DEVELOPER: 2,
    UserRole.REVIEWER: 2,
    UserRole.VIEWER: 1,
}


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.OWNER)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.VIEWER,
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @property
    def role_level(self):
        return ROLE_HIERARCHY.get(self.role, 0)

    def has_role_level(self, minimum_role):
        return self.role_level >= ROLE_HIERARCHY.get(minimum_role, 0)


class Invitation(models.Model):
    email = models.EmailField(db_index=True)
    role = models.CharField(max_length=20, choices=UserRole.choices)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_invitation"
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["token", "used_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["organization", "email"], name="uniq_org_email_invitation"),
        ]

    def __str__(self):
        return f"{self.email} invited to {self.organization.name} as {self.role}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired
