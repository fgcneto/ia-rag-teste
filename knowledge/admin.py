from django.contrib import admin
from .models import Project,KnowledgeChunk,SyncJob
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display=['path_with_namespace','provider','enabled','indexed_at','last_metadata_sync_at']; list_filter=['provider','enabled']; search_fields=['path_with_namespace','name']
@admin.register(KnowledgeChunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display=['id','project','source_type','title','created_at']; list_filter=['source_type']; search_fields=['project__path_with_namespace','title','source_key']; readonly_fields=['content_hash','created_at']
@admin.register(SyncJob)
class SyncJobAdmin(admin.ModelAdmin): list_display=['id','status','requested_by','created_at','started_at','finished_at']; list_filter=['status']
