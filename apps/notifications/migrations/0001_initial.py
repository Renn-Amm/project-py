from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notification_type", models.CharField(choices=[("task_assigned", "Task Assigned"), ("moved_to_review", "Moved to Review"), ("review_rejected", "Review Rejected"), ("overdue_detected", "Overdue Detected")], db_index=True, max_length=30)),
                ("title", models.CharField(max_length=255)),
                ("message", models.TextField(blank=True)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="organizations.organization")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
                ("related_task", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="tasks.task")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["recipient", "is_read"], name="notif_recipient_read_idx"),
                    models.Index(fields=["organization", "-created_at"], name="notif_org_created_idx"),
                ],
            },
        ),
    ]
