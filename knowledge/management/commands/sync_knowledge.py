from django.core.management.base import BaseCommand

from knowledge.models import SyncJob
from knowledge.tasks import sync_repositories


class Command(BaseCommand):
    help = "Sincroniza metadados e indexa, de forma segura, os repositórios da allowlist."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Reindexa mesmo quando o SHA não mudou.")

    def handle(self, *args, **options):
        job = SyncJob.objects.create(status="QUEUED", requested_by="management-command")
        self.stdout.write(f"SyncJob={job.pk} iniciado")
        result = sync_repositories.run(job_id=job.pk, force=options["force"])
        self.stdout.write(self.style.SUCCESS(str(result)))
