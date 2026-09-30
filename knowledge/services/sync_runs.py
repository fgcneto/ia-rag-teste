from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from knowledge.models import Project, ProjectSyncRun


ACTIVE_STATUSES = {
    ProjectSyncRun.Status.QUEUED,
    ProjectSyncRun.Status.RUNNING,
}

TERMINAL_STATUSES = {
    ProjectSyncRun.Status.SKIPPED,
    ProjectSyncRun.Status.DONE,
    ProjectSyncRun.Status.FAILED,
    ProjectSyncRun.Status.EXPIRED,
}


@dataclass(frozen=True)
class ReservationResult:
    run: ProjectSyncRun
    created: bool
    reason: str


@dataclass(frozen=True)
class ClaimResult:
    run: ProjectSyncRun
    claimed: bool
    reason: str


def _deadline(now, lease_seconds: int):
    if lease_seconds <= 0:
        raise ValueError("lease_seconds deve ser maior que zero.")

    return now + timedelta(seconds=lease_seconds)


@transaction.atomic
def reserve_project_sync(
    *,
    job_id: int,
    project_id: int,
    force: bool = False,
    lease_seconds: int = 3900,
    now=None,
) -> ReservationResult:
    """
    Reserva exclusivamente um projeto para um SyncJob.

    O lock da linha de Project serializa concorrentes que utilizam
    este serviço. A constraint uq_active_project_sync permanece como
    última linha de defesa no banco.
    """
    now = now or timezone.now()

    project = (
        Project.objects
        .select_for_update()
        .get(pk=project_id)
    )

    # Redelivery/idempotência do mesmo job.
    existing_for_job = (
        ProjectSyncRun.objects
        .filter(
            job_id=job_id,
            project=project,
        )
        .first()
    )

    if existing_for_job is not None:
        return ReservationResult(
            run=existing_for_job,
            created=False,
            reason="existing_for_job",
        )

    active = (
        ProjectSyncRun.objects
        .filter(
            project=project,
            status__in=ACTIVE_STATUSES,
        )
        .order_by("-created_at")
        .first()
    )

    if active is not None:
        if (
            active.lease_expires_at is not None
            and active.lease_expires_at <= now
        ):
            active.status = ProjectSyncRun.Status.EXPIRED
            active.finished_at = now
            active.lease_expires_at = None

            if not active.error:
                active.error = "Lease expirada antes de nova reserva."

            active.save(
                update_fields=[
                    "status",
                    "finished_at",
                    "lease_expires_at",
                    "error",
                    "updated_at",
                ]
            )
        else:
            return ReservationResult(
                run=active,
                created=False,
                reason="active_elsewhere",
            )

    run = ProjectSyncRun.objects.create(
        job_id=job_id,
        project=project,
        status=ProjectSyncRun.Status.QUEUED,
        force=force,
        lease_expires_at=_deadline(now, lease_seconds),
    )

    return ReservationResult(
        run=run,
        created=True,
        reason="created",
    )


@transaction.atomic
def claim_project_sync(
    *,
    run_id: int,
    task_id: str,
    lease_seconds: int = 3900,
    now=None,
) -> ClaimResult:
    """
    Transforma uma reserva QUEUED em RUNNING.

    Também permite recuperar a mesma execução quando um worker anterior
    deixou uma lease RUNNING expirar.
    """
    now = now or timezone.now()

    run = (
        ProjectSyncRun.objects
        .select_for_update()
        .get(pk=run_id)
    )

    if run.status in TERMINAL_STATUSES:
        return ClaimResult(
            run=run,
            claimed=False,
            reason="terminal",
        )

    if (
        run.status == ProjectSyncRun.Status.RUNNING
        and run.lease_expires_at is not None
        and run.lease_expires_at > now
    ):
        return ClaimResult(
            run=run,
            claimed=False,
            reason="already_running",
        )

    recovered = run.status == ProjectSyncRun.Status.RUNNING

    if recovered:
        metadata = dict(run.result_json or {})
        metadata["lease_recovery_count"] = (
            int(metadata.get("lease_recovery_count", 0)) + 1
        )
        run.result_json = metadata

    run.status = ProjectSyncRun.Status.RUNNING
    run.task_id = task_id
    run.lease_expires_at = _deadline(now, lease_seconds)

    if run.started_at is None:
        run.started_at = now

    run.save(
        update_fields=[
            "status",
            "task_id",
            "lease_expires_at",
            "started_at",
            "result_json",
            "updated_at",
        ]
    )

    return ClaimResult(
        run=run,
        claimed=True,
        reason="recovered" if recovered else "claimed",
    )

@transaction.atomic
def finish_project_sync(
    *,
    run_id: int,
    status: str,
    result_json=None,
    error: str | None = None,
    target_sha: str | None = None,
    task_id: str | None = None,
    now=None,
) -> ProjectSyncRun:
    if status not in TERMINAL_STATUSES:
        raise ValueError(
            f"Status terminal inválido: {status}"
        )

    now = now or timezone.now()

    run = (
        ProjectSyncRun.objects
        .select_for_update()
        .get(pk=run_id)
    )

    # Finalização idempotente.
    if run.status in TERMINAL_STATUSES:
        return run

    # Evita que um worker antigo finalize uma execução
    # que já tenha sido recuperada por outro worker.
    if (
        task_id
        and run.task_id
        and run.task_id != task_id
    ):
        raise RuntimeError(
            "ProjectSyncRun pertence a outra task."
        )

    run.status = status
    run.finished_at = now
    run.lease_expires_at = None

    if target_sha:
        run.target_sha = target_sha

    if result_json is not None:
        metadata = dict(run.result_json or {})
        metadata["ingestion"] = result_json
        run.result_json = metadata

    if error is not None:
        run.error = error

    run.save(
        update_fields=[
            "status",
            "finished_at",
            "lease_expires_at",
            "target_sha",
            "result_json",
            "error",
            "updated_at",
        ]
    )

    return run