from dataclasses import dataclass

from django.db import IntegrityError, transaction

from knowledge.models import SyncJob


SCHEDULED_REQUESTED_BY = "celery-beat"

ACTIVE_JOB_STATUSES = {
    SyncJob.Status.QUEUED,
    SyncJob.Status.RUNNING,
}


@dataclass(frozen=True)
class ScheduledSyncReservation:
    job: SyncJob
    created: bool
    reason: str


def _active_scheduled_job():
    return (
        SyncJob.objects
        .filter(
            requested_by=SCHEDULED_REQUESTED_BY,
            status__in=ACTIVE_JOB_STATUSES,
        )
        .order_by("-created_at")
        .first()
    )


@transaction.atomic
def reserve_scheduled_sync_job():
    active = _active_scheduled_job()

    if active is not None:
        return ScheduledSyncReservation(
            job=active,
            created=False,
            reason="active_job",
        )

    try:
        # Savepoint interno.
        #
        # Se duas execuções concorrentes tentarem criar o
        # SyncJob agendado ao mesmo tempo, a constraint do
        # PostgreSQL faz uma delas falhar aqui.
        #
        # O rollback deste bloco restaura a transação externa,
        # permitindo consultar o job vencedor com segurança.
        with transaction.atomic():
            job = SyncJob.objects.create(
                status=SyncJob.Status.QUEUED,
                requested_by=SCHEDULED_REQUESTED_BY,
            )

    except IntegrityError:
        active = _active_scheduled_job()

        if active is None:
            # IntegrityError não relacionado à exclusividade
            # esperada. Não mascarar a falha original.
            raise

        return ScheduledSyncReservation(
            job=active,
            created=False,
            reason="active_job",
        )

    return ScheduledSyncReservation(
        job=job,
        created=True,
        reason="created",
    )
