# AI Knowledge Django + MCP v0.3.0

Migração arquitetural do MVP FastAPI para **Django ASGI + MCP + PostgreSQL/pgvector + Celery + Redis + Ollama**, preparada para Linux e futura troca GitHub → GitLab.

## Perfis de acesso

- **Analista de Sistemas (`ANALYST`)**: consulta todos os projetos `enabled=True`. Não exige cadastro projeto a projeto.
- **Desenvolvedor (`DEVELOPER`)**: negação por padrão; consulta somente projetos explicitamente associados em `UserProjectAccess`.
- Superuser Django: administração técnica e acesso a todos os projetos.

A autorização é resolvida **antes do retrieval** e também é reaplicada no servidor MCP. O LLM nunca decide ACL.

## Subir no ambiente atual (Windows + Docker Desktop)

```powershell
Copy-Item .env.example .env
# edite .env e preserve seus tokens fora do Git

docker compose -f compose.yaml -f compose.dev.yaml up -d --build

docker compose exec web python manage.py createsuperuser
```

Acesse `http://127.0.0.1:8080/admin/`.

## Criar perfis

Analista, com todos os projetos:
```powershell
docker compose exec web python manage.py create_role_user analista1 --role ANALYST --password "TroqueEstaSenha"
```

Desenvolvedor, com projetos específicos:
```powershell
docker compose exec web python manage.py create_role_user dev1 --role DEVELOPER --project owner/sistema-a --project owner/sistema-b --password "TroqueEstaSenha"
```

Também é possível administrar os perfis e vínculos no Django Admin em **User access profiles**.

## MCP

O serviço `mcp-knowledge` expõe tools MCP por Streamable HTTP. O Django emite um `actor_token` assinado, de curta duração; o servidor MCP valida o token, recarrega o usuário no banco e resolve o ACL atual antes de buscar chunks. Assim, um tool call não pode ampliar o escopo do usuário simplesmente informando outro username.

## Linux

O alvo de homologação/produção é Linux. Use:
```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```
Windows permanece adequado para desenvolvimento por enquanto.

## GitLab

O contrato `SourceControlProvider` já desacopla o core. `GitHubProvider` está implementado; `GitLabProvider` é um stub intencional para a próxima etapa, sem contaminar RAG, ACL ou MCP.

## Segurança

- deny-by-default para Desenvolvedor;
- Analista recebe todos os projetos habilitados por regra de negócio;
- nenhum write method no GitHub provider;
- MCP usa identidade assinada e ACL server-side;
- conteúdo recuperado é tratado como não confiável;
- output guard antes do streaming;
- `.env` excluído do Git.

## Escopo de consulta por usuário (v0.3.0)
A tela permite consultar todos os sistemas autorizados ou selecionar um/múltiplos sistemas. O navegador nunca define autorização: Django calcula o conjunto máximo permitido, valida a seleção e envia somente o escopo efetivo ao MCP. O MCP recalcula a ACL e rejeita qualquer tentativa de ampliação do escopo antes do retrieval pgvector.

Consulte `GIT_WORKFLOW.md` para o fluxo Git recomendado.
