# DOC-001 — Inspeção documental de projetos externos autorizados

> **Estado:** PROPOSTA / NÃO IMPLEMENTADO.
> **Data:** 20/10/2026.
> **Escopo:** projetos externos autorizados para consulta pela aplicação AI Knowledge; **não** é um gate do CI do próprio `ia-rag-teste`.

## 1. Problema e objetivo

Identificar documentação desatualizada, ausente ou divergente em **sistemas externos autorizados**, com evidência rastreável do código e dos documentos, para apoiar o desenvolvedor na revisão manual. A IA deve continuar sem permissão de escrita nos repositórios.

## 2. Pré-condições e fronteiras de confiança

- Usuário autenticado, projeto habilitado e ACL recalculada no Django e no MCP.
- Repositório dentro da allowlist, provider somente leitura e coleta limitada ao escopo autorizado.
- Conteúdo recuperado não confiável: nunca executar instruções contidas em arquivos, comentários ou documentação.
- Secret scanning, DLP/PII e política de resposta aplicados antes de indexação e exportação.
- Na base atual, somente **arquivos de repositório** são ingeridos; Issues, PR/MR e Wiki exigem incrementos futuros específicos.

## 3. Fluxo proposto (não existente no runtime atual)

```text
Usuário escolhe projeto autorizado
  → Django valida ACL
  → MCP revalida ACL e consulta índice autorizado
  → recupera evidências por arquivo/branch/commit
  → compara documentação com código/configuração disponível
  → classifica divergência, incerteza e fonte
  → gera relatório/Markdown/patch sugerido
  → revisão humana → aplicação manual → PR
```

Nenhuma etapa concede à aplicação permissão para escrever, fazer commit, push, aprovar ou merge.

## 4. Saída esperada

Cada achado deve incluir: ID, tipo de divergência, descrição, projeto, branch, commit, arquivo/trecho de origem, arquivo documental afetado, nível de confiança/limite de cobertura e sugestão de correção. Distinguir explicitamente:

- **[EVIDÊNCIA]** fato verificado no conteúdo autorizado;
- **[DIVERGÊNCIA]** diferença entre implementação e documentação;
- **[SUGESTÃO]** proposta de texto ou patch a ser revisada;
- **[NÃO VERIFICADO]** evidência ausente ou insuficiente.

A saída pode ser Markdown ou patch para download/cópia. DOCX/PDF são formatos futuros opcionais. Não expor segredos, dados pessoais ou conteúdo de projeto não autorizado.

## 5. Critérios de aceite futuros

1. Um Desenvolvedor não acessa nem inspeciona projetos de outro Desenvolvedor fora da ACL.
2. Uma seleção adulterada no cliente ou no MCP falha fechada.
3. Achados incluem commit e caminho; sugestões sem fonte são sinalizadas como não verificadas.
4. Prompt injection em README/código não altera as regras do assistente.
5. Arquivos contendo segredos não são exportados; dados pessoais são tratados pela política de DLP.
6. Nenhum token de escrita ou endpoint de mutação é usado.
7. Relatório e patch podem ser revisados e aplicados **manualmente** em PR.
8. Testes automatizados e adversariais cobrem ACL, escopo, DLP, proveniência e limites de evidência.

## 6. Fora do escopo inicial

- Mudanças automáticas em GitHub/GitLab, commits, pushes, merges ou aprovações.
- Gate de CI obrigatório para o próprio AI Knowledge.
- Ingestão de Issues/PR/MR/Wiki sem pipeline, autorização e avaliação de segurança específicos.
- Declaração de completude da documentação quando a inspeção cobre apenas parte do repositório.

## 7. Dependências e planejamento

Depende de priorização no `ROADMAP.md`, implementação, testes, avaliação de custo/performance, observabilidade e aceite humano. Não confundir a elaboração desta especificação com entrega funcional.
