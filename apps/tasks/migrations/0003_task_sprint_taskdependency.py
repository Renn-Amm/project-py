from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0002_task_review_approved_at_task_review_approved_by_and_more"),
        ("projects", "0002_sprint"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="sprint",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tasks",
                to="projects.sprint",
            ),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["sprint"], name="tasks_task_sprint_idx"),
        ),
        migrations.CreateModel(
            name="TaskDependency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dependencies", to="tasks.task")),
                ("depends_on", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dependents", to="tasks.task")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("task", "depends_on"), name="uniq_task_dependency"),
                    models.CheckConstraint(
                        check=~models.Q(task=models.F("depends_on")),
                        name="no_self_dependency",
                    ),
                ],
                "indexes": [
                    models.Index(fields=["task"], name="tasks_taskd_task_idx"),
                    models.Index(fields=["depends_on"], name="tasks_taskd_depends_idx"),
                ],
            },
        ),
    ]
