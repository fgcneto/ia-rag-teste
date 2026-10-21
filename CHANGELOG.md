# Changelog

## v0.3.0 — 2026-09-16

Consolidação das duas entradas originais `v0.3.0` e `0.3.0 - 2026-09-16`, sem criação de nova versão e preservando seus itens funcionais:

- Migração da aplicação principal para Django ASGI.
- MCP Knowledge Server e cliente MCP, com revalidação de ACL.
- Perfil Analista de Sistemas com acesso aos projetos habilitados e perfil Desenvolvedor com escopo explícito por projeto.
- Django Admin para administração de ACL.
- Seletor de escopo: todos os sistemas autorizados ou seleção de um/múltiplos sistemas.
- Validação de escopo no Django e novamente no MCP, com negação por padrão.
- PostgreSQL/pgvector via Django ORM.
- Celery e Redis.
- Streaming Ollama preservado.
- Abstração de provider para GitHub/GitLab; GitHub Provider implementado e GitLab Provider previsto para evolução futura.
- Arquivos Compose de desenvolvimento/produção para evolução Linux.
- Estrutura Git/CI inicial para futura migração ao GitLab.
