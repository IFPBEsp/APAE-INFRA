# Evidências da alternância — issue #140

Registro das validações realizadas em 07/11/2026 e 09/11/2026 na VPS de testes da APAE.
Os trechos abaixo consolidam resultados apresentados nesta implementação;
não representam uma consulta contínua ao estado da VPS.

## Compose → cluster

Execução concluída:

```text
apae-prod : ok=67 changed=11 unreachable=0 failed=0 skipped=22 rescued=0 ignored=0
```

Estado observado após a troca:

```text
/var/lib/apae/runtime-mode: cluster
systemctl is-active k3s: active
systemctl is-enabled k3s: enabled

Docker em execução:
apae-minio-shared
apae-postgres (healthy)
```

O nó ficou `Ready`, com K3s `v1.36.5+k3s1`. Os quatro componentes do ArgoCD
e os três componentes obrigatórios de `kube-system` ficaram `1/1 Running`.
As aplicações Compose e o proxy estavam parados.

## Cluster → Compose

Execução concluída:

```text
apae-prod : ok=65 changed=6 unreachable=0 failed=0 skipped=12 rescued=0 ignored=0
```

Estado observado após o retorno:

```text
/var/lib/apae/runtime-mode: compose
systemctl is-active k3s: inactive
systemctl is-enabled k3s: disabled

Docker em execução:
proxy-proxy-1
apae-gestao-escolar-frontend
apae-geral-frontend
apae-atendimento-frontend
apae-atendimento-api
apae-gestao-api
apae-geral-api
apae-site-comemorativo
apae-minio-shared
apae-postgres (healthy)
```

O administrador confirmou no navegador que as aplicações estavam no ar e
que os documentos do MinIO estavam acessíveis. Essa confirmação funcional
complementa as verificações HTTP feitas pelo playbook.

Os contadores de tarefas refletem a versão executada naquele momento.
A integração posterior da renovação TLS adiciona tarefas; o número exato de
`ok` ou `changed` não é critério de sucesso para execuções futuras.

## Preservação dos serviços de dados

Antes da troca, foi registrado o resultado de `docker inspect` contendo nome,
ID, horário de início e montagens. Após a ida ao cluster e após o retorno,
a comparação com esse registro não produziu diferenças.

| Serviço | ID abreviado | Início observado em UTC | Volume |
| --- | --- | --- | --- |
| PostgreSQL | `b2e2878e25f5` | `2026-11-06T23:33:57.737254153Z` | `apae_postgres_data` |
| MinIO compartilhado | `54a25e23442d` | `2026-11-06T23:33:57.944281454Z` | `apae-minio-shared_minio-shared-data` |

Isso comprova que os containers não foram recriados nem reiniciados nesses
testes e que as montagens foram preservadas. Não constitui uma auditoria de
integridade de todos os registros ou objetos, nem um teste de backup/restore.

### Como repetir a comparação

Na VPS, antes de uma nova troca, grave em arquivo acessível apenas a root:

```bash
sudo sh -c 'umask 077; docker inspect apae-postgres apae-minio-shared \
  --format "{{.Name}} id={{.Id}} iniciado={{.State.StartedAt}} volumes={{json .Mounts}}" \
  > /var/lib/apae/data-before-switch.txt'
```

Depois da troca, compare:

```bash
sudo sh -c 'docker inspect apae-postgres apae-minio-shared \
  --format "{{.Name}} id={{.Id}} iniciado={{.State.StartedAt}} volumes={{json .Mounts}}" \
  | diff -u /var/lib/apae/data-before-switch.txt -'
```

Saída vazia e código zero indicam igualdade desses campos. Valide também
um registro conhecido e um documento já anexado pela aplicação. Não exponha
dados pessoais ou credenciais ao anexar evidências ao PR.

## Concorrência, repetição e encerramento do K3s

- A aquisição de uma trava já existente falhou com diagnóstico explícito,
  sem remover a trava da outra operação.
- Reexecuções no modo Compose concluíram sem duplicar containers nem alterar
  os volumes de dados.
- A checagem de atividade residual do K3s foi ajustada para consultar listeners
  reais e processos de containers. O arquivo antigo
  `/run/k3s/containerd/containerd.sock` existia sem listener e deixou de
  provocar chamadas desnecessárias ao `k3s-killall.sh`.
- O acesso SSH administrativo permaneceu disponível nas trocas realizadas;
  as saídas de verificação foram coletadas pelo usuário `ansible` na VPS.

## TLS e disponibilidade após renovação simulada

A [evidência detalhada de TLS](runtime-tls.md#evidências-da-instalação-em-07112026)
registra instalação, teste ACME e execução pelo systemd. Resumo:

- Vinte testes locais dos scripts passaram.
- `ansible-lint` dos três playbooks relacionados passou sem violações.
- O desafio de renovação `--dry-run` concluiu com sucesso na VPS.
- O certificado de produção permaneceu inalterado e o proxy voltou ao ar.
- O serviço systemd terminou com `Result=success` e `ExecMainStatus=0`.
- O timer ficou ativo e habilitado; a reaplicação da instalação alterou apenas
  a aquisição e a liberação da trava.
- Os cinco endpoints do inventário responderam HTTP 200 com validação TLS.
- IDs, horários de início e volumes dos serviços de dados continuaram iguais.

## Validação final das correções do PR #145 em 09/11/2026

Validação realizada sobre o commit `b14dd05`, após as correções da revisão.
O administrador autorizou a janela para interromper os produtos e executar
a ida ao cluster e o retorno ao Compose.

### Testes locais e CI

- Suíte completa: **60 testes passaram**, incluindo os 20 cenários TLS.
- Foi utilizado Kustomize **v5.8.1**, a mesma versão fixada no CI, com checksum
  conferido pelo valor do instalador versionado. A versão do sistema era
  diferente; não foi usada para declarar sucesso da suíte.
- `ansible-lint` dos três playbooks passou sem violações.
- Quatro cenários adicionais executaram as tarefas reais de verificação de
  reinício contra um Docker simulado, sem alterar a VPS: rejeição de `always`
  no Compose, rejeição de `always` em container parado, aceitação de
  `unless-stopped` e aceitação de projeto sem containers existentes.
- Os checks disponíveis no [PR #145](https://github.com/IFPBEsp/APAE-INFRA/pull/145)
  estavam aprovados: commitlint, lint Kubernetes, lint ArgoCD, Markdown e testes.
  Isso não substitui a aprovação humana do PR.

### Instalação TLS e ida ao cluster

A configuração TLS parametrizada por `ansible_host` foi reaplicada com sucesso:

```text
apae-prod : ok=14 changed=2 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
```

As duas alterações foram aquisição e liberação da trava; scripts e unidades
permaneceram sem alterações na VPS.

A ida ao cluster passou pelo novo pré-check de reinício de todos os projetos:

```text
apae-prod : ok=109 changed=11 unreachable=0 failed=0 skipped=27 rescued=0 ignored=0
```

O nó ficou `Ready`; os sete componentes obrigatórios ficaram `1/1 Running`.
Uma verificação adicional confirmou os IDs completos, horários de início e
montagens esperadas de PostgreSQL e MinIO iguais aos registrados antes da troca:

```text
apae-prod : ok=7 changed=0 unreachable=0 failed=0 skipped=1 rescued=0 ignored=0
```

O wrapper TLS foi executado no cluster e adiou a tentativa sem interromper
os workloads ou os serviços de dados:

```text
TLS_DEFERRED: Compose não é o modo concluído ou o K3s não está parado.
```

### Retorno ao Compose e estado final

O retorno executou o fluxo integrado de TLS antes de iniciar os produtos,
sem necessidade de nova emissão porque o certificado ainda tinha validade
suficiente. O playbook concluiu:

```text
apae-prod : ok=112 changed=12 unreachable=0 failed=0 skipped=12 rescued=0 ignored=0
```

Os cinco endpoints configurados passaram na verificação HTTPS do playbook.
Uma segunda verificação independente confirmou HTTP 200 com validação TLS,
registro final `compose`, timer ativo e preservação dos dados:

```text
apae-prod : ok=6 changed=0 unreachable=0 failed=0 skipped=2 rescued=0 ignored=0
```

PostgreSQL e MinIO mantiveram os mesmos IDs completos, horários de início e
volumes registrados na tabela inicial, tanto no cluster quanto após o retorno.
As verificações consultaram os containers existentes; não houve cópia,
restauração ou recriação de dados durante a alternância.

Após a conclusão, também foi executado o serviço systemd de TLS:

```text
apae-compose-tls-renew.service:
  Result=success
  ExecMainStatus=0
k3s:
  ActiveState=inactive
  UnitFileState=disabled
apae-compose-tls-renew.timer:
  enabled
```

A trava `/run/lock/apae-runtime-mode` estava ausente ao fim da operação.
A VPS foi deixada no modo Compose, com os produtos disponíveis.
Essa rodada completa confirma a integração das correções de reinício e TLS;
não foi feita nova emissão forçada de certificado de produção.

## Limites da validação e dependências futuras

Não foi executado reboot da VPS para testar retomada após reinicialização.
O comportamento configurado e as verificações necessárias após boot estão no
[guia operacional](runtime-mode.md#comportamento-após-reiniciar-a-vps).

Os produtos ainda não estavam implantados no cluster durante os testes de
alternância. Portanto, não há evidência de conexão de pods ao PostgreSQL/MinIO,
de acesso público aos documentos pelo Gateway Kubernetes ou de compatibilidade
de migrations novas executadas por esses produtos no cluster.
Essas validações devem integrar as próximas issues de implantação, conforme
as [responsabilidades documentadas](runtime-mode.md#responsabilidades-das-próximas-issues).

Os primeiros testes de 07/11 ocorreram antes da integração completa do TLS e
das correções do PR #145. A seção de 09/11 registra separadamente as execuções
da versão revisada, sem atribuir essas verificações aos testes anteriores.
