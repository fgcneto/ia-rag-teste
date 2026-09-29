from asgiref.sync import async_to_sync
from celery import shared_task
from django.utils import timezone

from core.ingestion.pipeline import ingest_project
from core.providers.factory import get_source_provider
from .models import Project, SyncJob


@shared_task(bind=True)
def sync_repositories(self, job_id=None, force=False):
    job = SyncJob.objects.get(pk=job_id) if job_id else SyncJob.objects.create(status="QUEUED")
    job.status = "RUNNING"
    job.started_at = timezone.now()
    job.task_id = self.request.id
    job.save()
    try:
        provider = get_source_provider()
        repos = async_to_sync(provider.repositories)()
        results = []
        for repo in repos:
            full = repo["full_name"]
            project, _ = Project.objects.update_or_create(
                path_with_namespace=full,
                defaults={
                    "provider": "github",
                    "external_id": str(repo.get("id", "")),
                    "name": repo.get("name", full),
                    "web_url": repo.get("html_url", ""),
                    "default_branch": repo.get("default_branch"),
                    "last_metadata_sync_at": timezone.now(),
                    "enabled": True,
                },
            )
            result = async_to_sync(ingest_project)(provider, project, force=force)
            results.append(result.as_dict())
        job.status = "DONE"
        job.result_json = {"projects_seen": len(repos), "ingestion": results}
    except Exception as exc:
        job.status = "FAILED"
        job.error = repr(exc)
        raise
    finally:
        job.finished_at = timezone.now()
        job.save()
    return job.result_json
