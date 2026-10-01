from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.utils import timezone

from knowledge import tasks
from knowledge.models import (
    Project,
    ProjectSyncRun,
    SyncJob,
)
from knowledge.services.sync_jobs import (
    finalize_sync_job,
)
from knowledge.services.sync_runs import (
    reserve_project_sync,
)


class FakeProvider:
    def __init__(self, sha="same-sha"):
        self.sha = sha
        self.tree_called = False

    async def repositories(self):
        return [{
            "id": 10,
            "full_name": (
                "synthetic/repository"
            ),
            "name": "repository",
            "html_url": (
                "https://example.invalid/"
                "synthetic/repository"
            ),
            "default_branch": "main",
        }]

    async def branch(
        self,
        repository,
        branch_name,
    ):
        return {
            "commit": {
                "sha": self.sha,
                "commit": {
                    "tree": {
                        "sha": "tree-sha",
                    }
                },
            }
        }

    async def repository_tree(
        self,
        repository,
        tree_sha,
    ):
        self.tree_called = True
        raise AssertionError(
            "repository_tree não deveria "
            "ser chamado para SHA idêntico"
        )


@pytest.mark.django_db(transaction=True)
def test_orchestrator_dispatches_project_task(
    settings,
    monkeypatch,
):
    settings.SOURCE_PROVIDER = "github"

    provider = FakeProvider(
        sha="remote-sha"
    )

    monkeypatch.setattr(
        tasks,
        "get_source_provider",
        lambda *args, **kwargs: provider,
    )

    dispatched = []

    def fake_delay(run_id):
        dispatched.append(run_id)
        return SimpleNamespace(
            id="child-task-1"
        )

    monkeypatch.setattr(
        tasks.sync_project_run,
        "delay",
        fake_delay,
    )

    job = SyncJob.objects.create(
        status="QUEUED"
    )

    tasks.sync_repositories.run(
        job_id=job.id,
        force=False,
    )

    job.refresh_from_db()

    run = ProjectSyncRun.objects.get(
        job=job
    )

    assert dispatched == [run.id]
    assert run.status == (
        ProjectSyncRun.Status.QUEUED
    )
    assert run.task_id == "child-task-1"
    assert (
        job.result_json[
            "dispatch_complete"
        ]
        is True
    )
    assert job.status == "RUNNING"


@pytest.mark.django_db(transaction=True)
def test_same_sha_child_is_skipped(
    settings,
    monkeypatch,
):
    settings.SOURCE_PROVIDER = "github"

    provider = FakeProvider(
        sha="same-sha"
    )

    monkeypatch.setattr(
        tasks,
        "get_source_provider",
        lambda *args, **kwargs: provider,
    )

    project = Project.objects.create(
        provider=Project.Provider.GITHUB,
        external_id="same-sha",
        path_with_namespace=(
            "synthetic/same-sha"
        ),
        name="same-sha",
        web_url=(
            "https://example.invalid/"
            "synthetic/same-sha"
        ),
        default_branch="main",
        last_repository_sha="same-sha",
        enabled=True,
    )

    job = SyncJob.objects.create(
        status="RUNNING",
        result_json={
            "dispatch_complete": True,
        },
    )

    reservation = reserve_project_sync(
        job_id=job.id,
        project_id=project.id,
    )

    result = tasks.sync_project_run.run(
        reservation.run.id
    )

    reservation.run.refresh_from_db()
    job.refresh_from_db()

    assert result["status"] == (
        ProjectSyncRun.Status.SKIPPED
    )
    assert reservation.run.status == (
        ProjectSyncRun.Status.SKIPPED
    )
    assert provider.tree_called is False
    assert job.status == "DONE"


@pytest.mark.django_db(transaction=True)
def test_failed_child_marks_job_failed(
    settings,
    monkeypatch,
):
    settings.SOURCE_PROVIDER = "github"

    class FailingProvider:
        async def branch(
            self,
            repository,
            branch_name,
        ):
            raise RuntimeError(
                "synthetic provider failure"
            )

    monkeypatch.setattr(
        tasks,
        "get_source_provider",
        lambda *args, **kwargs: (
            FailingProvider()
        ),
    )

    project = Project.objects.create(
        provider=Project.Provider.GITHUB,
        external_id="failing",
        path_with_namespace=(
            "synthetic/failing"
        ),
        name="failing",
        web_url=(
            "https://example.invalid/"
            "synthetic/failing"
        ),
        default_branch="main",
        enabled=True,
    )

    job = SyncJob.objects.create(
        status="RUNNING",
        result_json={
            "dispatch_complete": True,
        },
    )

    reservation = reserve_project_sync(
        job_id=job.id,
        project_id=project.id,
    )

    with pytest.raises(
        RuntimeError,
        match="synthetic provider failure",
    ):
        tasks.sync_project_run.run(
            reservation.run.id
        )

    reservation.run.refresh_from_db()
    job.refresh_from_db()

    assert reservation.run.status == (
        ProjectSyncRun.Status.FAILED
    )
    assert job.status == "FAILED"


@pytest.mark.django_db(transaction=True)
def test_mixed_children_finalize_as_partial():
    first = Project.objects.create(
        provider=Project.Provider.GITHUB,
        external_id="first",
        path_with_namespace="synthetic/first",
        name="first",
        web_url=(
            "https://example.invalid/"
            "synthetic/first"
        ),
        enabled=True,
    )

    second = Project.objects.create(
        provider=Project.Provider.GITHUB,
        external_id="second",
        path_with_namespace="synthetic/second",
        name="second",
        web_url=(
            "https://example.invalid/"
            "synthetic/second"
        ),
        enabled=True,
    )

    job = SyncJob.objects.create(
        status="RUNNING",
        result_json={
            "dispatch_complete": True,
        },
    )

    ProjectSyncRun.objects.create(
        job=job,
        project=first,
        status=ProjectSyncRun.Status.DONE,
        finished_at=timezone.now(),
    )

    ProjectSyncRun.objects.create(
        job=job,
        project=second,
        status=ProjectSyncRun.Status.FAILED,
        finished_at=timezone.now(),
        error="synthetic",
    )

    finalize_sync_job(job.id)

    job.refresh_from_db()

    assert job.status == "PARTIAL"


@pytest.mark.django_db(transaction=True)
def test_finalize_does_not_reprocess_terminal_job():
    finished_at = timezone.now()

    job = SyncJob.objects.create(
        status=SyncJob.Status.FAILED,
        finished_at=finished_at,
        result_json={
            "dispatch_complete": True,
            "stale_recovery": {
                "recovered_at": finished_at.isoformat(),
            },
        },
    )

    finalize_sync_job(job.id)

    job.refresh_from_db()

    assert job.status == SyncJob.Status.FAILED
    assert job.finished_at == finished_at
    assert job.result_json["stale_recovery"][
        "recovered_at"
    ] == finished_at.isoformat()


@pytest.mark.django_db(transaction=True)
def test_dispatch_failure_does_not_leave_queued_run(
    settings,
    monkeypatch,
):
    settings.SOURCE_PROVIDER = "github"

    provider = FakeProvider(
        sha="remote-sha"
    )

    monkeypatch.setattr(
        tasks,
        "get_source_provider",
        lambda *args, **kwargs: provider,
    )

    def fail_delay(run_id):
        raise RuntimeError(
            "synthetic broker failure"
        )

    monkeypatch.setattr(
        tasks.sync_project_run,
        "delay",
        fail_delay,
    )

    job = SyncJob.objects.create(
        status="QUEUED"
    )

    tasks.sync_repositories.run(
        job_id=job.id,
    )

    job.refresh_from_db()

    run = ProjectSyncRun.objects.get(
        job=job
    )

    assert run.status == (
        ProjectSyncRun.Status.FAILED
    )
    assert run.lease_expires_at is None
    assert job.status == "FAILED"


@pytest.mark.django_db(transaction=True)
def test_management_command_dispatches_celery(
    monkeypatch,
):
    def fake_delay(
        job_id,
        force,
    ):
        return SimpleNamespace(
            id="orchestrator-task-1"
        )

    monkeypatch.setattr(
        "knowledge.management.commands."
        "sync_knowledge."
        "sync_repositories.delay",
        fake_delay,
    )

    stdout = StringIO()

    call_command(
        "sync_knowledge",
        stdout=stdout,
    )

    job = SyncJob.objects.latest(
        "id"
    )

    assert job.task_id == (
        "orchestrator-task-1"
    )
    assert "enfileirado" in (
        stdout.getvalue()
    )