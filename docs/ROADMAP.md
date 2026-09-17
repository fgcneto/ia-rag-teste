# Roadmap — AI Knowledge

**Repositório:** `fgcneto/ia-rag-teste`  
**Versão base:** `v0.3.0`  
**Atualizado em:** 17/09/2026

## 1. Objetivo

Este documento registra evoluções planejadas para o AI Knowledge.

Itens deste arquivo são propostas ou trabalhos futuros e não devem ser interpretados como funcionalidades já disponíveis na versão v0.3.0.

## 2. Estado atual — v0.3.0

A base atual contém:

- Django ASGI;
- autenticação e administração;
- perfis Analista de Sistemas e Desenvolvedor;
- ACL por projeto;
- seleção pelo usuário de sistemas autorizados;
- MCP Knowledge Server;
- revalidação de ACL no MCP;
- PostgreSQL + pgvector;
- RAG;
- Ollama;
- `qwen3:4b`;
- `nomic-embed-text`;
- streaming de respostas;
- GitHub provider read-only;
- auditoria básica;
- Security Guard;
- estrutura para Celery/Redis;
- preparação para Presidio.

A v0.3.0 permanece um MVP técnico em validação.

## 3. Prioridade imediata — ingestão segura

A principal evolução é concluir o pipeline de indexação.

```text
GitHub / GitLab
      ↓
coleta de conteúdo autorizado
      ↓
filtros de caminho/extensão
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
PostgreSQL + pgvector
```

Requisitos:

- respeitar allowlist;
- nunca indexar projeto não autorizado à instância;
- excluir arquivos sensíveis;
- detectar segredos;
- detectar PII;
- registrar origem, branch e commit;
- permitir reindexação incremental;
- remover chunks obsoletos;
- manter rastreabilidade.

## 4. v0.3.1 — hardening e qualidade

Escopo sugerido:

- testes Django reais de ACL;
- testes de endpoint para 403;
- testes de isolamento entre Desenvolvedores;
- testes de Analista;
- testes de MCP;
- correção/configuração de `pytest-django`;
- Gitleaks no CI;
- Ruff;
- dependency scanning;
- SBOM;
- pinagem de GitHub Actions por commit SHA;
- melhorias no Django Admin para atribuição de projetos;
- auditoria administrativa;
- correlation/request ID.

## 5. v0.4.0 — ingestão e GitLab

Escopo possível:

- pipeline completo de ingestão segura;
- GitLab Self-Managed Provider;
- leitura de repositórios;
- Issues;
- Merge Requests;
- Wiki/documentação;
- commits;
- sincronização incremental;
- migração do CI para GitLab CI quando necessário.

A integração GitLab deve permanecer somente leitura.

## 6. Melhoria futura — geração de documentação técnica

O assistente poderá gerar documentação técnica a partir de um sistema selecionado pelo usuário.

A funcionalidade deverá respeitar a ACL existente.

```text
Usuário
   ↓
seleciona sistema autorizado
   ↓
MCP + ACL
   ↓
RAG
   ↓
código + README + documentação +
Issues + PR/MR + demais fontes permitidas
   ↓
análise
   ↓
documentação técnica proposta
   ↓
revisão humana
   ↓
download / cópia / aplicação manual no Git
```

### 6.1 Tipos de documentação

A geração poderá incluir:

- visão geral;
- arquitetura;
- módulos;
- componentes;
- APIs/endpoints;
- integrações;
- banco de dados;
- configuração;
- variáveis de ambiente sem revelar valores secretos;
- implantação;
- dependências;
- segurança;
- autenticação e autorização;
- troubleshooting;
- fluxos;
- diagramas;
- ADRs;
- runbooks.

### 6.2 Rastreabilidade

Toda documentação gerada deverá registrar:

```text
Sistema
Repositório
Branch
Commit analisado
Data/hora
Fontes utilizadas
Modelo LLM
Versão/política do assistente
```

Exemplo:

```text
Sistema: sistema-x
Branch: main
Commit: abc1234
LLM: qwen3:4b
Gerado em: 2026-09-17
```

Isso permitirá identificar exatamente qual versão do sistema fundamentou o documento.

### 6.3 Evidências

Afirmações técnicas devem possuir evidência recuperável.

Exemplo:

```text
[IDENTIFICADO NO CÓDIGO]
A API utiliza autenticação JWT.

Fonte:
src/security/auth.py
commit: abc1234
```

O LLM não deve inventar uma seção técnica quando não houver evidência suficiente.

## 7. Melhoria futura — revisão da documentação existente

Além de gerar documentos, o assistente poderá comparar a documentação existente com a implementação atual.

Fontes possíveis:

```text
README
docs/
Wiki
código
configurações
API
Issues
PR/MR
commits
```

O objetivo será apontar divergências e lacunas.

Exemplos:

- endpoint existente no código e ausente na documentação;
- endpoint documentado que não existe mais;
- variável de ambiente não documentada;
- dependência alterada;
- procedimento de deploy desatualizado;
- integração não descrita;
- módulo novo sem documentação;
- exemplo incompatível com a implementação;
- seção de segurança incompleta;
- referência a versão antiga.

## 8. Formato das sugestões de documentação

O assistente deve separar fatos de recomendações.

Formato sugerido:

```text
[IDENTIFICADO NO CÓDIGO]
O endpoint /api/v1/paciente exige autenticação JWT.

Fonte:
src/api/paciente.py

[DOCUMENTAÇÃO ATUAL]
O README não descreve o mecanismo de autenticação.

Fonte:
README.md

[SUGESTÃO]
Adicionar uma seção "Autenticação da API" explicando o fluxo JWT.
```

Uma sugestão produzida pelo LLM nunca deve ser apresentada como característica confirmada do sistema.

## 9. Controle humano sobre documentação

Mesmo após a implementação dessa funcionalidade, o princípio read-only deve permanecer.

A IA poderá:

```text
gerar Markdown
gerar DOCX/PDF
gerar diagramas
produzir diff sugerido
produzir patch para download
sugerir texto para README
```

A IA não deverá:

```text
alterar o repositório diretamente
fazer commit automaticamente
fazer push automaticamente
aprovar PR/MR
fazer merge
alterar branch protegida
```

A aplicação da mudança permanecerá sob decisão humana.

## 10. Documentação como artefato versionável

Documentos técnicos textuais devem preferencialmente ser mantidos em Markdown:

```text
docs/
├── ARQUITETURA.md
├── SEGURANCA.md
├── ROADMAP.md
└── ...
```

DOCX/PDF podem existir como artefatos institucionais, mas Markdown facilita:

- diff;
- revisão;
- Pull Request / Merge Request;
- histórico;
- blame;
- pesquisa;
- manutenção junto ao código.

## 11. SSO e identidade corporativa

Evolução futura possível:

- LDAP/Active Directory;
- OIDC;
- SSO corporativo;
- sincronização de grupos;
- mapeamento grupo -> perfil/projeto;
- desativação automática de acessos.

A ACL final deve continuar sendo validada server-side.

## 12. Auditoria e observabilidade

Evoluções:

- SIEM;
- métricas;
- tracing;
- request/correlation ID;
- dashboards;
- alertas de segurança;
- alertas de falha de sincronização;
- histórico de indexação;
- retenção formal;
- auditoria de mudanças de ACL.

## 13. Administração de acesso

Melhorias futuras:

- atribuição múltipla de projetos por UI;
- grupos de acesso;
- projetos por equipe;
- expiração de acesso;
- justificativa para concessão;
- aprovação;
- revisão periódica;
- relatório de permissões.

## 14. Fine-tuning

Fine-tuning não é prioridade para armazenar conhecimento dos repositórios.

Conhecimento que muda frequentemente deve permanecer em RAG.

Fine-tuning poderá ser avaliado posteriormente para comportamentos estáveis, por exemplo:

- padrão de resposta;
- classificação;
- formato de incidentes;
- ADR;
- Known Issue;
- Runbook;
- concisão;
- disciplina de citação.

Fine-tuning nunca substituirá:

- ACL;
- DLP;
- secret scanning;
- prompt injection guard;
- output guard;
- evidências;
- system prompt;
- revisão humana.

## 15. Critérios para promover funcionalidades

Uma funcionalidade que envolva conhecimento corporativo deve passar por:

```text
desenvolvimento
   ↓
testes automatizados
   ↓
testes de ACL
   ↓
testes de segurança
   ↓
testes com dados sintéticos
   ↓
homologação
   ↓
documentação
   ↓
produção
```

## 16. Princípios que o roadmap não pode violar

Toda evolução deve preservar:

1. Source control read-only para a IA.
2. Menor privilégio.
3. Deny by default.
4. ACL antes do retrieval.
5. Revalidação no MCP.
6. Conteúdo recuperado tratado como não confiável.
7. Segredos e PII protegidos antes da indexação.
8. Respostas técnicas baseadas em evidências.
9. Auditoria.
10. Controle humano sobre mudanças no Git.
