import pytest
from django.db import IntegrityError, transaction
from types import SimpleNamespace
from knowledge import tasks

from knowledge.models import SyncJob
from knowledge.services.scheduled_sync import (
    SCHEDULED_REQUESTED_BY,
    reserve_scheduled_sync_job,
)


@pytest.mark.django_db(transaction=True)
def test_reserve_scheduled_sync_creates_job():
    result = reserve_scheduled_sync_job()

    assert result.created is True
    assert result.reason == "created"
    assert result.job.status == SyncJob.Status.QUEUED
    assert result.job.requested_by == SCHEDULED_REQUESTED_BY


@pytest.mark.django_db(transaction=True)
def test_existing_queued_scheduled_job_blocks_new_job():
    existing = SyncJob.objects.create(
        status=SyncJob.Status.QUEUED,
        requested_by=SCHEDULED_REQUESTED_BY,
    )

    result = reserve_scheduled_sync_job()

    assert result.created is False
    assert result.reason == "active_job"
    assert result.job.id == existing.id

    assert (
        SyncJob.objects
        .filter(
            requested_by=SCHEDULED_REQUESTED_BY,
        )
        .count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_existing_running_scheduled_job_blocks_new_job():
    existing = SyncJob.objects.create(
        status=SyncJob.Status.RUNNING,
        requested_by=SCHEDULED_REQUESTED_BY,
    )

    result = reserve_scheduled_sync_job()

    assert result.created is False
    assert result.job.id == existing.id


@pytest.mark.django_db(transaction=True)
def test_terminal_scheduled_job_allows_new_cycle():
    old = SyncJob.objects.create(
        status=SyncJob.Status.DONE,
        requested_by=SCHEDULED_REQUESTED_BY,
    )

    result = reserve_scheduled_sync_job()

    assert result.created is True
    assert result.job.id != old.id


@pytest.mark.django_db(transaction=True)
def test_manual_job_does_not_block_scheduled_cycle():
    SyncJob.objects.create(
        status=SyncJob.Status.RUNNING,
        requested_by="management-command",
    )

    result = reserve_scheduled_sync_job()

    assert result.created is True


@pytest.mark.django_db(transaction=True)
def test_database_rejects_two_active_scheduled_jobs():
    SyncJob.objects.create(
        status=SyncJob.Status.RUNNING,
        requested_by=SCHEDULED_REQUESTED_BY,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SyncJob.objects.create(
                status=SyncJob.Status.QUEUED,
                requested_by=SCHEDULED_REQUESTED_BY,
            )

@pytest.mark.django_db(transaction=True)
def test_integrity_error_falls_back_to_active_job(
    monkeypatch,
):
    existing = SyncJob.objects.create(
        status=SyncJob.Status.RUNNING,
        requested_by="synthetic-other-source",
    )

    responses = iter([
        None,
        existing,
    ])

    monkeypatch.setattr(
        "knowledge.services.scheduled_sync._active_scheduled_job",
        lambda: next(responses),
    )

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError(
            "synthetic concurrent insert"
        )

    monkeypatch.setattr(
        SyncJob.objects,
        "create",
        raise_integrity_error,
    )

    result = reserve_scheduled_sync_job()

    assert result.created is False
    assert result.reason == "active_job"
    assert result.job.id == existing.id

@pytest.mark.django_db(transaction=True)
def test_scheduled_tick_dispatches_orchestrator(
    monkeypatch,
):
    job = SyncJob.objects.create(
        status=SyncJob.Status.QUEUED,
        requested_by=SCHEDULED_REQUESTED_BY,
    )

    reservation = SimpleNamespace(
        job=job,
        created=True,
        reason="created",
    )

    monkeypatch.setattr(
        tasks,
        "reserve_scheduled_sync_job",
        lambda: reservation,
    )

    dispatched = []

    def fake_delay(**kwargs):
        dispatched.append(kwargs)

        return SimpleNamespace(
            id="scheduled-orchestrator-1"
        )

    monkeypatch.setattr(
        tasks.sync_repositories,
        "delay",
        fake_delay,
    )

    result = tasks.scheduled_sync_tick.run()

    job.refresh_from_db()

    assert dispatched == [{
        "job_id": job.id,
        "force": False,
    }]

    assert job.task_id == (
        "scheduled-orchestrator-1"
    )

    assert result["created"] is True
    assert result["dispatched"] is True


@pytest.mark.django_db(transaction=True)
def test_scheduled_tick_does_not_dispatch_when_active(
    monkeypatch,
):
    job = SyncJob.objects.create(
        status=SyncJob.Status.RUNNING,
        requested_by=SCHEDULED_REQUESTED_BY,
    )

    reservation = SimpleNamespace(
        job=job,
        created=False,
        reason="active_job",
    )

    monkeypatch.setattr(
        tasks,
        "reserve_scheduled_sync_job",
        lambda: reservation,
    )

    def unexpected_dispatch(*args, **kwargs):
        raise AssertionError(
            "Orquestrador não deveria ser publicado."
        )

    monkeypatch.setattr(
        tasks.sync_repositories,
        "delay",
        unexpected_dispatch,
    )

    result = tasks.scheduled_sync_tick.run()

    assert result["created"] is False
    assert result["dispatched"] is False
    assert result["reason"] == "active_job"


@pytest.mark.django_db(transaction=True)
def test_scheduled_tick_marks_job_failed_when_dispatch_fails(
    monkeypatch,
):
    job = SyncJob.objects.create(
        status=SyncJob.Status.QUEUED,
        requested_by=SCHEDULED_REQUESTED_BY,
    )

    reservation = SimpleNamespace(
        job=job,
        created=True,
        reason="created",
    )

    monkeypatch.setattr(
        tasks,
        "reserve_scheduled_sync_job",
        lambda: reservation,
    )

    def fail_dispatch(*args, **kwargs):
        raise RuntimeError(
            "synthetic broker failure"
        )

    monkeypatch.setattr(
        tasks.sync_repositories,
        "delay",
        fail_dispatch,
    )

    with pytest.raises(
        RuntimeError,
        match="synthetic broker failure",
    ):
        tasks.scheduled_sync_tick.run()

    job.refresh_from_db()

    assert job.status == SyncJob.Status.FAILED
    assert job.finished_at is not None
    assert "synthetic broker failure" in job.error