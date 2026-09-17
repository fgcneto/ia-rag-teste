from celery import shared_task
from django.utils import timezone
from asgiref.sync import async_to_sync
from .models import Project,SyncJob
from core.providers.factory import get_source_provider
@shared_task(bind=True)
def sync_repositories(self,job_id=None):
 job=SyncJob.objects.get(pk=job_id) if job_id else SyncJob.objects.create(status='QUEUED')
 job.status='RUNNING';job.started_at=timezone.now();job.task_id=self.request.id;job.save()
 try:
  provider=get_source_provider(); repos=async_to_sync(provider.repositories)(); count=0
  for r in repos:
   full=r['full_name']; Project.objects.update_or_create(path_with_namespace=full,defaults={'provider':'github','external_id':str(r.get('id','')),'name':r.get('name',full),'web_url':r.get('html_url',''),'default_branch':r.get('default_branch'),'enabled':True});count+=1
  job.status='DONE';job.result_json={'projects_seen':count}
 except Exception as exc: job.status='FAILED';job.error=repr(exc);raise
 finally: job.finished_at=timezone.now();job.save()
 return job.result_json
