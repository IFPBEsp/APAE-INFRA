# Matriz de comunicação do cluster

Os fluxos desta matriz descrevem a configuração prevista para os produtos. As imagens Docker estão disponíveis, mas os workloads dos produtos ainda não foram ativados no cluster. A conectividade será validada após a ativação.

## APAE Atendimento (`apae-dev`)

| Origem | Destino | Porta | Finalidade | Evidência |
| --- | --- | --- | --- | --- |
| Data plane do Gateway | `atendimento-app` | `3000/TCP` | Servir o frontend e receber `/atendimento/api` | Rota a confirmar na #113 |
| Pod `app=atendimento-app` | `atendimento` (`app=atendimento`) | `8080/TCP` | Encaminhar chamadas à API pelo Next.js | Confirmado no workflow de build e nos manifests |
| Pod `app=atendimento` | Banco configurado por `DB_URL` | A confirmar | Persistência da aplicação | Destino efetivo pendente |
| Pod `app=atendimento` | Storage S3 configurado por `S3_ENDPOINT` | A confirmar | Armazenamento de arquivos | Destino efetivo pendente |

Em 11/11/2026, o Deployment `atendimento` tinha zero réplicas desejadas.
Os testes de conectividade do backend no cluster estão pendentes.

## Gestão Escolar (`apae-dev`)

| Origem | Destino | Porta | Finalidade | Evidência |
| --- | --- | --- | --- | --- |
| Data plane do Gateway | `gestao-escolar-frontend` | `3000/TCP` | Servir `/gestao-escolar` | Rota a confirmar na #113 |
| Pod `app=gestao-escolar-frontend` | `gestao-escolar-backend` | `8080/TCP` | Encaminhar chamadas a `/gestao-escolar/api` pelo Next.js | Rewrite e URL confirmados no código e no workflow de build. Uso no cluster depende da rota da #113 |
| Pod `app=gestao-escolar-backend` | Banco configurado por `DATASOURCE_URL` | A confirmar | Persistência da aplicação | Destino efetivo pendente |
| Pod `app=gestao-escolar-backend` | MinIO configurado por `MINIO_URL` | A confirmar | Armazenamento de arquivos | Destino efetivo pendente |

## APAE Geral (`apae-dev`)

| Origem | Destino | Porta | Finalidade | Evidência |
| --- | --- | --- | --- | --- |
| Data plane do Gateway | `apae` | `3000/TCP` | Servir `/apae-geral`, incluindo os Route Handlers de `/apae-geral/api` | Rota a confirmar na #113 |
| Pod `app=apae` | `api` | `8080/TCP` | Chamar o backend a partir do servidor Next.js | `API_URL` aponta para o Service interno |
| Pod `app=api` | PostgreSQL configurado por `DB_URL` | A confirmar | Persistência da aplicação | Destino efetivo pendente |
| Pod `app=api` | MinIO configurado por `MINIO_URL` | A confirmar | Armazenamento de documentos | Destino efetivo pendente |
| Navegador | Endpoint de objetos configurado por `MINIO_PUBLIC_URL` | A confirmar | Abrir documentos por URL pré-assinada | Uso confirmado no código. Endereço e caminho de acesso pendentes |

O Service `management-app` declara `3000/TCP`. O Deployment tem zero réplicas
e referencia `management-app:unpublished`. Os fluxos desse componente ainda
estão a definir.

## Site Comemorativo (`apae-dev`)

| Origem | Destino | Porta | Finalidade | Evidência |
| --- | --- | --- | --- | --- |
| Data plane do Gateway | `site-comemorativo` | `3000/TCP` | Servir páginas e API do Next.js sob `/site-comemorativo` | Service confirmado. Rota e URLs da API a validar na #113 |
| Pod `app=site-comemorativo` | PostgreSQL configurado por `DATABASE_URL` | A confirmar | Persistência via Prisma | Dependência confirmada. Destino efetivo pendente |
| Pod `app=site-comemorativo` | Vercel Blob | `443/TCP` (HTTPS) | Enviar arquivos da linha do tempo | Integração confirmada no código. Acesso a validar |
| Pod `app=site-comemorativo` | SMTP do Gmail | A confirmar | Enviar e-mails pelo formulário | Integração confirmada no código. Acesso a validar |

O link para `/apae-geral` é seguido pelo navegador e não requer comunicação
entre os pods `site-comemorativo` e `apae`.

## Infraestrutura compartilhada

| Origem | Destino | Porta | Finalidade | Evidência |
| --- | --- | --- | --- | --- |
| Pods de aplicação | CoreDNS (`kube-dns`, `kube-system`) | `53/UDP` e `53/TCP` | Resolver nomes de Services e destinos externos | Confirmar Service e seletores antes de aplicar restrições de saída |
| Coletor autorizado pela #116 | Endpoints de métricas do Gateway | `9113/TCP` | Coletar métricas por acesso interno | Porta registrada na #111. Identidade do coletor a definir na #116 |
| Administrador autorizado | `argocd-server` (`argocd`) | `443/TCP` no Service | Acessar a interface via túnel SSH e port-forward em loopback | Procedimento documentado |
| Administrador autorizado | Console do MinIO | A confirmar | Administrar o storage | Caminho privado a definir. Auditoria da #111 registrou ausência de portas Docker publicadas |

### Teste de conectividade no ambiente temporário

Em 12/11/2026, a VPS estabeleceu conexões TCP com o PostgreSQL (5432),
a API do MinIO (9000) e o console do MinIO (9001) na rede Docker
`apae-net`. As mesmas conexões expiraram a partir de um pod de teste em
`apae-dev`.

A captura do teste com PostgreSQL mostrou SYNs na interface do pod,
sem tráfego observado na bridge Docker. Regras em `raw/PREROUTING`
descartam tráfego direto para os dois contêineres quando os pacotes
entram por outra interface.

#### Teste de autenticação mTLS no nó

Um pod em `apae-dev` alcançou um servidor mTLS temporário em
`10.42.0.1:15432`. Sem certificado de cliente, o servidor recusou a sessão
com `TLSV13_ALERT_CERTIFICATE_REQUIRED`. Com um certificado de cliente
assinado pela CA de teste, o servidor retornou `HTTP 200`.

Os pods, o Secret e os arquivos temporários de TLS foram removidos. Após
encerrar o servidor de teste, o `ss` confirmou que a porta `15432/TCP`
ficou livre.

#### Teste ponta a ponta entre k3s e Docker

O cliente autorizado pela NetworkPolicy recebeu `HTTP 200` com corpo
`ok` do backend descartável na `apae-net`. A conexão passou pelo
Service ClusterIP, pelo HAProxy no k3s e pelo HAProxy na rede Docker.
O trecho entre os proxies usou mTLS.

O cliente bloqueado resolveu o mesmo Service e recebeu
`Connection refused`. Em um teste direto ao HAProxy da rede Docker,
a conexão sem certificado de cliente foi recusada pelo TLS.

O namespace, os contêineres e os arquivos temporários foram removidos.
A porta `15432/TCP` ficou livre. A ponte entre k3s e Docker foi validada
com um backend descartável no ambiente temporário da VPS.

### Acesso aos serviços de dados em produção

O desenho de produção prevê que os workloads acessem PostgreSQL e MinIO
por Services internos do k3s. Os manifests desses serviços definirão os
nomes, namespaces e seletores. A issue #114 usará essas definições para
restringir o acesso aos consumidores da matriz e validar os fluxos
permitidos e bloqueados.

[Estudo de comunicação interna](../nginx/04-comunicacao-aplicacoes-e-observabilidade.md#18-comunicação-interna)
