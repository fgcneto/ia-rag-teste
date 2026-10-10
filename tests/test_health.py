from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from asgiref.sync import async_to_sync
from django.test import AsyncClient


def test_liveness_returns_ok():
    response = async_to_sync(AsyncClient().get)("/health/live/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("database_ok", "ollama_ok", "expected_status"),
    [
        (True, True, 200),
        (False, True, 503),
        (True, False, 503),
        (False, False, 503),
    ],
)
def test_readiness(database_ok, ollama_ok, expected_status):
    with (
        patch(
            "knowledge.health.check_database",
            return_value=database_ok,
        ),
        patch("knowledge.health.httpx.AsyncClient") as http_client,
    ):
        client_instance = http_client.return_value.__aenter__.return_value

        if ollama_ok:
            response_mock = Mock()
            response_mock.raise_for_status.return_value = None
            client_instance.get = AsyncMock(return_value=response_mock)
        else:
            client_instance.get = AsyncMock(
                side_effect=httpx.ConnectError("Ollama indisponível")
        )

        response = async_to_sync(AsyncClient().get)("/health/ready/")

    assert response.status_code == expected_status
    assert response.json() == {
        "status": "ready" if expected_status == 200 else "degraded",
        "database": "ok" if database_ok else "error",
        "ollama": "ok" if ollama_ok else "error",
    }


@pytest.mark.django_db(transaction=True)
def test_readiness_with_real_database():
    with patch("knowledge.health.httpx.AsyncClient") as http_client:
        client_instance = http_client.return_value.__aenter__.return_value

        response_mock = Mock()
        response_mock.raise_for_status.return_value = None
        client_instance.get = AsyncMock(return_value=response_mock)

        response = async_to_sync(AsyncClient().get)("/health/ready/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "ollama": "ok",
    }
