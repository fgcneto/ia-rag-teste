from collections import Counter

from django.db import transaction
from django.utils import timezone

from knowledge.models import ProjectSyncRun, SyncJob


TERMINAL_STATUSES = {
    ProjectSyncRun.Status.SKIPPED,
    ProjectSyncRun.Status.DONE,
    ProjectSyncRun.Status.FAILED,
    ProjectSyncRun.Status.EXPIRED,
}

SUCCESS_STATUSES = {
    ProjectSyncRun.Status.SKIPPED,
    ProjectSyncRun.Status.DONE,
}

FAILURE_STATUSES = {
    ProjectSyncRun.Status.FAILED,
    ProjectSyncRun.Status.EXPIRED,
}


@transaction.atomic
def finalize_sync_job(
    job_id: int,
    now=None,
) -> SyncJob:
    now = now or timezone.now()

    job = (
        SyncJob.objects
        .select_for_update()
        .get(pk=job_id)
    )

    payload = dict(job.result_json or {})

    # Um child pode terminar enquanto o orquestrador
    # ainda está criando os outros ProjectSyncRun.
    if not payload.get("dispatch_complete"):
        return job

    runs = list(
        job.project_runs.only(
            "id",
            "status",
        )
    )

    if any(
        run.status not in TERMINAL_STATUSES
        for run in runs
    ):
        return job

    counts = Counter(
        run.status
        for run in runs
    )

    dispatch_errors = payload.get(
        "dispatch_errors",
        [],
    )

    success_count = sum(
        counts.get(status, 0)
        for status in SUCCESS_STATUSES
    )

    failure_count = (
        sum(
            counts.get(status, 0)
            for status in FAILURE_STATUSES
        )
        + len(dispatch_errors)
    )

    if failure_count == 0:
        final_status = "DONE"
    elif success_count == 0:
        final_status = "FAILED"
    else:
        final_status = "PARTIAL"

    payload["status_counts"] = dict(counts)

    job.status = final_status
    job.finished_at = now
    job.result_json = payload

    job.save(
        update_fields=[
            "status",
            "finished_at",
            "result_json",
        ]
    )

    return job