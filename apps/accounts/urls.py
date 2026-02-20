from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.views import (
    ChangePasswordView,
    InvitationAcceptView,
    InvitationCreateView,
    InvitationListView,
    LogoutView,
    RegisterView,
    UserListView,
    UserProfileView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", UserProfileView.as_view(), name="user_profile"),
    path("users/", UserListView.as_view(), name="user_list"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("invite/", InvitationCreateView.as_view(), name="invitation_create"),
    path("invite/accept/", InvitationAcceptView.as_view(), name="invitation_accept"),
    path("invitations/", InvitationListView.as_view(), name="invitation_list"),
]
