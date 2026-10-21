# Secure Knowledge Ingestion

## Objetivo

Indexar somente conteúdo textual dos repositórios explicitamente autorizados em `GITHUB_ALLOWED_REPOSITORIES`, impedindo que segredos e PII desnecessária cheguem ao banco vetorial.

## Fluxo

```text
GitHub allowlist -> metadata/commit -> tree -> path/size filter -> raw content
 -> secret scan -> PII masking (local + Presidio) -> chunking
 -> nomic-embed-text -> atomic replacement of repository_file chunks -> pgvector
```

## Garantias do MVP

- o provider GitHub enumera somente a allowlist;
- arquivos sensíveis, binários, backups, dumps e artefatos são descartados antes da leitura/indexação;
- um arquivo com padrão de segredo é bloqueado integralmente;
- CPF/e-mail são mascarados localmente antes do embedding;
- com `PRESIDIO_ENABLED=true`, o Analyzer complementa a sanitização;
- com `PRESIDIO_FAIL_CLOSED=true`, falha no DLP interrompe a indexação e preserva o índice anterior;
- o índice só é substituído em transação após coleta, sanitização e embeddings concluírem;
- `last_repository_sha` evita reindexação sem mudança;
- cada chunk registra projeto, caminho, branch, commit, URL, hash e índice;
- a recuperação continua filtrada por `project_id` autorizado.

## Execução manual

```powershell
docker compose --env-file .env -f compose.yaml -f compose.dev.yaml exec web python manage.py sync_knowledge
```

Para reindexar mesmo sem mudança de SHA:

```powershell
docker compose --env-file .env -f compose.yaml -f compose.dev.yaml exec web python manage.py sync_knowledge --force
```

## Validação

Após a execução, confira projetos e chunks sem exibir o conteúdo indexado:

```powershell
docker compose --env-file .env -f compose.yaml -f compose.dev.yaml exec web python manage.py shell -c "from knowledge.models import Project; print(list(Project.objects.values('id','path_with_namespace','last_repository_sha','indexed_at')))"
```

Para contagem por projeto, prefira:

```powershell
docker compose --env-file .env -f compose.yaml -f compose.dev.yaml exec web python manage.py shell -c "from django.db.models import Count; from knowledge.models import KnowledgeChunk; print(list(KnowledgeChunk.objects.values('project_id').annotate(chunks=Count('id')).order_by('project_id')))"
```

## Limites

Este incremento indexa **arquivos do repositório**. Issues e Pull Requests permanecem fora do pipeline. A detecção de segredos por regex é uma camada mínima; Gitleaks ou ferramenta equivalente continua recomendada antes de produção. O Presidio precisa ser calibrado e validado para os tipos de PII e idioma do ambiente institucional.

## Revisão RC3 — limites de comprovação

As instruções acima descrevem o ambiente de desenvolvimento **Docker Compose**. A operação local da RC3 relatada no encerramento utilizou **Podman rootless** em Ubuntu; os comandos não devem ser transpostos automaticamente sem identificar arquivos Compose, diretório de execução, nomes de serviço e configuração efetiva. Esta revisão não executou a ingestão nem confirmou contagens no banco.

A proposta DOC-001 de inspeção documental externa permanece **não implementada** e não amplia o escopo das fontes ingeridas. A geração de relatórios ou patches deve ocorrer sem conceder permissão de escrita ao provider.
