from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from knowledge.models import Project, ProjectSyncRun, SyncJob


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


def active_lease():
    return timezone.now() + timedelta(hours=2)


@pytest.mark.django_db(transaction=True)
def test_same_job_cannot_have_duplicate_project_runs():
    project = make_project("duplicate-job-project")
    job = SyncJob.objects.create(status="RUNNING")

    ProjectSyncRun.objects.create(
        job=job,
        project=project,
        status=ProjectSyncRun.Status.DONE,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ProjectSyncRun.objects.create(
                job=job,
                project=project,
                status=ProjectSyncRun.Status.SKIPPED,
            )


@pytest.mark.django_db(transaction=True)
def test_only_one_active_sync_is_allowed_per_project():
    project = make_project("exclusive-project")

    first_job = SyncJob.objects.create(status="RUNNING")
    second_job = SyncJob.objects.create(status="RUNNING")

    ProjectSyncRun.objects.create(
        job=first_job,
        project=project,
        status=ProjectSyncRun.Status.RUNNING,
        lease_expires_at=active_lease(),
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ProjectSyncRun.objects.create(
                job=second_job,
                project=project,
                status=ProjectSyncRun.Status.QUEUED,
                lease_expires_at=active_lease(),
            )


@pytest.mark.django_db(transaction=True)
def test_terminal_sync_can_coexist_with_active_sync():
    project = make_project("terminal-and-active")

    old_job = SyncJob.objects.create(status="DONE")
    current_job = SyncJob.objects.create(status="RUNNING")

    ProjectSyncRun.objects.create(
        job=old_job,
        project=project,
        status=ProjectSyncRun.Status.DONE,
    )

    run = ProjectSyncRun.objects.create(
        job=current_job,
        project=project,
        status=ProjectSyncRun.Status.RUNNING,
        lease_expires_at=active_lease(),
    )

    assert run.pk is not None


@pytest.mark.django_db(transaction=True)
def test_active_sync_requires_lease():
    project = make_project("lease-required")
    job = SyncJob.objects.create(status="RUNNING")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ProjectSyncRun.objects.create(
                job=job,
                project=project,
                status=ProjectSyncRun.Status.RUNNING,
                lease_expires_at=None,
            )