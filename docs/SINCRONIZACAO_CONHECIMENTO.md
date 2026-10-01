# Sincronização da Base de Conhecimento

**Repositório:** `fgcneto/ia-rag-teste`

**Data de referência:** 30/09/2026

**Escopo:** operação e diagnóstico da sincronização assíncrona

## 1. Objetivo

Este documento descreve como operar, observar e diagnosticar a sincronização da base de conhecimento.

A arquitetura geral está em `ARQUITETURA.md` e os controles de segurança estão em `SEGURANCA.md`.

## 2. Configuração

A sincronização periódica é desabilitada por padrão.

```env
KNOWLEDGE_SYNC_ENABLED=false
KNOWLEDGE_SYNC_INTERVAL_SECONDS=3600
KNOWLEDGE_SYNC_STALE_AFTER_SECONDS=7200
```

- `KNOWLEDGE_SYNC_ENABLED`: habilita o agendamento pelo Celery Beat.
- `KNOWLEDGE_SYNC_INTERVAL_SECONDS`: intervalo entre os ticks periódicos.
- `KNOWLEDGE_SYNC_STALE_AFTER_SECONDS`: idade mínima para um `SyncJob` agendado ser candidato à recuperação operacional.

Os valores devem ser positivos.

## 3. Fluxo de execução

```text
Celery Beat
  ↓
scheduled_sync_tick
  ↓
reserve_scheduled_sync_job
  ↓
sync_repositories
  ↓
reserve_project_sync
  ↓
sync_project_run
  ↓
finalize_sync_job
```

O Beat dispara apenas o trigger. A ingestão ocorre nos workers Celery.

## 4. Estados

`SyncJob` representa o ciclo global:

```text
QUEUED
RUNNING
DONE
PARTIAL
FAILED
```

`ProjectSyncRun` representa a execução de um projeto:

```text
QUEUED
RUNNING
SKIPPED
DONE
FAILED
EXPIRED
```

`SKIPPED` indica que o SHA remoto já corresponde ao SHA indexado.

`EXPIRED` indica que a lease de uma execução perdeu validade e a execução foi encerrada pelo mecanismo de recuperação.

## 5. Exclusividade

O PostgreSQL é a fonte de verdade para os controles de concorrência.

A sincronização aplica duas regras independentes:

1. somente um `SyncJob` periódico ativo para `requested_by=celery-beat`;
2. somente um `ProjectSyncRun` ativo por projeto.

Execuções manuais não são bloqueadas pelo guard global do Beat, mas continuam sujeitas à exclusividade por projeto.

## 6. Incrementalidade

A incrementalidade atual é baseada no SHA do repositório.

Quando o SHA remoto é igual a `Project.last_repository_sha`, o run termina como `SKIPPED` antes de percorrer novamente a árvore do repositório, sanitizar os arquivos ou recalcular embeddings.

Delta incremental em nível de arquivo ainda não está implementado.

## 7. Leases e recuperação

Cada `ProjectSyncRun` ativo possui `lease_expires_at`.

A task de projeto utiliza uma lease maior que `CELERY_TASK_TIME_LIMIT`, com margem adicional de 300 segundos.

Um novo ciclo periódico não deve invalidar uma execução que ainda possua lease válida.

Quando um `SyncJob` agendado ultrapassa `KNOWLEDGE_SYNC_STALE_AFTER_SECONDS`, o sistema primeiro tenta reconciliar o job por `finalize_sync_job`. Isso cobre o caso em que todos os runs terminaram, mas a agregação final foi interrompida.

Se o job continuar ativo e existir run com lease válida, nenhuma recuperação é feita.

Se não existir run ativo com lease válida, runs ativos com lease expirada são marcados `EXPIRED`, o job antigo é encerrado como `FAILED` e um novo ciclo pode ser reservado.

## 8. Observabilidade

O Django Admin oferece consulta de `SyncJob` e `ProjectSyncRun`.

Esses registros são somente leitura no Admin.

Para `SyncJob`, observar principalmente:

- `status`;
- `requested_by`;
- `task_id`;
- `created_at`, `started_at`, `finished_at`;
- `result_json`;
- `error`.

Para `ProjectSyncRun`, observar principalmente:

- projeto e job pai;
- `status`;
- `task_id`;
- `target_sha`;
- `lease_expires_at`;
- timestamps;
- `result_json`;
- `error`.

## 9. Sincronização manual

Para disparar uma sincronização manual:

```bash
python manage.py sync_knowledge
```

Para reindexar mesmo quando o SHA não mudou:

```bash
python manage.py sync_knowledge --force
```

`--force` ignora a verificação de igualdade do SHA, mas não ignora a exclusividade por projeto.

## 10. Diagnóstico operacional

### 10.1 Verificar jobs periódicos ativos

No Django shell:

```python
from knowledge.models import SyncJob

SyncJob.objects.filter(
    requested_by="celery-beat",
    status__in=["QUEUED", "RUNNING"],
)
```

Em condição normal devem existir zero ou um job periódico ativo.

### 10.2 Verificar runs ativos

```python
from knowledge.models import ProjectSyncRun

ProjectSyncRun.objects.filter(
    status__in=["QUEUED", "RUNNING"],
)
```

Todo run ativo deve possuir `lease_expires_at`.

### 10.3 Verificar SHA indexado

```python
project.last_repository_sha
```

Se o SHA remoto for igual ao SHA persistido, a execução normal deve terminar como `SKIPPED`.

### 10.4 Falhas externas

Falhas como DNS temporário, timeout de conexão ou desconexão do provider devem aparecer como `FAILED` no job/run correspondente e não devem manter o guard global bloqueado indefinidamente.

Antes de alterar estado no banco, verificar:

- status do `SyncJob`;
- status e lease dos `ProjectSyncRun`;
- logs do worker;
- conectividade com PostgreSQL, Redis e provider;
- horário atual do Django (`timezone.now()`) ao comparar leases.

Não corrigir jobs manualmente no banco sem preservar primeiro as evidências de diagnóstico.

## 11. Segurança operacional

A sincronização não amplia as permissões do source control.

O provider e as tasks devem permanecer estritamente read-only.

Não devem ser fornecidos ao Worker ou ao Beat escopos com capacidade de alteração de repositórios.

Os requisitos completos estão em `SEGURANCA.md`.

## 12. Limitações atuais

Permanecem como evolução futura:

- delta incremental em nível de arquivo;
- retry específico por tipo de falha externa;
- métricas e dashboards dedicados;
- alertas operacionais externos;
- implementação completa do provider GitLab institucional.
