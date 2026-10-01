from asgiref.sync import async_to_sync
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from core.ingestion.pipeline import ingest_project
from core.providers.factory import get_source_provider
from knowledge.models import Project, ProjectSyncRun, SyncJob
from knowledge.services.sync_jobs import finalize_sync_job
from knowledge.services.sync_runs import (
    claim_project_sync,
    finish_project_sync,
    reserve_project_sync,
)
from knowledge.services.scheduled_sync import (
    reserve_scheduled_sync_job,
)


LEASE_SECONDS = int(
    getattr(
        settings,
        "CELERY_TASK_TIME_LIMIT",
        3600,
    )
) + 300


def _repository_identity(repo):
    full_name = (
        repo.get("full_name")
        or repo.get("path_with_namespace")
        or ""
    )

    return {
        "full_name": str(full_name),
        "external_id": str(repo.get("id", "")),
        "name": str(
            repo.get("name")
            or full_name
        ),
        "web_url": str(
            repo.get("html_url")
            or repo.get("web_url")
            or ""
        ),
        "default_branch": repo.get(
            "default_branch"
        ),
    }


@shared_task(bind=True)
def sync_project_run(
    self,
    run_id,
):
    task_id = (
        self.request.id
        or f"direct-{run_id}"
    )

    claim = claim_project_sync(
        run_id=run_id,
        task_id=task_id,
        lease_seconds=LEASE_SECONDS,
    )

    run = claim.run

    if not claim.claimed:
        if claim.reason == "terminal":
            finalize_sync_job(
                run.job_id
            )

        return {
            "run_id": run.id,
            "claimed": False,
            "reason": claim.reason,
            "status": run.status,
        }

    try:
        provider = get_source_provider(
            run.project.provider
        )

        result = async_to_sync(
            ingest_project
        )(
            provider,
            run.project,
            force=run.force,
        )

        final_status = (
            ProjectSyncRun.Status.SKIPPED
            if result.unchanged
            else ProjectSyncRun.Status.DONE
        )

        finish_project_sync(
            run_id=run.id,
            status=final_status,
            result_json=result.as_dict(),
            target_sha=result.sha,
            task_id=task_id,
        )

        finalize_sync_job(
            run.job_id
        )

        return {
            "run_id": run.id,
            "claimed": True,
            "status": final_status,
            "result": result.as_dict(),
        }

    except Exception as exc:
        finish_project_sync(
            run_id=run.id,
            status=ProjectSyncRun.Status.FAILED,
            error=repr(exc),
            task_id=task_id,
        )

        finalize_sync_job(
            run.job_id
        )

        raise


@shared_task(bind=True)
def scheduled_sync_tick(self):
    reservation = reserve_scheduled_sync_job()
    job = reservation.job

    if not reservation.created:
        return {
            "job_id": job.id,
            "created": False,
            "dispatched": False,
            "reason": reservation.reason,
            "status": job.status,
        }

    payload = dict(job.result_json or {})

    if self.request.id:
        payload["trigger_task_id"] = self.request.id

        job.result_json = payload
        job.save(
            update_fields=[
                "result_json",
            ]
        )

    try:
        result = sync_repositories.delay(
            job_id=job.id,
            force=False,
        )

    except Exception as exc:
        job.status = SyncJob.Status.FAILED
        job.error = repr(exc)
        job.finished_at = timezone.now()

        job.save(
            update_fields=[
                "status",
                "error",
                "finished_at",
            ]
        )

        raise

    job.task_id = result.id

    job.save(
        update_fields=[
            "task_id",
        ]
    )

    return {
        "job_id": job.id,
        "created": True,
        "dispatched": True,
        "task_id": result.id,
        "reason": reservation.reason,
    }


@shared_task(bind=True)
def sync_repositories(
    self,
    job_id=None,
    force=False,
):
    job = (
        SyncJob.objects.get(pk=job_id)
        if job_id
        else SyncJob.objects.create(
            status="QUEUED"
        )
    )

    current_payload = dict(
        job.result_json or {}
    )

    # Redelivery do próprio orquestrador depois que
    # todos os dispatches já foram concluídos.
    if current_payload.get(
        "dispatch_complete"
    ):
        finalize_sync_job(
            job.id
        )

        job.refresh_from_db()

        return job.result_json

    if (
        job.status in {
            "DONE",
            "PARTIAL",
            "FAILED",
        }
        and job.finished_at
    ):
        return job.result_json

    job.status = "RUNNING"

    if job.started_at is None:
        job.started_at = timezone.now()

    if self.request.id:
        job.task_id = self.request.id

    job.save(
        update_fields=[
            "status",
            "started_at",
            "task_id",
        ]
    )

    provider_name = str(
        settings.SOURCE_PROVIDER
    ).strip().lower()

    try:
        provider = get_source_provider(
            provider_name
        )

        repos = async_to_sync(
            provider.repositories
        )()

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

        raise

    dispatches = []
    dispatch_errors = []

    for repo in repos:
        identity = _repository_identity(
            repo
        )

        full = identity["full_name"]

        if not full:
            dispatch_errors.append({
                "repository": "",
                "error": (
                    "Repositório sem "
                    "identificador."
                ),
            })
            continue

        run = None

        try:
            project, _ = (
                Project.objects
                .update_or_create(
                    path_with_namespace=full,
                    defaults={
                        "provider": (
                            provider_name
                        ),
                        "external_id": (
                            identity[
                                "external_id"
                            ]
                        ),
                        "name": (
                            identity["name"]
                        ),
                        "web_url": (
                            identity["web_url"]
                        ),
                        "default_branch": (
                            identity[
                                "default_branch"
                            ]
                        ),
                        "last_metadata_sync_at": (
                            timezone.now()
                        ),
                        "enabled": True,
                    },
                )
            )

            reservation = (
                reserve_project_sync(
                    job_id=job.id,
                    project_id=project.id,
                    force=force,
                    lease_seconds=(
                        LEASE_SECONDS
                    ),
                )
            )

            if (
                reservation.reason
                == "active_elsewhere"
            ):
                busy_run, _ = (
                    ProjectSyncRun.objects
                    .get_or_create(
                        job=job,
                        project=project,
                        defaults={
                            "status": (
                                ProjectSyncRun
                                .Status
                                .SKIPPED
                            ),
                            "force": force,
                            "finished_at": (
                                timezone.now()
                            ),
                            "result_json": {
                                "reason": (
                                    "active_elsewhere"
                                ),
                                "blocking_run_id": (
                                    reservation
                                    .run
                                    .id
                                ),
                            },
                        },
                    )
                )

                dispatches.append({
                    "repository": full,
                    "run_id": busy_run.id,
                    "dispatched": False,
                    "reason": (
                        "active_elsewhere"
                    ),
                })

                continue

            run = reservation.run

            if run.status in {
                ProjectSyncRun.Status.SKIPPED,
                ProjectSyncRun.Status.DONE,
                ProjectSyncRun.Status.FAILED,
                ProjectSyncRun.Status.EXPIRED,
            }:
                dispatches.append({
                    "repository": full,
                    "run_id": run.id,
                    "dispatched": False,
                    "reason": (
                        reservation.reason
                    ),
                })
                continue

            if (
                run.status
                == ProjectSyncRun.Status.RUNNING
            ):
                dispatches.append({
                    "repository": full,
                    "run_id": run.id,
                    "dispatched": False,
                    "reason": (
                        "already_running"
                    ),
                })
                continue

            # Se uma execução anterior do
            # orquestrador já conseguiu publicar
            # a child task, não publicamos novamente.
            if (
                run.status
                == ProjectSyncRun.Status.QUEUED
                and run.task_id
            ):
                dispatches.append({
                    "repository": full,
                    "run_id": run.id,
                    "task_id": run.task_id,
                    "dispatched": False,
                    "reason": (
                        "already_dispatched"
                    ),
                })
                continue

            try:
                async_result = (
                    sync_project_run.delay(
                        run.id
                    )
                )

            except Exception as exc:
                finish_project_sync(
                    run_id=run.id,
                    status=(
                        ProjectSyncRun
                        .Status
                        .FAILED
                    ),
                    error=(
                        "Falha ao publicar "
                        f"task: {exc!r}"
                    ),
                )

                dispatch_errors.append({
                    "repository": full,
                    "run_id": run.id,
                    "error": repr(exc),
                })

                continue

            # A task já foi publicada. Se houver uma
            # corrida e o worker já tiver feito claim,
            # este UPDATE simplesmente não altera nada.
            (
                ProjectSyncRun.objects
                .filter(
                    pk=run.id,
                    status=(
                        ProjectSyncRun
                        .Status
                        .QUEUED
                    ),
                )
                .update(
                    task_id=async_result.id
                )
            )

            dispatches.append({
                "repository": full,
                "run_id": run.id,
                "task_id": async_result.id,
                "dispatched": True,
            })

        except Exception as exc:
            if (
                run is not None
                and run.status
                == ProjectSyncRun.Status.QUEUED
            ):
                finish_project_sync(
                    run_id=run.id,
                    status=(
                        ProjectSyncRun
                        .Status
                        .FAILED
                    ),
                    error=repr(exc),
                )

            dispatch_errors.append({
                "repository": full,
                "error": repr(exc),
            })

    job.refresh_from_db()

    payload = dict(
        job.result_json or {}
    )

    payload.update({
        "projects_seen": len(repos),
        "dispatch_complete": True,
        "dispatches": dispatches,
        "dispatch_errors": dispatch_errors,
    })

    job.result_json = payload

    job.save(
        update_fields=[
            "result_json",
        ]
    )

    finalize_sync_job(
        job.id
    )

    job.refresh_from_db()

    return job.result_json