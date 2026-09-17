# Arquitetura — AI Knowledge

**Repositório:** `fgcneto/ia-rag-teste`  
**Versão de referência:** `v0.3.0`  
**Data de referência:** 17/09/2026  
**Estado:** MVP técnico em validação

## 1. Objetivo

O AI Knowledge é um assistente técnico corporativo destinado a responder perguntas sobre sistemas e documentação técnica autorizados.

O conhecimento dos sistemas não deve ser incorporado ao modelo de linguagem como fonte primária. Ele é recuperado sob demanda por RAG (Retrieval-Augmented Generation), respeitando o escopo de acesso do usuário.

Princípio arquitetural:

> Sem evidência recuperada de fonte autorizada, o assistente não deve completar a resposta usando conhecimento geral do modelo.

## 2. Visão geral

```text
Navegador
   |
   v
Django ASGI
   |-- autenticação / sessão / CSRF
   |-- perfis e ACL
   |-- seleção de sistemas
   |-- Security Guard
   |
   v
MCP Knowledge Server
   |-- actor_token assinado e de curta duração
   |-- revalidação de usuário
   |-- revalidação de ACL
   |
   v
RAG Service
   |-- embedding da pergunta
   |-- filtro por projetos autorizados
   |-- recuperação vetorial
   |
   +--> PostgreSQL + pgvector
   |
   v
Ollama
   |-- Qwen3 4B
   |-- nomic-embed-text
   |
   v
Output Guard
   |
   v
Streaming da resposta para o navegador
```

Serviços auxiliares:

```text
Redis -> Celery Worker / Beat
Presidio Analyzer -> capacidade preparada para DLP/PII
GitHub Provider -> fonte atual, somente leitura
GitLab Provider -> evolução futura para ambiente institucional
```

## 3. Componentes

| Componente | Tecnologia | Responsabilidade |
|---|---|---|
| Aplicação web | Django ASGI + Uvicorn | Autenticação, administração, UI, escopo e streaming |
| MCP | MCP / FastMCP | Fronteira padronizada de consulta ao conhecimento |
| RAG | Serviço Python próprio | Embeddings, recuperação, contexto e evidências |
| LLM | Ollama + Qwen3 4B | Geração local das respostas |
| Embeddings | `nomic-embed-text` | Representação vetorial do conhecimento |
| Banco | PostgreSQL + pgvector | Dados, ACL, chunks, vetores e auditoria |
| Jobs | Celery + Redis | Processamento e sincronizações assíncronas |
| Source control | GitHub Provider | Consulta read-only a repositórios |
| Privacidade | Security Guard / Presidio | Proteções contra PII, segredos e abuso |

## 4. Modelo de linguagem

O modelo configurado por padrão na v0.3.0 é:

```text
LLM: qwen3:4b
Runtime: Ollama
Execução: local
```

O modelo de embeddings é:

```text
nomic-embed-text
dimensão esperada: 768
```

Parâmetros padrão relevantes:

| Parâmetro | Valor |
|---|---:|
| `OLLAMA_CHAT_MODEL` | `qwen3:4b` |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` |
| `OLLAMA_NUM_CTX` | `4096` |
| `OLLAMA_NUM_PREDICT` | `192` |
| `OLLAMA_NUM_THREAD` | `8` |
| `RAG_TOP_K` | `3` |
| `RAG_MIN_SIMILARITY` | `0.48` |
| `RAG_MAX_CONTEXT_CHARS` | `4500` |
| `RAG_MAX_CHUNK_CHARS` | `1800` |

A configuração registrada no código deve ser diferenciada do modelo efetivamente carregado em runtime. No ambiente em execução, a confirmação pode ser feita com:

```bash
docker compose exec ollama ollama list
```

## 5. Autorização e seleção de sistemas

Existem dois perfis funcionais principais.

### Analista de Sistemas

Pode consultar todos os projetos habilitados.

### Desenvolvedor

Pode consultar somente projetos explicitamente atribuídos ao seu perfil.

Um Desenvolvedor sem projetos atribuídos não recebe acesso por padrão.

O usuário pode escolher consultar:

- todos os sistemas aos quais já possui autorização; ou
- um subconjunto desses sistemas.

A seleção realizada pelo navegador nunca concede autorização.

```text
Usuário
  ↓
ACL máxima do usuário
  ↓
sistemas selecionados
  ↓
validação server-side
  ↓
effective_project_ids
```

IDs manipulados pelo cliente que estejam fora da ACL devem ser rejeitados.

## 6. MCP

O Django não deve confiar simplesmente no escopo enviado ao MCP.

O fluxo implementado é:

```text
Django
  ↓
valida usuário e ACL
  ↓
gera actor_token assinado
  ↓
envia project_ids efetivos ao MCP
  ↓
MCP valida actor_token
  ↓
MCP recarrega usuário
  ↓
MCP recalcula ACL
  ↓
requested ⊆ allowed ?
  ├── não -> negar
  └── sim -> executar retrieval
```

O MCP é uma fronteira de integração e não substitui autorização.

## 7. RAG

A pergunta é convertida em embedding e comparada com `KnowledgeChunk`.

O filtro por projeto ocorre antes da recuperação vetorial:

```python
KnowledgeChunk.objects \
    .filter(project_id__in=allowed_ids) \
    .annotate(distance=CosineDistance("embedding", qvec)) \
    .order_by("distance")[:RAG_TOP_K]
```

Esse comportamento é uma propriedade de segurança: conteúdo não autorizado não deve ser recuperado e posteriormente “filtrado pelo LLM”.

O contexto recuperado deve ser tratado como dado não confiável, pois arquivos, README, Issues, Pull Requests e comentários podem conter prompt injection indireta.

## 8. Fontes de conhecimento

### Atual

GitHub.com, por meio do provider da aplicação.

A integração deve operar somente em leitura e ser limitada por allowlist.

### Futuro

GitLab Self-Managed institucional.

A abstração de provider foi criada para permitir a troca da fonte sem alterar a lógica principal do RAG.

Na v0.3.0, o GitLab Provider ainda não deve ser considerado operacional.

## 9. Estado da indexação na v0.3.0

A arquitetura já possui:

- modelo `KnowledgeChunk`;
- PostgreSQL/pgvector;
- geração de embedding da pergunta;
- recuperação vetorial;
- provider GitHub;
- leitura de metadados e fontes suportadas pelo provider.

Entretanto, o pipeline completo de ingestão ainda é uma etapa de evolução.

Estado esperado:

```text
GitHub
  ↓
coleta de conteúdo
  ↓
filtros de arquivos
  ↓
secret scanner
  ↓
DLP / PII
  ↓
sanitização
  ↓
chunking
  ↓
nomic-embed-text
  ↓
KnowledgeChunk
  ↓
pgvector
```

Esse pipeline deve ser concluído antes da homologação para uso institucional.

## 10. Serviços em containers

A composição inclui, conceitualmente:

```text
web
postgres
redis
ollama
worker
beat
mcp-knowledge
presidio-analyzer
```

Somente a aplicação web deve precisar de exposição externa.

PostgreSQL, Redis, Ollama e MCP devem permanecer em rede interna.

Em produção, o `web` deve ficar atrás de proxy reverso com HTTPS.

## 11. Princípios arquiteturais

1. O source control é somente leitura para a IA.
2. O LLM não decide autorização.
3. ACL é aplicada antes do retrieval.
4. MCP revalida a autorização.
5. Conteúdo de repositório é dado não confiável.
6. Sem evidência autorizada, não há resposta técnica afirmativa.
7. Segurança não depende exclusivamente de prompt.
8. Segredos e dados pessoais devem ser removidos antes da indexação sempre que não forem necessários.
9. Respostas devem manter rastreabilidade até as fontes utilizadas.
10. Alterações no Git permanecem sob controle humano.

## 12. Documentos relacionados

- `SEGURANCA.md`
- `ROADMAP.md`
- `../SECURITY.md`
- `../GIT_WORKFLOW.md`
- `Documentacao_Tecnica_AI_Knowledge_Django_MCP_v0.3.0.docx`
