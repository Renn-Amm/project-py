from django.db import models


class EvaluationEvent(models.Model):
    flag = models.ForeignKey(
        "feature_flags.FeatureFlag",
        on_delete=models.CASCADE,
        related_name="evaluation_events",
    )
    flag_key = models.CharField(max_length=255, db_index=True)
    user_identifier = models.CharField(max_length=255, db_index=True)
    evaluated_variant = models.JSONField(null=True)
    environment_name = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "analytics_evaluationevent"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["flag_key", "-timestamp"]),
            models.Index(fields=["flag", "environment_name", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.flag_key}:{self.user_identifier} -> {self.evaluated_variant}"
