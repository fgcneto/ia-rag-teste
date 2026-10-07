import asyncio
import json

import httpx
import pytest

from core.llm import ollama


class FakeStreamResponse:
    def __init__(self, objects):
        self.objects = objects

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for obj in self.objects:
            yield json.dumps(obj)


class FakeClient:
    def __init__(self, objects, *args, **kwargs):
        self.objects = objects

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, *args, **kwargs):
        return FakeStreamResponse(self.objects)


def test_stream_chat_yields_content_without_exposing_thinking(
    monkeypatch,
):
    objects = [
        {
            "message": {
                "role": "assistant",
                "thinking": "raciocínio interno",
                "content": "",
            },
            "done": False,
        },
        {
            "message": {
                "role": "assistant",
                "content": "Resposta segura.",
            },
            "done": False,
        },
        {
            "message": {
                "role": "assistant",
                "content": "",
            },
            "done": True,
            "done_reason": "stop",
            "eval_count": 20,
        },
    ]

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: FakeClient(
            objects, *args, **kwargs
        ),
    )

    async def collect():
        return [
            chunk
            async for chunk in ollama.stream_chat(
                "system",
                "user",
            )
        ]

    chunks = asyncio.run(collect())

    assert chunks == ["Resposta segura."]


def test_stream_chat_fails_when_generation_finishes_without_content(
    monkeypatch,
):
    objects = [
        {
            "message": {
                "role": "assistant",
                "thinking": "raciocínio interno",
                "content": "",
            },
            "done": False,
        },
        {
            "message": {
                "role": "assistant",
                "thinking": "mais raciocínio",
                "content": "",
            },
            "done": True,
            "done_reason": "length",
            "eval_count": 192,
        },
    ]

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: FakeClient(
            objects, *args, **kwargs
        ),
    )

    async def consume():
        async for _ in ollama.stream_chat("system", "user"):
            pass

    with pytest.raises(ollama.EmptyGenerationError):
        asyncio.run(consume())
