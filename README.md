# AI Knowledge Django + MCP v0.3.0

Migração arquitetural do MVP FastAPI para **Django ASGI + MCP + PostgreSQL/pgvector + Celery + Redis + Ollama**, preparada para Linux e futura troca GitHub → GitLab.

## Perfis de acesso

- **Analista de Sistemas (`ANALYST`)**: consulta todos os projetos `enabled=True`. Não exige cadastro projeto a projeto.
- **Desenvolvedor (`DEVELOPER`)**: negação por padrão; consulta somente projetos explicitamente associados em `UserProjectAccess`.
- Superuser Django: administração técnica e acesso a todos os projetos.

A autorização é resolvida **antes do retrieval** e também é reaplicada no servidor MCP. O LLM nunca decide ACL.

## Desenvolvimento local (Windows + Docker Desktop)

```powershell
Copy-Item .env.example .env
# edite .env e preserve seus tokens fora do Git

docker compose -f compose.yaml -f compose.dev.yaml up -d --build

docker compose --env-file .env -f compose.yaml -f compose.dev.yaml exec web python manage.py createsuperuser
```

Acesse `http://127.0.0.1:8080/admin/`.

## Criar perfis

**Atenção:** os comandos abaixo são apenas exemplos de desenvolvimento; passar `--password` na linha de comando pode expor a senha no histórico do shell e na lista de processos. Para usuários reais, prefira um fluxo seguro de provisionamento/definição de senha e administração de vínculos pelo Django Admin. Não reutilize os valores ilustrativos.

Analista, com todos os projetos:
```powershell
docker compose --env-file .env -f compose.yaml -f compose.dev.yaml exec web python manage.py create_role_user analista1 --role ANALYST --password "SenhaSomenteExemplo"
```

Desenvolvedor, com projetos específicos:
```powershell
docker compose --env-file .env -f compose.yaml -f compose.dev.yaml exec web python manage.py create_role_user dev1 --role DEVELOPER --project owner/sistema-a --project owner/sistema-b --password "SenhaSomenteExemplo"
```

Também é possível administrar os perfis e vínculos no Django Admin em **User access profiles**.

## MCP

O serviço `mcp-knowledge` expõe tools MCP por Streamable HTTP. O Django emite um `actor_token` assinado, de curta duração; o servidor MCP valida o token, recarrega o usuário no banco e resolve o ACL atual antes de buscar chunks. Assim, um tool call não pode ampliar o escopo do usuário simplesmente informando outro username.

## Linux com Docker Compose

O alvo de homologação/produção é Linux. A instrução abaixo é um exemplo de Compose documentado, **não uma comprovação de deploy pronto para produção**. Verifique `.env`, proxy HTTPS, volumes, secrets e políticas operacionais antes de usar:
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

## Operação RC3 com Podman (Ubuntu)

A RC3 local relatada utiliza **Podman rootless**, diferentemente dos exemplos Docker Compose acima. Os oito serviços foram observados anteriormente, mas este pacote de documentação não inclui os arquivos Compose ou a configuração do host. Para diagnóstico inicial **somente leitura**, no terminal Ubuntu do host da RC3:

```bash
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
```

Não presumir que `docker compose` e `podman-compose` utilizem os mesmos caminhos, nomes de projeto ou políticas de restart. Evite `down -v`, remoção de volumes ou operações de restore sem runbook validado e autorização.

## Estado e documentação da RC3

A revisão documental de 20/10/2026 **não** declara liberação para produção. Consulte:

- `docs/ENCERRAMENTO_RC3.md` — rastreabilidade, evidências e critérios pendentes.
- `docs/RUNBOOK_BACKUP_RESTORE_RC3.md` — roteiro de backup/restore **não validado**.
- `docs/ROADMAP.md` — evolução e proposta DOC-001.
- `docs/ESPECIFICACAO_DOC_001.md` — inspeção documental futura de projetos externos autorizados; **não implementada**.
- `docs/TESTES_SEGURANCA.md` — resultados históricos de 29 testes (26/09/2026), não reexecutados nesta revisão.

A IA que consulta projetos externos permanece read-only. Atualizações locais dos arquivos deste repositório devem ser revisadas por um mantenedor e integradas via Pull Request na cadeia de branches protegidas.
