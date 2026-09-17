import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from asgiref.sync import sync_to_async
from core.security.guard import (
    inspect_question, Decision, SECURITY_RESPONSE, PRIVACY_RESPONSE,
    SECRET_RESPONSE, NO_EVIDENCE_RESPONSE, question_hash,
)
from core.rag.service import answer_stream
from core.mcp.client import search_knowledge_via_mcp
from accounts.services import authorized_projects_sync, resolve_query_scope
from auditlog.models import AuditEvent


@login_required
def home(request):
    profile = getattr(request.user, 'access_profile', None)
    projects = authorized_projects_sync(request.user)
    return render(request, 'chatapp/home.html', {'profile': profile, 'projects': projects})


def event(name, **kw):
    return (json.dumps({'event': name, **kw}, ensure_ascii=False) + '\n').encode()


@login_required
async def chat_stream(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    try:
        payload = json.loads(request.body or '{}')
        question = (payload.get('question') or '').strip()
        scope = payload.get('scope') or {}
        mode = scope.get('mode', 'all')
        requested_project_ids = scope.get('project_ids') or []
    except Exception:
        return JsonResponse({'detail': 'JSON inválido'}, status=400)

    try:
        effective_project_ids = await resolve_query_scope(
            request.user, mode, requested_project_ids
        )
    except ValueError as exc:
        return JsonResponse({'detail': str(exc)}, status=400)
    except PermissionError as exc:
        await sync_to_async(AuditEvent.objects.create)(
            user=request.user, event_type='chat', decision='ACL_DENY',
            reason='Tentativa de consultar projeto fora do escopo autorizado.',
            question_hash=question_hash(question),
        )
        return JsonResponse({'detail': str(exc)}, status=403)

    sec = inspect_question(question, settings.MAX_QUESTION_CHARS)
    blocked = {
        Decision.SECURITY_ATTACK: SECURITY_RESPONSE,
        Decision.PRIVACY_VIOLATION: PRIVACY_RESPONSE,
        Decision.SECRET_REQUEST: SECRET_RESPONSE,
        Decision.TOO_LARGE: 'Pergunta excede o tamanho permitido.',
    }

    async def stream():
        if sec.decision != Decision.ALLOW:
            await sync_to_async(AuditEvent.objects.create)(
                user=request.user, event_type='chat', decision=sec.decision.value,
                reason=sec.reason, question_hash=question_hash(question)
            )
            yield event('meta', decision=sec.decision.value, sources=[])
            yield event('delta', text=blocked[sec.decision])
            yield event('done')
            return
        try:
            sources = await search_knowledge_via_mcp(
                request.user, sec.redacted, effective_project_ids
            )
        except Exception as exc:
            await sync_to_async(AuditEvent.objects.create)(
                user=request.user, event_type='chat', decision='MCP_ERROR',
                reason=type(exc).__name__, question_hash=question_hash(question)
            )
            yield event('error', message='Falha segura ao consultar a camada MCP.')
            return
        if not sources:
            yield event('meta', decision='OUT_OF_SCOPE', sources=[])
            yield event('delta', text=NO_EVIDENCE_RESPONSE)
            yield event('done')
            return
        public = [
            {k: s[k] for k in ('chunk_id', 'project', 'title', 'url', 'source_type', 'similarity')}
            for s in sources
        ]
        yield event('meta', decision='ALLOW', sources=public)
        async for delta in answer_stream(sec.redacted, sources):
            yield event('delta', text=delta)
        await sync_to_async(AuditEvent.objects.create)(
            user=request.user, event_type='chat', decision='ALLOW',
            reason=f'Resposta RAG via MCP; escopo={sorted(effective_project_ids)}',
            question_hash=question_hash(question),
            source_ids=[s['chunk_id'] for s in sources],
        )
        yield event('done')

    return StreamingHttpResponse(
        stream(), content_type='application/x-ndjson',
        headers={'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no'},
    )
