from django.contrib import admin
from django.test import RequestFactory

from knowledge.admin import (
    ProjectSyncRunAdmin,
    SyncJobAdmin,
)
from knowledge.models import (
    ProjectSyncRun,
    SyncJob,
)


def test_execution_models_are_registered():
    assert isinstance(
        admin.site._registry[SyncJob],
        SyncJobAdmin,
    )

    assert isinstance(
        admin.site._registry[ProjectSyncRun],
        ProjectSyncRunAdmin,
    )


def test_sync_job_admin_is_read_only():
    request = RequestFactory().get(
        "/admin/knowledge/syncjob/"
    )

    model_admin = admin.site._registry[
        SyncJob
    ]

    assert (
        model_admin.has_add_permission(request)
        is False
    )

    assert (
        model_admin.has_change_permission(
            request
        )
        is False
    )

    assert (
        model_admin.has_delete_permission(
            request
        )
        is False
    )


def test_project_sync_run_admin_is_read_only():
    request = RequestFactory().get(
        "/admin/knowledge/projectsyncrun/"
    )

    model_admin = admin.site._registry[
        ProjectSyncRun
    ]

    assert (
        model_admin.has_add_permission(request)
        is False
    )

    assert (
        model_admin.has_change_permission(
            request
        )
        is False
    )

    assert (
        model_admin.has_delete_permission(
            request
        )
        is False
    )
