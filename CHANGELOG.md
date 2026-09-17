# Changelog
## v0.3.0
- migração da aplicação principal para Django ASGI;
- MCP Knowledge Server + MCP client;
- perfil Analista de Sistemas com escopo global;
- perfil Desenvolvedor com escopo explícito por projeto;
- Django Admin para ACL;
- Celery/Redis;
- pgvector via Django ORM;
- streaming Ollama preservado;
- provider abstraction GitHub/GitLab;
- Compose dev/prod para Linux futuro.

## 0.3.0 - 2026-09-16
- Django ASGI como aplicação principal.
- MCP Knowledge com revalidação de ACL.
- Perfis Analista de Sistemas e Desenvolvedor.
- Analista consulta todos os projetos habilitados; Desenvolvedor somente projetos atribuídos.
- Seletor de escopo: todos os sistemas autorizados ou seleção de um/múltiplos sistemas.
- Validação de escopo no Django e novamente no MCP (deny-by-default).
- Streaming Ollama preservado.
- GitHub provider e contrato para GitLab provider.
- Estrutura Git/CI inicial para migração futura ao GitLab.
