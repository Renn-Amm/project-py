import pytest
from django.test import Client


@pytest.mark.django_db
class TestDashboardPages:
    def test_public_pages_load(self):
        c = Client()
        assert c.get("/").status_code == 200
        assert c.get("/signup/").status_code == 200

    def test_dashboard_login_and_projects_page(self, owner_user, project):
        c = Client()
        # login via django auth
        assert c.login(username=owner_user.email, password="testpass123") is True
        assert c.get("/dashboard/").status_code in (200, 302)
        assert c.get("/dashboard/projects/").status_code == 200
        assert c.get(f"/dashboard/projects/{project.id}/").status_code == 200
        assert c.get("/dashboard/analytics/").status_code == 200
        assert c.get("/dashboard/audit/").status_code == 200
        assert c.get("/dashboard/performance/").status_code == 200
