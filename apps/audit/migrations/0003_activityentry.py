from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0002_rename_audit_audit_organiz_1c5c31_idx_audit_audit_organiz_155e59_idx"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActivityEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("activity_type", models.CharField(choices=[("status_change", "Status Change"), ("time_logged", "Time Logged"), ("review_submitted", "Review Submitted"), ("assignment_changed", "Assignment Changed"), ("task_created", "Task Created"), ("comment_added", "Comment Added")], db_index=True, max_length=30)),
                ("description", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activity_entries", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activity_entries", to="organizations.organization")),
                ("task", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="activity_entries", to="tasks.task")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["organization", "-created_at"], name="activity_org_created_idx"),
                    models.Index(fields=["task", "-created_at"], name="activity_task_created_idx"),
                ],
            },
        ),
    ]
