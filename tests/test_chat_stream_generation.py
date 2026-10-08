import json

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import AsyncClient

from accounts.models import UserProjectAccess
from auditlog.models import AuditEvent
from core.llm.ollama import EmptyGenerationError
from knowledge.models import Project


@pytest.mark.django_db(transaction=True)
def test_empty_llm_generation_is_audited_as_error_not_allow(
    monkeypatch,
):
    user = get_user_model().objects.create_user(
        username="llm-error-test",
        password="test-password",
    )

    project = Project.objects.create(
        provider="github",
        external_id="llm-error-project",
        name="llm-error-project",
        path_with_namespace="test/llm-error-project",
        web_url="https://example.invalid/test/llm-error-project",
        default_branch="main",
        enabled=True,
    )

    UserProjectAccess.objects.create(
        profile=user.access_profile,
        project=project,
        can_query=True,
    )

    sources = [
        {
            "chunk_id": 999001,
            "project_id": project.id,
            "project": project.path_with_namespace,
            "title": "SEGURANCA.md",
            "url": "https://example.invalid/SEGURANCA.md",
            "source_type": "repository",
            "content": "Conteúdo técnico autorizado.",
            "similarity": 0.90,
        }
    ]

    async def fake_search(user, question, project_ids):
        return sources

    async def fake_answer_stream(question, received_sources):
        if False:
            yield ""
        raise EmptyGenerationError(
            "LLM generation finished without content; "
            "done_reason=length"
        )

    monkeypatch.setattr(
        "chatapp.views.search_knowledge_via_mcp",
        fake_search,
    )
    monkeypatch.setattr(
        "chatapp.views.answer_stream",
        fake_answer_stream,
    )

    async def exercise():
        client = AsyncClient()
        await client.aforce_login(user)

        response = await client.post(
            "/api/chat/stream/",
            data=json.dumps(
                {
                    "question": "Como funciona o controle de acesso?",
                    "scope": {
                        "mode": "selected",
                        "project_ids": [project.id],
                    },
                }
            ),
            content_type="application/json",
        )

        body = b""
        async for chunk in response.streaming_content:
            body += chunk

        return response, body.decode()

    response, body = async_to_sync(exercise)()

    assert response.status_code == 200

    events = [
        json.loads(line)
        for line in body.splitlines()
        if line.strip()
    ]

    assert events[0]["event"] == "meta"
    assert events[0]["decision"] == "ALLOW"

    error_events = [
        item for item in events
        if item["event"] == "error"
    ]
    assert error_events == [
        {
            "event": "error",
            "message": "Falha segura ao gerar a resposta.",
        }
    ]

    assert not any(
        item["event"] == "done"
        for item in events
    )

    assert AuditEvent.objects.filter(
        user=user,
        decision="LLM_ERROR",
    ).count() == 1

    assert not AuditEvent.objects.filter(
        user=user,
        decision="ALLOW",
    ).exists()

    audit = AuditEvent.objects.get(
        user=user,
        decision="LLM_ERROR",
    )

    assert audit.reason == "EmptyGenerationError"
    assert audit.source_ids == [999001]

    assert "thinking" not in body.lower()
    assert "done_reason" not in body.lower()


@pytest.mark.django_db(transaction=True)
def test_grounding_validation_failure_is_audited_as_error_not_allow(
    monkeypatch,
):
    user = get_user_model().objects.create_user(
        username="grounding-error-test",
        password="test-password",
    )

    project = Project.objects.create(
        provider="github",
        external_id="grounding-error-project",
        name="grounding-error-project",
        path_with_namespace="test/grounding-error-project",
        web_url="https://example.invalid/test/grounding-error-project",
        default_branch="main",
        enabled=True,
    )

    UserProjectAccess.objects.create(
        profile=user.access_profile,
        project=project,
        can_query=True,
    )

    sources = [
        {
            "chunk_id": 999002,
            "project_id": project.id,
            "project": project.path_with_namespace,
            "title": "SEGURANCA.md",
            "url": "https://example.invalid/SEGURANCA.md",
            "source_type": "repository",
            "content": "Conteúdo técnico autorizado.",
            "similarity": 0.90,
        }
    ]

    async def fake_search(user, question, project_ids):
        return sources

    async def fake_answer_stream(question, received_sources):
        if False:
            yield ""

        from core.rag.service import GroundingValidationError

        raise GroundingValidationError(
            "Resposta sem citação de fonte."
        )

    monkeypatch.setattr(
        "chatapp.views.search_knowledge_via_mcp",
        fake_search,
    )
    monkeypatch.setattr(
        "chatapp.views.answer_stream",
        fake_answer_stream,
    )

    async def exercise():
        client = AsyncClient()
        await client.aforce_login(user)

        response = await client.post(
            "/api/chat/stream/",
            data=json.dumps(
                {
                    "question": "Como funciona o controle de acesso?",
                    "scope": {
                        "mode": "selected",
                        "project_ids": [project.id],
                    },
                }
            ),
            content_type="application/json",
        )

        body = b""

        try:
            async for chunk in response.streaming_content:
                body += chunk
        except Exception as exc:
            return response, body.decode(), exc

        return response, body.decode(), None

    response, body, raised = async_to_sync(exercise)()

    assert response.status_code == 200
    assert raised is None

    events = [
        json.loads(line)
        for line in body.splitlines()
        if line.strip()
    ]

    assert events[0]["event"] == "meta"
    assert events[0]["decision"] == "ALLOW"

    assert not any(
        item["event"] == "delta"
        for item in events
    )

    assert [
        item
        for item in events
        if item["event"] == "error"
    ] == [
        {
            "event": "error",
            "message": "Falha segura ao gerar a resposta.",
        }
    ]

    assert not any(
        item["event"] == "done"
        for item in events
    )

    assert AuditEvent.objects.filter(
        user=user,
        decision="LLM_ERROR",
    ).count() == 1

    assert not AuditEvent.objects.filter(
        user=user,
        decision="ALLOW",
    ).exists()

    audit = AuditEvent.objects.get(
        user=user,
        decision="LLM_ERROR",
    )

    assert audit.reason == "GroundingValidationError"
    assert audit.source_ids == [999002]

    assert "Resposta sem citação" not in body