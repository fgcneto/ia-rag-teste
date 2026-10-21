# Encerramento técnico da RC3 — AI Knowledge Django MCP

> **Estado:** RASCUNHO PARA REVISÃO. **Aceite técnico condicionado; produção não aprovada por este documento.**
> **Data da revisão documental:** 20/10/2026.
> **Branch de trabalho indicada:** `docs/rc3-closure`, derivada de `origin/homolog` no commit `030e5a8` (referência histórica; confirmar com `git status`/`git log` no checkout real).
> **Base:** oito documentos recebidos no pacote RC3, evidências operacionais anteriormente relatadas e registros de governança conhecidos. **Não** foram fornecidos código completo, Compose, manifestos, logs brutos ou acesso de execução ao ambiente para revalidação.

## 1. Objetivo e critérios de interpretação

Consolidar fatos documentados, resultados operacionais **relatados**, lacunas e ações exigidas para o aceite formal da RC3. Não equivale a homologação para produção, comprovação de RPO/RTO, disponibilidade externa ou certificação de segurança.

## 2. Identificação e governança

| Item | Referência histórica conhecida |
| --- | --- |
| Repositório | `fgcneto/ia-rag-teste` |
| Branches protegidas | `homolog`, `prod`, `main` |
| Fluxo | branch de trabalho → `homolog` → `prod` → `main`, por PR |
| Imagem RC3 local relatada | `localhost/ai-knowledge-django-mcp:rc3-secure-c572ca3` |
| Commit da política de CI | `742c407` |
| PRs de promoção | [#16](https://github.com/fgcneto/ia-rag-teste/pull/16), [#17](https://github.com/fgcneto/ia-rag-teste/pull/17), [#18](https://github.com/fgcneto/ia-rag-teste/pull/18) |
| Commit de `main` observado anteriormente | `6dd00e9f4613580de04443d6ede8e7f7222b047a` |
| CI pós-merge em `main` relatado | [Execução #39526957269](https://github.com/fgcneto/ia-rag-teste/actions/runs/39526957269), `completed/success` |
| Árvore Git das três branches, na verificação histórica | `b9ca8f4b8d830bc864b572890dde9c577f1dee70` |

O conteúdo das árvores `origin/homolog`, `origin/prod` e `origin/main` foi relatado como equivalente no momento da verificação histórica, apesar de commits de ponta diferentes. Esta revisão **não** consultou o estado remoto atual.

Três Rulesets (`protect-homolog`, `protect-prod`, `protect-main`) foram relatados como ativos. O job `tests` de `.github/workflows/ci.yml` aplica a política de promoção; a regra `prod` → `main` também verifica equivalência de conteúdo. Não houve comprovação de revisão independente: foi identificado um único colaborador e zero aprovações obrigatórias no contexto relatado. Não criar exigência de segundo aprovador sem revisor legítimo disponível.

## 3. Escopo da documentação confrontada

Foram lidos os oito arquivos recebidos: `docs/ARQUITETURA.md`, `docs/SEGURANCA.md`, `docs/ROADMAP.md`, `docs/TESTES_SEGURANCA.md`, `docs/SECURE_INGESTION.md`, `docs/SINCRONIZACAO_CONHECIMENTO.md`, `README.md` e `CHANGELOG.md`.

- Arquitetura: Django ASGI, MCP com `actor_token`, ACL antes do retrieval, pgvector, Ollama, Celery/Redis e GitHub read-only.
- GitLab Provider: contrato/stub, **não operacional** nesta base.
- Ingestão atual: **arquivos** de repositórios autorizados; Issues/PRs **não** são fontes do pipeline documentado.
- Sincronização: desabilitada por padrão, exclusividade/leases em PostgreSQL, incrementalidade por SHA de repositório, não por delta de arquivo.
- Segurança: controles implementados e limites de hardening de produção; a proteção por prompt não substitui ACL/DLP.
- README: exemplos Windows/Docker Desktop e Linux/Docker Compose; RC3 local relatada em Ubuntu/Podman rootless, sem pressupor equivalência.
- Changelog: duas entradas `v0.3.0` consolidadas nesta revisão, sem nova release.

## 4. Componentes e observações operacionais relatadas

| Container RC3 | Papel | Evidência histórica relatada |
| --- | --- | --- |
| `ai-knowledge-v031-rc3_postgres_1` | PostgreSQL/pgvector | ativo; saúde básica satisfatória |
| `ai-knowledge-v031-rc3_redis_1` | Redis | `PONG` |
| `ai-knowledge-v031-rc3_ollama_1` | LLM/embeddings | iniciado |
| `ai-knowledge-v031-rc3_presidio-analyzer_1` | PII | iniciado |
| `ai-knowledge-v031-rc3_web_1` | Django | HTTP 302 local; `manage.py check` sem problemas |
| `ai-knowledge-v031-rc3_worker_1` | Celery Worker | `inspect ping` positivo |
| `ai-knowledge-v031-rc3_beat_1` | Celery Beat | iniciado |
| `ai-knowledge-v031-rc3_mcp-knowledge_1` | MCP | `initialize` e `tools/list` verificados anteriormente |

Container iniciado **não** prova saúde funcional ponta a ponta. Não declarar `/health`, `/metrics`, dashboards, OpenAPI ou SLOs como existentes sem evidência de código e execução.

## 5. Matriz de evidências e lacunas

| Verificação | Estado da evidência | Limite |
| --- | --- | --- |
| Suíte histórica de segurança (26/09/2026) | `29/29 PASS`, 2 warnings, em `TESTES_SEGURANCA.md` | execução histórica, não RC3 atual |
| Suíte operacional RC3 | 93 testes aprovados **relatados** | log bruto, comando, commit e ambiente não fornecidos |
| Django check / migrations | aprovados em verificações anteriores | repetir no commit-alvo |
| PostgreSQL e Redis | saúde básica relatada | não é teste de carga ou restore |
| Celery Worker | `inspect ping` positivo | não valida todas as tasks |
| MCP | `initialize` e `tools/list` relatados | não valida contratos/ACL completos |
| Reinício do host Ubuntu | containers existentes reiniciados **manualmente** | não demonstra restart automático |
| CI após PR #18 em `main` | sucesso relatado, run `39526957269` | não reconsultado nesta revisão |
| Equivalência das branches | árvore idêntica em inspeção anterior | não reconsultada nesta revisão |
| Backups PostgreSQL | dois dumps e SHA-256 relatados | restauração e integridade pós-restore não comprovadas |
| HTTPS, monitoramento, RPO/RTO | sem comprovação suficiente | requisito de produção pendente |

## 6. Backup, restore e continuidade

Foram relatados dois dumps PostgreSQL com hash SHA-256 em diretório privado `~/.local/share/ai-knowledge/backups/`. Não anexar dumps nem revelar dados. Para diagnóstico não destrutivo no host Ubuntu/rootless Podman da RC3:

```bash
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
podman logs --tail 100 ai-knowledge-v031-rc3_web_1
podman logs --tail 100 ai-knowledge-v031-rc3_worker_1
podman logs --tail 100 ai-knowledge-v031-rc3_postgres_1
```

Antes de qualquer restore, validar autorização, banco de destino **isolado**, versão do PostgreSQL, integridade do dump, backup atual, janela e plano de retorno. Não executar restore destrutivo em produção com base neste documento. `RUNBOOK_BACKUP_RESTORE_RC3.md` é **rascunho não validado**.

O reinício manual dos containers existentes após reboot não equivale a política de reinício automático. Testar e registrar separadamente, caso seja requisito.

## 7. Riscos residuais e tratamento

| Risco | Situação e ação exigida |
| --- | --- |
| Revisão independente | ausente; planejar segundo mantenedor confiável e proteção de workflows |
| Alteração do próprio workflow de CI | avaliar controle independente da política de promoção |
| HTTPS/proxy reverso | não comprovado; validar antes de produção |
| Credenciais e revogação histórica | revisar, rotacionar/revogar quando aplicável; sem expor valores |
| Sincronização externa | `KNOWLEDGE_SYNC_ENABLED=false` em configuração anteriormente verificada; não presumir ingestão ativa |
| Monitoramento/alertas e RPO/RTO | não definidos/comprovados nesta revisão |
| Restore ponta a ponta | pendente de execução isolada e evidências |
| DOC-001 | proposta futura de inspeção de **projetos externos**, não implementada e não gate de CI próprio |

Responsáveis e prazos para cada risco devem ser definidos no processo de homologação; não são inferidos nesta revisão.

## 8. Checklist para aceite formal

- [x] Política de promoção por PR exercitada historicamente em `homolog`, `prod` e `main`.
- [x] Rulesets ativos e CI pós-merge relatados como aprovados.
- [x] Árvores Git equivalentes na inspeção histórica.
- [x] Confronto documental dos oito arquivos recebidos.
- [ ] Consolidar logs, comandos, datas, commits e ambiente dos 93 testes RC3.
- [x] Preservar e distinguir a evidência histórica de 29/29 testes de segurança.
- [ ] Confrontar com código completo, Compose, dependências e logs efetivos.
- [ ] Validar backup/restore em ambiente isolado e integridade pós-restauração.
- [ ] Definir e testar restart automático, se exigido.
- [ ] Registrar aceitação/tratamento de riscos, responsáveis e prazos.
- [ ] Validar HTTPS, gestão de credenciais, observabilidade e RPO/RTO aplicáveis.

**Conclusão:** governança e CI/CD apresentam evidências históricas positivas; o **encerramento técnico global da RC3 permanece condicionado**. Não declarar liberação para produção.

## 9. Documentos relacionados

- `ARQUITETURA.md`, `SEGURANCA.md`, `ROADMAP.md`, `TESTES_SEGURANCA.md`.
- `SECURE_INGESTION.md`, `SINCRONIZACAO_CONHECIMENTO.md`.
- `RUNBOOK_BACKUP_RESTORE_RC3.md` — rascunho não validado.
- `ESPECIFICACAO_DOC_001.md` — proposta futura, não implementada.
- `../README.md`, `../CHANGELOG.md`.

Toda atualização deve ocorrer em branch de trabalho e Pull Request, sem commits diretos nas branches protegidas. A IA não recebe permissão de escrita no source control.
