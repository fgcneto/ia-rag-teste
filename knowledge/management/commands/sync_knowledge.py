from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.utils import timezone

from knowledge.models import SyncJob
from knowledge.tasks import sync_repositories


class Command(BaseCommand):
    help = (
        "Agenda sincronização segura dos "
        "repositórios da allowlist via Celery."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Reindexa mesmo quando "
                "o SHA não mudou."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        job = SyncJob.objects.create(
            status="QUEUED",
            requested_by=(
                "management-command"
            ),
        )

        try:
            result = (
                sync_repositories.delay(
                    job_id=job.pk,
                    force=options["force"],
                )
            )

        except Exception as exc:
            job.status = "FAILED"
            job.error = repr(exc)
            job.finished_at = timezone.now()

            job.save(
                update_fields=[
                    "status",
                    "error",
                    "finished_at",
                ]
            )

            raise CommandError(
                "Não foi possível enviar "
                "a sincronização ao Celery."
            ) from exc

        job.task_id = result.id

        job.save(
            update_fields=[
                "task_id",
            ]
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"SyncJob={job.pk} "
                f"enfileirado "
                f"task_id={result.id}"
            )
        )