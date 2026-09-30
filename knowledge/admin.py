from django.contrib import admin

from .models import (
    KnowledgeChunk,
    Project,
    ProjectSyncRun,
    SyncJob,
)


class ReadOnlyExecutionAdminMixin:
    """
    Objetos de execução são registros operacionais/auditáveis.

    O Django Admin deve permitir consulta, mas não criação,
    alteração ou exclusão desses registros.
    """

    def has_add_permission(
        self,
        request,
    ):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        "path_with_namespace",
        "provider",
        "enabled",
        "indexed_at",
        "last_metadata_sync_at",
    ]

    list_filter = [
        "provider",
        "enabled",
    ]

    search_fields = [
        "path_with_namespace",
        "name",
    ]


@admin.register(KnowledgeChunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "project",
        "source_type",
        "title",
        "created_at",
    ]

    list_filter = [
        "source_type",
    ]

    search_fields = [
        "project__path_with_namespace",
        "title",
        "source_key",
    ]

    readonly_fields = [
        "content_hash",
        "created_at",
    ]


@admin.register(SyncJob)
class SyncJobAdmin(
    ReadOnlyExecutionAdminMixin,
    admin.ModelAdmin,
):
    list_display = [
        "id",
        "status",
        "requested_by",
        "task_id",
        "created_at",
        "started_at",
        "finished_at",
    ]

    list_filter = [
        "status",
        "requested_by",
    ]

    search_fields = [
        "task_id",
        "requested_by",
    ]

    readonly_fields = [
        "id",
        "status",
        "task_id",
        "requested_by",
        "started_at",
        "finished_at",
        "result_json",
        "error",
        "created_at",
    ]

    ordering = [
        "-created_at",
    ]


@admin.register(ProjectSyncRun)
class ProjectSyncRunAdmin(
    ReadOnlyExecutionAdminMixin,
    admin.ModelAdmin,
):
    list_display = [
        "id",
        "job",
        "project",
        "status",
        "force",
        "target_sha",
        "started_at",
        "finished_at",
        "lease_expires_at",
    ]

    list_filter = [
        "status",
        "force",
    ]

    search_fields = [
        "project__path_with_namespace",
        "task_id",
        "target_sha",
    ]

    readonly_fields = [
        "id",
        "job",
        "project",
        "status",
        "task_id",
        "target_sha",
        "force",
        "lease_expires_at",
        "started_at",
        "finished_at",
        "result_json",
        "error",
        "created_at",
        "updated_at",
    ]

    list_select_related = [
        "job",
        "project",
    ]

    ordering = [
        "-created_at",
    ]
