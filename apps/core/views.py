from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connection, transaction
from django.shortcuts import redirect, render
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import Organization

User = get_user_model()


class HealthCheckView(APIView):
    """Health check endpoint for load balancers and monitoring."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        health = {"status": "healthy", "checks": {}}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health["checks"]["database"] = "ok"
        except Exception:
            health["checks"]["database"] = "error"
            health["status"] = "unhealthy"

        status_code = 200 if health["status"] == "healthy" else 503
        return Response(health, status=status_code)


def landing_page_view(request):
    return render(request, "public/landing.html")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_home")

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        organization_name = (request.POST.get("organization_name") or "").strip()

        if not email or not password or not organization_name:
            messages.error(
                request, "Email, password, and organization name are required."
            )
            return render(request, "public/signup.html")

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Please enter a valid email address.")
            return render(request, "public/signup.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, "public/signup.html")

        with transaction.atomic():
            organization = Organization.objects.create(name=organization_name)
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role="owner",
                organization=organization,
            )

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("dashboard_home")

    return render(request, "public/signup.html")
