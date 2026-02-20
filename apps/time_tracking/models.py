from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class TimeEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="time_entries")
    task = models.ForeignKey("tasks.Task", on_delete=models.CASCADE, related_name="time_entries")
    hours = models.DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(0)])
    date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["task", "date"]),
            models.Index(fields=["user", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.hours}h on {self.task_id}"
