from django.http import JsonResponse
from django.db import connection
import httpx
from django.conf import settings
def live(request): return JsonResponse({'status':'ok'})
async def ready(request):
    db='ok'; ollama='ok'
    try:
        with connection.cursor() as c: c.execute('SELECT 1')
    except Exception: db='error'
    try:
        async with httpx.AsyncClient(timeout=3) as client: r=await client.get(settings.OLLAMA_URL.rstrip('/')+'/api/tags'); r.raise_for_status()
    except Exception: ollama='error'
    status=200 if db=='ok' and ollama=='ok' else 503
    return JsonResponse({'status':'ready' if status==200 else 'degraded','database':db,'ollama':ollama},status=status)
