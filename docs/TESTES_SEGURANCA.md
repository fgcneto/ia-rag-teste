# Relatório de Testes de Segurança

## 1. Objetivo

Este documento registra as verificações de segurança executadas no projeto
AI Django MCP (`ia-rag-teste`) e as evidências obtidas durante os testes.

Seu objetivo é fornecer rastreabilidade técnica dos controles utilizados para:

- restringir o acesso aos repositórios autorizados;
- impedir acesso a projetos fora do escopo do usuário;
- reduzir o risco de ingestão de segredos;
- reduzir o risco de persistência de dados pessoais em claro;
- impedir que arquivos explicitamente sensíveis sejam indexados;
- garantir que sanitização ocorra antes da geração de embeddings;
- validar a integridade da persistência no PostgreSQL/pgvector;
- validar comportamento fail-closed dos controles de segurança;
- manter o acesso ao provedor de código-fonte em modo somente leitura.

Este relatório não constitui prova de segurança absoluta.

Um resultado `PASS` significa que o controle apresentou o comportamento esperado
nos cenários, dados, versão e ambiente descritos neste documento. Não significa
que todas as classes possíveis de vulnerabilidade, segredo ou dado pessoal
tenham sido eliminadas.

---

## 2. Ambiente validado

Data da validação: 2026-09-26

Repositório:

    fgcneto/ia-rag-teste

Branch remota utilizada:

    main

Commit ingerido:

    d9b485efce7e28000c5cfc6f0df2034171d0fd35

Componentes principais:

- Django 5.2
- PostgreSQL + pgvector
- Redis
- Celery 5.5
- Ollama
- nomic-embed-text
- qwen3:4b
- Microsoft Presidio Analyzer
- MCP
- Podman / podman-compose

Dimensão esperada dos embeddings:

    768

---

## 3. Modelo de segurança

A arquitetura adota como princípio:

> A IA é uma ferramenta de consulta técnica dos sistemas autorizados.
> Ela não é um chatbot de propósito geral e não possui capacidade de
> alteração no repositório de código-fonte.

As decisões de autorização não devem depender exclusivamente do modelo de
linguagem.

O pipeline de conhecimento validado segue conceitualmente:

    Source Control
        |
        v
    Allowlist
        |
        v
    Filtro de arquivos
        |
        v
    Secret scanning
        |
        v
    PII / Presidio
        |
        v
    Sanitização
        |
        v
    Chunking
        |
        v
    Embedding
        |
        v
    PostgreSQL / pgvector

---

## 4. Matriz de verificações executadas

| ID | Controle | Resultado |
|---|---|---|
| SEC-001 | `.env` excluído do versionamento | PASS |
| SEC-002 | arquivos swap do editor excluídos | PASS |
| SEC-003 | allowlist de repositórios | PASS |
| SEC-004 | acesso read-only ao GitHub | PASS |
| SEC-005 | credencial não exposta durante validação | PASS |
| SEC-006 | ACL no endpoint HTTP | PASS |
| SEC-007 | ACL no MCP | PASS |
| SEC-008 | acesso MCP autorizado | PASS |
| SEC-009 | filtro de arquivos na ingestão | PASS |
| SEC-010 | secret scanning básico | PASS* |
| SEC-011 | Presidio disponível e funcional | PASS |
| SEC-012 | sanitização anterior ao embedding | PASS |
| SEC-013 | embeddings com 768 dimensões | PASS |
| SEC-014 | persistência pgvector | PASS |
| SEC-015 | ausência de paths proibidos após ingestão | PASS |
| SEC-016 | ausência dos padrões de segredo auditados | PASS* |
| SEC-017 | ausência de e-mails em claro na auditoria | PASS* |
| SEC-018 | ausência de CPF em claro na auditoria | PASS* |
| SEC-019 | idempotência por SHA | PASS |
| SEC-020 | integridade dos chunks em reprocessamento | PASS |

`PASS*` indica que a validação depende do conjunto de padrões atualmente
implementado e não representa cobertura universal.

---

## 5. Proteção de segredos locais

### SEC-001 — `.env`

Verificação realizada com `git check-ignore`.

Resultado:

    .env -> ignorado pelo Git

Status:

    PASS

O `.env` contém configuração local e pode conter credenciais. Ele não deve ser
adicionado ao repositório.

### SEC-002 — arquivos temporários do editor

Foi identificado:

    ..env.swp

O `.gitignore` foi atualizado para incluir:

    *.swp
    *.swo

Após a alteração, `git check-ignore` confirmou que o arquivo swap passou a ser
ignorado.

Status:

    PASS

---

## 6. Restrição do Source Control

### SEC-003 — allowlist

Configuração validada no container:

    SOURCE_PROVIDER = github
    GITHUB_ALLOWED_REPOSITORIES = ['fgcneto/ia-rag-teste']
    ALLOWLIST_COUNT = 1

Status:

    PASS

### SEC-004 — acesso read-only

O provider realizou com sucesso operações de leitura para:

- obter metadados do repositório;
- consultar a branch `main`;
- obter o commit;
- obter a árvore recursiva.

Resultados:

    REPOSITORIES_RETURNED = 1
    FULL_NAME = fgcneto/ia-rag-teste
    DEFAULT_BRANCH = main
    COMMIT_SHA = d9b485efce7e28000c5cfc6f0df2034171d0fd35
    TREE_ITEMS = 109
    BLOBS = 82
    RESULTADO = GITHUB_READONLY_OK

Status:

    PASS

A credencial utilizada deve permanecer limitada às permissões estritamente
necessárias de leitura.

---

## 7. Controle de acesso

### SEC-006 — ACL HTTP

Foi validada tentativa de acesso de usuário Developer a projeto fora de seu
escopo autorizado.

Resultado:

    HTTP 403

Status:

    PASS

### SEC-007 — ACL MCP

Foi realizada tentativa de consulta MCP utilizando projeto fora do conjunto
permitido ao ator.

Resultado:

    PermissionError:
    Escopo MCP contém projeto não autorizado.

Status:

    PASS

### SEC-008 — caminho autorizado

Consulta com projeto pertencente ao escopo autorizado ultrapassou corretamente
a camada ACL.

Status:

    PASS

---

## 8. Ingestão segura

Foi realizada ingestão controlada exclusivamente do repositório:

    fgcneto/ia-rag-teste

Resultados:

    project_id = 2
    repository = fgcneto/ia-rag-teste
    sha = d9b485efce7e28000c5cfc6f0df2034171d0fd35

    files_seen = 82
    files_indexed = 60
    files_skipped = 22
    files_secret_blocked = 0
    chunks_written = 94
    unchanged = False

    CHUNKS_AFTER = 94
    RESULTADO = CONTROLLED_INGESTION_OK

Status:

    PASS

O valor `files_secret_blocked = 0` significa que nenhum arquivo desse snapshot
acionou os padrões de segredo implementados. Ele não demonstra, isoladamente,
ausência universal de segredos.

---

## 9. Auditoria pós-ingestão

Após a persistência, foi executada auditoria read-only sobre os chunks.

Resultados:

    TOTAL_CHUNKS = 94
    UNIQUE_SOURCE_PATHS = 60

    WRONG_VECTOR_DIMENSIONS = 0
    BLOCKED_PATHS_FOUND = 0
    SECRET_PATTERN_HITS = 0
    RAW_EMAIL_HITS = 0
    RAW_CPF_HITS = 0

    RESULTADO = POST_INGEST_AUDIT_OK

Todos os 94 chunks auditados apresentaram dimensão de embedding igual a 768.

Nenhum path explicitamente proibido pelo teste foi encontrado.

Nenhum dos padrões de segredo, CPF ou e-mail utilizados nessa auditoria foi
encontrado em claro nos chunks persistidos.

Status:

    PASS

Limitação:

Os resultados são válidos para os detectores e expressões avaliados. Eles não
constituem prova da inexistência de qualquer tipo possível de segredo ou PII.

---

## 10. Idempotência

Uma segunda ingestão foi executada sem alteração do SHA remoto.

Antes:

    SHA = d9b485efce7e28000c5cfc6f0df2034171d0fd35
    CHUNK_COUNT = 94

Segunda execução:

    files_seen = 0
    files_indexed = 0
    files_skipped = 0
    files_secret_blocked = 0
    chunks_written = 0
    unchanged = True

Depois:

    CHUNK_COUNT = 94
    IDS_HASHES_UNCHANGED = True
    INDEXED_AT_UNCHANGED = True

Resultado:

    RESULTADO = INGESTION_IDEMPOTENCY_OK

Status:

    PASS

Esse teste demonstra que, para o SHA avaliado, o pipeline interrompe o
reprocessamento após identificar que a versão já foi indexada.

---

## 11. Presidio e proteção de PII

Foram realizados:

- health check do Presidio;
- chamada funcional ao analyzer;
- detecção de e-mail fictício;
- validação da configuração fail-closed;
- auditoria pós-ingestão para CPF e e-mail em claro.

Configuração relevante:

    PRESIDIO_ENABLED = True
    PRESIDIO_FAIL_CLOSED = True
    PRESIDIO_LANGUAGE = en

Status:

    PASS

A indisponibilidade efetiva do Presidio ainda deverá ser exercitada por teste
adversarial específico para comprovar o comportamento fail-closed do pipeline.

---

## 12. Embeddings e pgvector

Modelo:

    nomic-embed-text

Dimensão retornada:

    768

O campo Django foi validado como:

    pgvector.django.vector.VectorField

Dimensão:

    768

Também foi realizado teste transacional contendo:

- geração de embedding;
- persistência temporária;
- leitura;
- `CosineDistance`;
- rollback.

Resultado:

    RESULTADO = PGVECTOR_TRANSACTION_OK

Status:

    PASS

---

## 13. Testes automatizados

A suíte existente foi executada em ambiente isolado.

Resultado:

    16 passed

Status:

    PASS

Esse resultado representa a suíte existente no momento da validação. Novos
testes adversariais deverão ampliar essa cobertura.

---

## 14. Limitações conhecidas

### 14.1 Secret scanner

O scanner atual utiliza padrões conservadores para algumas classes de segredo.

Ele não substitui uma solução especializada de secret scanning.

Hardening planejado:

    Gitleaks ou ferramenta equivalente

### 14.2 Cobertura de PII

CPF e e-mail foram explicitamente avaliados na auditoria atual.

Outras categorias de PII dependem da cobertura do Presidio, idioma,
configuração e recognizers disponíveis.

### 14.3 Segurança absoluta

Nenhum teste deste documento deve ser interpretado como garantia de que:

- o sistema seja invulnerável;
- todos os tipos de segredo sejam detectados;
- todo tipo de PII seja detectado;
- nenhuma vulnerabilidade futura possa ser introduzida;
- nenhuma dependência possua vulnerabilidade.

O objetivo é manter controles verificáveis e regressões automatizadas.

---

## 15. Testes adversariais pendentes

Antes da liberação definitiva do fluxo automático de sincronização deverão ser
avaliados, quando aplicáveis:

- arquivo `.env`;
- arquivo `.env.production`;
- private key fictícia;
- GitHub token fictício;
- AWS access key fictícia;
- CPF fictício;
- e-mail fictício;
- arquivo acima do limite de ingestão;
- path pertencente a diretório proibido;
- indisponibilidade do Presidio;
- tentativa de acesso a projeto não autorizado;
- manipulação de `project_ids`;
- tentativa equivalente através do MCP;
- conteúdo contendo prompt injection;
- validação de que conteúdo do repositório é tratado como dado não confiável.

---

## 16. Hardening planejado

Itens recomendados para evolução:

1. Gitleaks no CI;
2. dependency scanning;
3. geração de SBOM;
4. Ruff no CI;
5. `makemigrations --check`;
6. testes de ACL com banco real;
7. testes HTTP de autorização;
8. testes MCP de autorização;
9. testes adversariais automatizados da ingestão;
10. pin de GitHub Actions por SHA;
11. revisão periódica das permissões do service account;
12. revisão periódica da allowlist.

---

## 17. Critério de regressão

Uma alteração deverá bloquear promoção/merge quando provocar falha em controle
de segurança obrigatório, incluindo, quando automatizado:

    pytest
    migration check
    secret scan
    ACL tests
    ingestion security tests

Falhas de segurança não devem ser contornadas com desativação temporária dos
controles para permitir o merge.

---

## 18. Histórico

### 2026-09-26

Primeira versão formal do relatório.

Incluídas evidências de:

- proteção do `.env`;
- allowlist;
- GitHub read-only;
- ACL HTTP;
- ACL MCP;
- Presidio;
- ingestão segura;
- embedding;
- pgvector;
- auditoria pós-ingestão;
- idempotência;
- suíte pytest.

Próxima etapa:

    testes adversariais controlados

---

## 19. Testes adversariais automatizados

Data: 2026-09-26

Foi ampliada a suíte de segurança da ingestão com dados exclusivamente
sintéticos.

Foram exercitados:

- arquivos e diretórios explicitamente sensíveis;
- limite máximo de tamanho;
- private keys sintéticas;
- GitHub tokens sintéticos;
- GitHub fine-grained PAT sintético;
- AWS access key sintética;
- referências legítimas a variáveis de ambiente;
- CPF fictício;
- e-mail fictício;
- bloqueio de conteúdo contendo segredo;
- sanitização local anterior à ingestão;
- Presidio indisponível em modo fail-closed;
- Presidio indisponível em modo fail-open;
- comportamento do chunking.

Resultado:

    16 tests collected
    16 passed

Status:

    SEC-021 — PASS

Observação:

Nenhuma credencial real foi utilizada como fixture dos testes.

---

## 20. Sanitização na fronteira do embedding

Foi criado teste de integração do pipeline utilizando provider e embedding
sintéticos.

O teste forneceu ao pipeline:

- e-mail fictício em claro;
- CPF fictício em claro.

O embedding foi substituído por implementação controlada capaz de registrar
exatamente o conteúdo recebido.

Resultado:

- e-mail original não chegou ao embedding;
- CPF original não chegou ao embedding;
- `[EMAIL-MASCARADO]` chegou ao embedding;
- `[CPF-MASCARADO]` chegou ao embedding;
- e-mail original não foi persistido;
- CPF original não foi persistido;
- conteúdo mascarado foi persistido.

Status:

    SEC-022 — sanitização antes do embedding — PASS
    SEC-023 — PII em claro ausente da persistência — PASS

Escopo da evidência:

O teste demonstra o comportamento para CPF e e-mail cobertos pelos detectores
atuais. Não representa cobertura universal de todas as categorias de PII.

---

## 21. Falha segura para embedding dimensionalmente inválido

Foi criado um projeto sintético contendo um chunk previamente válido.

Em seguida, uma nova ingestão foi executada utilizando embedding sintético com:

    dimensão retornada = 767
    dimensão esperada = 768

Resultado esperado e observado:

    RuntimeError

Após a falha foram verificados:

- `last_repository_sha` anterior preservado;
- chunk anterior preservado;
- ID anterior preservado;
- conteúdo anterior preservado;
- referência anterior preservada;
- nenhum replace da base válida.

Status:

    SEC-024 — embedding dimensional inválido bloqueado — PASS
    SEC-025 — estado persistido preservado após falha — PASS

---

## 22. Regressão completa

Após a inclusão dos testes adversariais e dos testes de segurança do pipeline,
foi executada a suíte completa sobre o checkout atual.

Resultado:

    29 tests collected
    29 passed
    2 warnings
    tempo = 8.09s

Status:

    PASS

Os warnings observados foram:

1. tentativa de teardown do banco `test_ai_knowledge` enquanto ainda existia
   uma sessão transitória;
2. impossibilidade de criação de `.pytest_cache`, pois o checkout foi
   deliberadamente montado read-only no container de teste.

Uma inspeção posterior de `pg_stat_activity` não encontrou sessões residuais
em `test_ai_knowledge`.

Esses warnings não produziram falha nos testes.

---

## 23. Integridade Django e migrations

Também foram executados:

    python manage.py check

Resultado:

    System check identified no issues (0 silenced).

E:

    python manage.py makemigrations --check --dry-run

Resultado:

    No changes detected

Status:

    Django system check — PASS
    Migration consistency — PASS

---

## 24. Estado dos gates de segurança

Situação após esta rodada:

    Proteção local de segredos              PASS
    GitHub allowlist                        PASS
    GitHub read-only                        PASS
    ACL HTTP                                PASS
    ACL MCP                                 PASS
    Filtro de paths                         PASS
    Secret scanner básico                   PASS*
    PII local                               PASS
    Presidio                                PASS
    Presidio fail-closed                    PASS
    Sanitização antes do embedding          PASS
    Persistência sanitizada                 PASS
    Embedding 768d                          PASS
    Embedding dimensional inválido          BLOQUEADO
    Preservação do estado após falha        PASS
    Auditoria pós-ingestão                  PASS
    Idempotência por SHA                    PASS
    Suíte completa                          29/29 PASS
    Django system check                     PASS
    Migration consistency                   PASS

`PASS*` permanece condicionado à cobertura limitada do scanner de segredos
atual. Gitleaks ou ferramenta equivalente continua previsto como hardening.

Próximos gates:

    CI security gates
    prompt injection / trust boundary
    sync_knowledge controlado
