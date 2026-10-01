from dataclasses import dataclass
from datetime import timedelta
from knowledge.services.sync_jobs import finalize_sync_job
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from knowledge.models import ProjectSyncRun, SyncJob


SCHEDULED_REQUESTED_BY = "celery-beat"

ACTIVE_JOB_STATUSES = {
    SyncJob.Status.QUEUED,
    SyncJob.Status.RUNNING,
}

ACTIVE_RUN_STATUSES = {
    ProjectSyncRun.Status.QUEUED,
    ProjectSyncRun.Status.RUNNING,
}


@dataclass(frozen=True)
class ScheduledSyncReservation:
    job: SyncJob
    created: bool
    reason: str


def _active_scheduled_job(*, for_update=False):
    queryset = SyncJob.objects.filter(
        requested_by=SCHEDULED_REQUESTED_BY,
        status__in=ACTIVE_JOB_STATUSES,
    )

    if for_update:
        queryset = queryset.select_for_update()

    return queryset.order_by("-created_at").first()


def _recover_stale_job(
    job,
    *,
    now,
    stale_after_seconds,
):
    reference_at = job.started_at or job.created_at

    cutoff = now - timedelta(
        seconds=stale_after_seconds,
    )

    if reference_at > cutoff:
        return False

    live_run_exists = job.project_runs.filter(
        status__in=ACTIVE_RUN_STATUSES,
        lease_expires_at__gt=now,
    ).exists()

    if live_run_exists:
        return False

    stale_runs = job.project_runs.filter(
        status__in=ACTIVE_RUN_STATUSES,
        lease_expires_at__lte=now,
    )

    stale_runs.update(
        status=ProjectSyncRun.Status.EXPIRED,
        finished_at=now,
        lease_expires_at=None,
        error=(
            "Lease expirada durante recuperação "
            "do SyncJob agendado."
        ),
        updated_at=now,
    )

    payload = dict(job.result_json or {})

    payload["stale_recovery"] = {
        "recovered_at": now.isoformat(),
        "stale_after_seconds": stale_after_seconds,
    }

    job.status = SyncJob.Status.FAILED
    job.finished_at = now
    job.result_json = payload

    if not job.error:
        job.error = (
            "SyncJob agendado recuperado após "
            "timeout operacional."
        )

    job.save(
        update_fields=[
            "status",
            "finished_at",
            "result_json",
            "error",
        ]
    )

    return True


@transaction.atomic
def reserve_scheduled_sync_job(
    *,
    now=None,
    stale_after_seconds=None,
):
    now = now or timezone.now()

    if stale_after_seconds is None:
        stale_after_seconds = int(
            settings.KNOWLEDGE_SYNC_STALE_AFTER_SECONDS
        )

    if stale_after_seconds <= 0:
        raise ValueError(
            "stale_after_seconds deve ser maior que zero."
        )

    active = _active_scheduled_job(
        for_update=True,
    )
    if active is not None:
        reference_at = (
            active.started_at
            or active.created_at
        )

        cutoff = now - timedelta(
            seconds=stale_after_seconds,
        )

        if reference_at <= cutoff:
            finalize_sync_job(
                active.id,
                now=now,
            )

            active.refresh_from_db()

            if active.status not in ACTIVE_JOB_STATUSES:
                active = None

    if active is not None:
        recovered = _recover_stale_job(
            active,
            now=now,
            stale_after_seconds=stale_after_seconds,
        )

        if not recovered:
            return ScheduledSyncReservation(
                job=active,
                created=False,
                reason="active_job",
            )

    try:
        with transaction.atomic():
            job = SyncJob.objects.create(
                status=SyncJob.Status.QUEUED,
                requested_by=SCHEDULED_REQUESTED_BY,
            )

    except IntegrityError:
        active = _active_scheduled_job()

        if active is None:
            raise

        return ScheduledSyncReservation(
            job=active,
            created=False,
            reason="active_job",
        )

    return ScheduledSyncReservation(
        job=job,
        created=True,
        reason=(
            "recovered_stale_job"
            if active is not None
            else "created"
        ),
    )