from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_remove_user_tenant_user_organization_alter_user_role"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Invitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("role", models.CharField(choices=[("owner", "Owner"), ("project_manager", "Project Manager"), ("developer", "Developer"), ("reviewer", "Reviewer"), ("viewer", "Viewer")], max_length=20)),
                ("token", models.CharField(db_index=True, max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_invitations", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invitations", to="organizations.organization")),
            ],
            options={
                "db_table": "accounts_invitation",
                "indexes": [
                    models.Index(fields=["organization", "-created_at"], name="accounts_in_organiz_idx"),
                    models.Index(fields=["token", "used_at"], name="accounts_in_token_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("organization", "email"), name="uniq_org_email_invitation"),
                ],
            },
        ),
    ]
