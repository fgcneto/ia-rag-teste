from django.db import models
from pgvector.django import VectorField
class Project(models.Model):
    class Provider(models.TextChoices): GITHUB='github','GitHub'; GITLAB='gitlab','GitLab'
    provider=models.CharField(max_length=20,choices=Provider.choices,default=Provider.GITHUB,db_index=True)
    external_id=models.CharField(max_length=255,blank=True,default='')
    path_with_namespace=models.CharField(max_length=500,unique=True,db_index=True)
    name=models.CharField(max_length=255); web_url=models.URLField(max_length=1000)
    default_branch=models.CharField(max_length=255,blank=True,null=True); last_repository_sha=models.CharField(max_length=64,blank=True,null=True)
    last_metadata_sync_at=models.DateTimeField(blank=True,null=True); indexed_at=models.DateTimeField(blank=True,null=True); enabled=models.BooleanField(default=True,db_index=True)
    def __str__(self): return self.path_with_namespace
class KnowledgeChunk(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='chunks')
    source_type=models.CharField(max_length=50,db_index=True); source_key=models.CharField(max_length=500,db_index=True); chunk_index=models.IntegerField()
    title=models.CharField(max_length=1000); source_url=models.URLField(max_length=1500); ref=models.CharField(max_length=255,blank=True,null=True)
    content=models.TextField(); content_hash=models.CharField(max_length=64,db_index=True); metadata_json=models.JSONField(default=dict)
    embedding=VectorField(dimensions=768); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['project','source_type','source_key','chunk_index'],name='uq_current_chunk')]
class SyncJob(models.Model):
    status=models.CharField(max_length=30,default='QUEUED',db_index=True); task_id=models.CharField(max_length=100,blank=True,null=True,db_index=True)
    requested_by=models.CharField(max_length=255,blank=True,null=True); started_at=models.DateTimeField(blank=True,null=True); finished_at=models.DateTimeField(blank=True,null=True)
    result_json=models.JSONField(default=dict); error=models.TextField(blank=True,null=True); created_at=models.DateTimeField(auto_now_add=True)
