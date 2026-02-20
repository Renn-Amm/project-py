from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Sprint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("goal", models.TextField(blank=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("is_closed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sprints", to="projects.project")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("project", "name"), name="uniq_sprint_project_name"),
                    models.CheckConstraint(
                        check=models.Q(start_date__lt=models.F("end_date")),
                        name="sprint_start_before_end",
                    ),
                ],
                "indexes": [
                    models.Index(fields=["project", "is_closed"], name="projects_sp_project_idx"),
                ],
            },
        ),
    ]
