# Migração FastAPI -> Django

A lógica foi reorganizada em `core/` para reduzir acoplamento ao framework. Streaming usa `StreamingHttpResponse` em ASGI. O worker RQ foi substituído por Celery/Redis. SQLAlchemy foi substituído por Django ORM + pgvector. O endpoint central agora usa MCP para retrieval.

Não copie `.env` para o repositório. Migre valores manualmente para o novo `.env`.
