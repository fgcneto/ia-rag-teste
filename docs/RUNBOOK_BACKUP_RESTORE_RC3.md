# Runbook preliminar — Backup, restore e continuidade RC3

> **Estado:** RASCUNHO NÃO VALIDADO — não executar restore em produção com base apenas neste arquivo.
> **Ambiente de referência:** Ubuntu com Podman rootless; confirmar a configuração real antes de qualquer intervenção.
> **Data:** 20/10/2026.

## 1. Objetivo e responsabilidades

Estabelecer um roteiro de **planejamento, diagnóstico e validação** de backup/restore do PostgreSQL/pgvector e de recuperação operacional. O responsável técnico deve aprovar a janela, definir o executor, identificar o banco de destino isolado e preservar as evidências. Este texto não comprova RPO, RTO, consistência de dumps nem reinício automático.

## 2. Pré-condições de segurança

- Confirmar incidente/objetivo, autorização formal e plano de retorno.
- Identificar host, usuário rootless, container, versão do PostgreSQL, banco e volume de **destino**; não presumir nomes ou caminhos.
- Registrar versões de imagens, schema/migrations, dependências e configuração necessária **sem imprimir segredos**.
- Confirmar que o backup existe, que há espaço livre e que a soma SHA-256 corresponde ao valor registrado em local seguro.
- Confirmar criptografia, permissões, retenção e acesso mínimo ao arquivo de backup.
- Criar ambiente **isolado** de recuperação, sem conexão de escrita com o banco de produção.
- Definir critérios de sucesso, tempo máximo aceitável e rollback; obter aprovação antes de qualquer operação mutável.

## 3. Inspeção não destrutiva — host Ubuntu da RC3

Executar no terminal do host correto, com o mesmo usuário rootless responsável pelos containers:

```bash
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
podman logs --tail 100 ai-knowledge-v031-rc3_postgres_1
podman logs --tail 100 ai-knowledge-v031-rc3_web_1
podman logs --tail 100 ai-knowledge-v031-rc3_worker_1
```

Logs podem conter informações sensíveis: revisar/redigir antes de compartilhar. Conferir também espaço livre, horário do host, estado dos volumes e serviços, sem modificar containers nem banco.

## 4. Verificação do arquivo de backup

Somente após identificar o **caminho exato** e verificar as permissões, executar em ambiente seguro:

```bash
sha256sum -- /caminho/privado/para/backup-validado.dump
```

O caminho acima é **placeholder**; não copiar literalmente. Comparar o resultado com o checksum obtido na criação do backup e guardado fora do dump. A igualdade do hash prova integridade de bytes, **não** restauração bem-sucedida ou consistência lógica.

## 5. Ensaio de restore em ambiente isolado — procedimento a detalhar

1. Preparar PostgreSQL compatível, com banco/volume de **teste** vazio e acesso restrito.
2. Selecionar ferramenta de restauração conforme formato real do backup (`pg_restore` para custom/directory/tar; `psql` para SQL plano). **Não** executar comandos de restauração antes de confirmar formato, versão, destino e autorização.
3. Registrar comandos aprovados no plano de mudança; executar somente no banco de teste.
4. Verificar erros e código de saída, extensões (incluindo pgvector), schemas, migrations, tabelas e contagens sintéticas/permitidas.
5. Realizar testes de aplicação em ambiente de teste: inicialização Django, consultas read-only, ACL, retrieval isolado e integridade dos índices, sem enviar dados pessoais a logs.
6. Documentar duração total, integridade, evidências sanitizadas, limitações e resultado do ensaio.
7. Encerrar o ensaio segundo política aprovada, preservando evidências sem expor dump ou segredos.

**Pendente:** comandos concretos, identificação do volume, formato do dump, versão exata do banco e critérios quantitativos devem ser obtidos do ambiente real; não foram incluídos no pacote documental.

## 6. Continuidade após reboot

A operação RC3 relatou reinício **manual** dos oito containers existentes após reboot, sem recriar volumes. Isso não comprova inicialização automática. Para testar uma política de restart, definir o mecanismo suportado pelo host (por exemplo, unidades de serviço administradas) e executar ensaio controlado com evidência antes/depois, verificando PostgreSQL, Redis, Celery, MCP, Ollama, Presidio e Django. Não alterar política de restart durante incidente sem mudança aprovada.

## 7. Registro de evidências e aceite

| Campo | Preencher durante o ensaio |
| --- | --- |
| Data/hora, executor, aprovador | Pendente |
| Host e ambiente isolado | Pendente |
| Commit, imagem, PostgreSQL/pgvector | Pendente |
| Arquivo de backup (identificador não sensível) e SHA-256 | Pendente |
| Formato, ferramenta, código de saída | Pendente |
| Integridade, migrations, testes de aplicação | Pendente |
| Duração e RPO/RTO alcançados | Pendente |
| Resultado, falhas, ações corretivas e aceite | Pendente |

Sem registro e aprovação dessas evidências, o critério de restore da RC3 permanece **não atendido**.
