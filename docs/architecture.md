# Arquitetura

```text
Browser -> Django ASGI -> Security Guard -> MCP Client
                                      -> MCP Knowledge Server -> ACL Django -> pgvector/RAG
                                                                        -> Ollama
Django Admin -> usuários/perfis/projetos
Celery -> SourceControlProvider -> GitHub hoje / GitLab futuro
```

## Invariantes
1. O LLM não decide autorização.
2. Desenvolvedor sem vínculo não recupera nenhum projeto.
3. Analista consulta todos os projetos habilitados.
4. MCP revalida identidade e ACL no servidor.
5. GitHub/GitLab são providers substituíveis.
