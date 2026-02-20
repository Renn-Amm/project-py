import pytest
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import Invitation, User, UserRole


@pytest.mark.django_db
class TestInvitationCreate:
    def test_owner_can_create_invitation(self, authenticated_client, organization):
        resp = authenticated_client.post(
            "/api/auth/invite/",
            {"email": "newmember@test.com", "role": "developer"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["email"] == "newmember@test.com"
        assert resp.data["role"] == "developer"
        assert "token" in resp.data
        assert Invitation.objects.filter(email="newmember@test.com").exists()

    def test_viewer_cannot_create_invitation(self, viewer_client):
        resp = viewer_client.post(
            "/api/auth/invite/",
            {"email": "someone@test.com", "role": "developer"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_invite_existing_member(self, authenticated_client, developer_user):
        resp = authenticated_client.post(
            "/api/auth/invite/",
            {"email": developer_user.email, "role": "developer"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_invite_same_email_twice(self, authenticated_client):
        authenticated_client.post(
            "/api/auth/invite/",
            {"email": "dup@test.com", "role": "developer"},
            format="json",
        )
        resp = authenticated_client.post(
            "/api/auth/invite/",
            {"email": "dup@test.com", "role": "reviewer"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestInvitationAccept:
    def test_accept_valid_invitation(self, authenticated_client, api_client):
        resp = authenticated_client.post(
            "/api/auth/invite/",
            {"email": "accept@test.com", "role": "developer"},
            format="json",
        )
        token = resp.data["token"]

        accept = api_client.post(
            "/api/auth/invite/accept/",
            {"token": token, "password": "strongpass123", "first_name": "Joined", "last_name": "User"},
            format="json",
        )
        assert accept.status_code == status.HTTP_201_CREATED
        assert accept.data["email"] == "accept@test.com"
        assert accept.data["role"] == "developer"

        user = User.objects.get(email="accept@test.com")
        assert user.role == UserRole.DEVELOPER

    def test_cannot_reuse_invitation(self, authenticated_client, api_client):
        resp = authenticated_client.post(
            "/api/auth/invite/",
            {"email": "reuse@test.com", "role": "developer"},
            format="json",
        )
        token = resp.data["token"]

        api_client.post(
            "/api/auth/invite/accept/",
            {"token": token, "password": "strongpass123"},
            format="json",
        )

        reuse = api_client.post(
            "/api/auth/invite/accept/",
            {"token": token, "password": "strongpass123"},
            format="json",
        )
        assert reuse.status_code == status.HTTP_400_BAD_REQUEST

    def test_expired_token_rejected(self, authenticated_client, api_client):
        resp = authenticated_client.post(
            "/api/auth/invite/",
            {"email": "expired@test.com", "role": "developer"},
            format="json",
        )
        token = resp.data["token"]

        # Manually expire the invitation
        invitation = Invitation.objects.get(token=token)
        invitation.expires_at = timezone.now() - timezone.timedelta(hours=1)
        invitation.save(update_fields=["expires_at"])

        accept = api_client.post(
            "/api/auth/invite/accept/",
            {"token": token, "password": "strongpass123"},
            format="json",
        )
        assert accept.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_token_rejected(self, api_client):
        resp = api_client.post(
            "/api/auth/invite/accept/",
            {"token": "bogus-token", "password": "strongpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestInvitationList:
    def test_owner_can_list_invitations(self, authenticated_client):
        authenticated_client.post(
            "/api/auth/invite/",
            {"email": "list1@test.com", "role": "developer"},
            format="json",
        )
        resp = authenticated_client.get("/api/auth/invitations/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1
