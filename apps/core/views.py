from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


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
