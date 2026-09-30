from datetime import timedelta

import pytest
from django.utils import timezone

from knowledge.models import Project, ProjectSyncRun, SyncJob
from knowledge.services.sync_runs import (
    claim_project_sync,
    reserve_project_sync,
)


def make_project(name: str) -> Project:
    return Project.objects.create(
        provider=Project.Provider.GITHUB,
        external_id=name,
        path_with_namespace=f"synthetic/{name}",
        name=name,
        web_url=f"https://example.invalid/synthetic/{name}",
        default_branch="main",
        enabled=True,
    )


@pytest.mark.django_db(transaction=True)
def test_reservation_creates_queued_run_with_lease():
    project = make_project("reserve-project")
    job = SyncJob.objects.create(status="RUNNING")

    result = reserve_project_sync(
        job_id=job.id,
        project_id=project.id,
        lease_seconds=600,
    )

    assert result.created is True
    assert result.reason == "created"
    assert result.run.status == ProjectSyncRun.Status.QUEUED
    assert result.run.lease_expires_at is not None


@pytest.mark.django_db(transaction=True)
def test_duplicate_reservation_for_same_job_is_idempotent():
    project = make_project("same-job")
    job = SyncJob.objects.create(status="RUNNING")

    first = reserve_project_sync(
        job_id=job.id,
        project_id=project.id,
    )

    second = reserve_project_sync(
        job_id=job.id,
        project_id=project.id,
    )

    assert first.run.id == second.run.id
    assert second.created is False
    assert second.reason == "existing_for_job"

    assert (
        ProjectSyncRun.objects
        .filter(job=job, project=project)
        .count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_active_run_blocks_other_job():
    project = make_project("active-project")

    first_job = SyncJob.objects.create(status="RUNNING")
    second_job = SyncJob.objects.create(status="RUNNING")

    first = reserve_project_sync(
        job_id=first_job.id,
        project_id=project.id,
    )

    second = reserve_project_sync(
        job_id=second_job.id,
        project_id=project.id,
    )

    assert first.created is True
    assert second.created is False
    assert second.reason == "active_elsewhere"
    assert second.run.id == first.run.id


@pytest.mark.django_db(transaction=True)
def test_expired_run_is_replaced_by_new_reservation():
    project = make_project("expired-project")

    old_job = SyncJob.objects.create(status="RUNNING")
    new_job = SyncJob.objects.create(status="RUNNING")

    past = timezone.now() - timedelta(minutes=5)

    old_run = ProjectSyncRun.objects.create(
        job=old_job,
        project=project,
        status=ProjectSyncRun.Status.RUNNING,
        lease_expires_at=past,
    )

    result = reserve_project_sync(
        job_id=new_job.id,
        project_id=project.id,
    )

    old_run.refresh_from_db()

    assert old_run.status == ProjectSyncRun.Status.EXPIRED
    assert old_run.lease_expires_at is None
    assert old_run.finished_at is not None

    assert result.created is True
    assert result.run.id != old_run.id
    assert result.run.status == ProjectSyncRun.Status.QUEUED


@pytest.mark.django_db(transaction=True)
def test_claim_moves_queued_run_to_running():
    project = make_project("claim-project")
    job = SyncJob.objects.create(status="RUNNING")

    reservation = reserve_project_sync(
        job_id=job.id,
        project_id=project.id,
    )

    result = claim_project_sync(
        run_id=reservation.run.id,
        task_id="synthetic-task-1",
    )

    assert result.claimed is True
    assert result.reason == "claimed"

    result.run.refresh_from_db()

    assert result.run.status == ProjectSyncRun.Status.RUNNING
    assert result.run.task_id == "synthetic-task-1"
    assert result.run.started_at is not None


@pytest.mark.django_db(transaction=True)
def test_valid_running_lease_cannot_be_claimed_again():
    project = make_project("running-project")
    job = SyncJob.objects.create(status="RUNNING")

    reservation = reserve_project_sync(
        job_id=job.id,
        project_id=project.id,
    )

    first = claim_project_sync(
        run_id=reservation.run.id,
        task_id="task-a",
    )

    second = claim_project_sync(
        run_id=reservation.run.id,
        task_id="task-b",
    )

    assert first.claimed is True
    assert second.claimed is False
    assert second.reason == "already_running"

    second.run.refresh_from_db()

    assert second.run.task_id == "task-a"


@pytest.mark.django_db(transaction=True)
def test_expired_running_lease_can_be_recovered():
    project = make_project("recover-project")
    job = SyncJob.objects.create(status="RUNNING")

    reservation = reserve_project_sync(
        job_id=job.id,
        project_id=project.id,
    )

    run = reservation.run
    run.status = ProjectSyncRun.Status.RUNNING
    run.task_id = "dead-worker"
    run.lease_expires_at = timezone.now() - timedelta(seconds=1)
    run.save()

    result = claim_project_sync(
        run_id=run.id,
        task_id="replacement-worker",
    )

    assert result.claimed is True
    assert result.reason == "recovered"

    result.run.refresh_from_db()

    assert result.run.task_id == "replacement-worker"
    assert result.run.result_json["lease_recovery_count"] == 1


@pytest.mark.django_db(transaction=True)
def test_terminal_run_cannot_be_claimed():
    project = make_project("terminal-project")
    job = SyncJob.objects.create(status="DONE")

    run = ProjectSyncRun.objects.create(
        job=job,
        project=project,
        status=ProjectSyncRun.Status.DONE,
    )

    result = claim_project_sync(
        run_id=run.id,
        task_id="unexpected-task",
    )

    assert result.claimed is False
    assert result.reason == "terminal"