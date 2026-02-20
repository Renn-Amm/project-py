from django.core.management.base import BaseCommand

from apps.tasks.services import OverdueDetectionService


class Command(BaseCommand):
    help = "Mark tasks as overdue when deadline has passed and task is not completed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            type=int,
            default=None,
            help="Optional organization id to scope overdue detection.",
        )

    def handle(self, *args, **options):
        organization_id = options.get("organization_id")
        updated = OverdueDetectionService.mark_overdue_tasks(organization_id=organization_id)
        self.stdout.write(self.style.SUCCESS(f"Marked {updated} task(s) as overdue."))
