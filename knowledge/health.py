import httpx
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import DatabaseError, connection
from django.http import JsonResponse


def check_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        return cursor.fetchone() == (1,)


def live(request):
    return JsonResponse({"status": "ok"})


async def ready(request):
    db = "ok"
    ollama = "ok"

    try:
        database_healthy = await sync_to_async(
            check_database,
            thread_sensitive=True,
        )()
        if not database_healthy:
            db = "error"
    except (DatabaseError, OSError):
        db = "error"

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(settings.OLLAMA_URL.rstrip("/") + "/api/tags")
            response.raise_for_status()
    except httpx.HTTPError:
        ollama = "error"

    status = 200 if db == "ok" and ollama == "ok" else 503

    return JsonResponse(
        {
            "status": "ready" if status == 200 else "degraded",
            "database": db,
            "ollama": ollama,
        },
        status=status,
    )
