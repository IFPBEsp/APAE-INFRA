# NGINX Gateway Fabric no k3s

## Estado e condição para implantação

A preparação da #111 foi validada localmente. O modo cluster foi ativado
pelo procedimento Ansible da issue #140. O nó está `Ready`, e os componentes
do ArgoCD e de `kube-system` estão em execução. Apenas PostgreSQL e MinIO
compartilhado permanecem ativos no Docker.

As verificações iniciais não encontraram CRDs dos grupos
`gateway.networking.k8s.io` ou `gateway.nginx.org`, nem listeners TCP em
80/443. Os Services observados são do tipo `ClusterIP`.

A implantação do Gateway ainda está pendente: o AppProject efetivo mantém
as permissões iniciais, e a Application raiz acompanha `main`, que ainda
não contém as Applications da #111. É necessário disponibilizar os
manifests nessa revisão e aplicar as permissões pelo Ansible antes dos
syncs manuais.

| Verificação | Estado nesta preparação |
| --- | --- |
| Base da #91 / PR #119 | Integrada à `dev` em `0563119ff77c57afdd4509c9452305070a50d55b` e incorporada à branch da #111 em `8605ab7`. |
| Preparação inicial da #111 | Commit `282a624`. |
| Chart Helm | Renderizado localmente no commit fixado, com 26 recursos, incluindo CRDs e hooks. |
| AppProject | Lista de permissões conferida localmente para 43 recursos: chart, Gateway API, Gateway e três Applications. |
| Validação estática anterior | Kubeconform aprovou 15 recursos de infraestrutura e três Applications; KubeLinter sem erros. Esses resultados não incluem a validação completa do chart no cluster. |
| Implantação e testes do Gateway na VPS | Pendentes; a ativação do cluster e as leituras iniciais não comprovam o funcionamento do Gateway. |

A renderização local não comprova compatibilidade efetiva com a API da VPS,
disponibilidade das portas, convergência do controller ou persistência após
reinícios. A implantação da #111 permanece pendente até executar e registrar
as verificações operacionais deste documento.

## Exposição na VPS

O data plane do NGINX Gateway Fabric usa uma réplica e publica as portas
80 e 443 da VPS com `hostPort`. O Service do data plane usa `ClusterIP`.
Essa configuração reserva apenas as portas de entrada necessárias e mantém
a rede do pod separada da rede do host.

| Opção | Avaliação |
| --- | --- |
| `hostPort` | Escolhido para expor 80 e 443 no nó único da VPS. |
| ServiceLB | Exigiria reativar o componente desabilitado na #90 e publicar um Service `LoadBalancer`. |
| `hostNetwork` | Colocaria o pod na rede do host. O gateway precisa de apenas dois mapeamentos de porta. |

A configuração versionada do k3s desabilita Traefik e ServiceLB conforme a #90.
O estado efetivo ainda precisa ser conferido na VPS. As portas 80 e 443 precisam
estar livres antes do sync que cria o data plane. Não interromper o Compose
para liberá-las fora da janela de migração.

## Versões

- Gateway API `1.6.3`, canal `standard`, com o pacote versionado no APAE-INFRA.
- NGINX Gateway Fabric `2.8.1`, com o chart fixado no commit
  `ed383f6aaa256a3e0b75c89f6d6e9f75fbe5faa3` do repositório oficial.
- O chart declara Kubernetes `>= 1.32.0-0`; conferir a versão efetiva do k3s
  antes da implantação.
- O acesso ao chart OCI retornou `403` no teste local. A Application usa
  o chart em `charts/nginx-gateway-fabric` do Git oficial, sem depender de OCI.

## Revisões Git e descoberta das Applications

O PR #119 fornece `argocd/project-infra.yaml` e `argocd/app-of-apps.yaml`.
A raiz `apae-root` acompanha `main`, com `path: argocd`, `directory.recurse: true`
e `directory.include: 'apps/*/*.yaml'`. Esse filtro inclui os três arquivos
de `argocd/apps/infra/` e exclui os objetos de bootstrap na raiz de `argocd/`.

As Applications `gateway-api-crds` e `nginx-gateway` também acompanham `main`.
Somente `nginx-gateway-fabric` acompanha o commit fixado do repositório NGINX.
Não trocar as revisões para `dev` ou para a branch da feature como atalho
de implantação.

Na leitura realizada durante a preparação, `origin/main` continha apenas
`argocd/README.md` nesses caminhos de infraestrutura. Antes da implantação,
confirmar que a promoção aprovada para `main` disponibilizou os objetos de
bootstrap, as três Applications e seus diretórios de manifests. Integrar a #111
somente à `dev` não disponibiliza esses arquivos para as Applications atuais.

A raiz tem sync automático com `selfHeal` e `prune`; as três filhas têm sync
manual. Publicar os manifests em `main` pode registrar as filhas automaticamente,
mas não autoriza sincronizar seus workloads. Conferir o conjunto de filhas e o
diff da raiz antes da promoção; excluir uma filha do Git pode acionar o prune.

## Permissões e aplicação do AppProject

`argocd/project-infra.yaml` deve permitir explicitamente:

| Escopo | Grupo | Recursos |
| --- | --- | --- |
| Origem | Git | `https://github.com/IFPBEsp/APAE-INFRA.git` e `https://github.com/nginx/nginx-gateway-fabric.git` |
| Destino | Cluster local (`https://kubernetes.default.svc`) | Namespaces `argocd` e `nginx-gateway` |
| Cluster | Grupo core (`""`) | `Namespace` |
| Cluster | `apiextensions.k8s.io` | `CustomResourceDefinition` |
| Cluster | `admissionregistration.k8s.io` | `ValidatingAdmissionPolicy`, `ValidatingAdmissionPolicyBinding` |
| Cluster | `rbac.authorization.k8s.io` | `ClusterRole`, `ClusterRoleBinding` |
| Cluster | `gateway.networking.k8s.io` | `GatewayClass` |
| Namespace | `argoproj.io` | `Application` |
| Namespace | Grupo core (`""`) | `ServiceAccount`, `Service` |
| Namespace | `apps` | `Deployment` |
| Namespace | `batch` | `Job` |
| Namespace | `rbac.authorization.k8s.io` | `Role`, `RoleBinding` |
| Namespace | `gateway.nginx.org` | `NginxGateway`, `NginxProxy` |
| Namespace | `gateway.networking.k8s.io` | `Gateway` |

O pacote standard da Gateway API inclui a política de admissão
`safe-upgrades.gateway.networking.k8s.io` e seu binding; permitir apenas CRDs
não basta. Os hooks do chart de certificados precisam de `ServiceAccount`,
`Role`, `RoleBinding` e `Job`.

Não é necessário permitir `Secret` ou `HTTPRoute` ao ArgoCD na configuração
atual: o Job cria seus Secrets pelo RBAC Kubernetes, e o smoke test é uma
operação administrativa temporária. O AppProject não restringe as operações
executadas pelo controller ou pelo Job por meio de suas ServiceAccounts.

O **Ansible**, não o ArgoCD, administra os AppProjects e a raiz. A ampliação
versionada deve ser aplicada pelo procedimento de bootstrap descrito em
[argocd-bootstrap-recovery.md](../../ansible/docs/argocd-bootstrap-recovery.md),
usando `ansible/playbooks/argocd.yml` a partir da revisão aprovada. A role também
executa etapas de instalação/atualização e segurança do ArgoCD; não tratar a
execução desse playbook como uma aplicação isolada do AppProject.
Conferir o diff e os efeitos previstos antes de executar na janela autorizada.
Não usar um patch avulso no cluster como substituto da configuração versionada.

Após a aplicação pelo Ansible, ler o AppProject efetivo e conferir as origens,
destinos e whitelists antes de qualquer sync das filhas.

## Pré-implantação na janela de migração

Os comandos desta seção são de **leitura e devem ser executados na VPS por SSH**,
conforme [k3s-access.md](../../ansible/docs/k3s-access.md). Não executá-los no Linux
local esperando encontrar o binário do k3s. A existência da configuração no Git
não comprova que o cluster esteja instalado ou disponível.

```sh
hostname
sudo /usr/local/bin/k3s --version
sudo /usr/local/bin/k3s kubectl get nodes -o wide
sudo /usr/local/bin/k3s kubectl get pods -A -o wide
sudo /usr/local/bin/k3s kubectl -n argocd get applications
sudo /usr/local/bin/k3s kubectl -n argocd get application apae-root -o yaml
sudo /usr/local/bin/k3s kubectl -n argocd get appproject apae-infra -o yaml
sudo /usr/local/bin/k3s kubectl get crd
sudo /usr/local/bin/k3s kubectl -n kube-system get helmcharts,deployments,daemonsets
sudo ss -ltnp '( sport = :80 or sport = :443 )'
sudo docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

Antes de avançar:

- Confirmar nó `Ready`, saúde dos componentes e versão compatível do Kubernetes.
- Inspecionar CRDs dos grupos `gateway.networking.k8s.io` e `gateway.nginx.org`.
  Se existirem, ler anotações de versão/canal, labels, `managedFields` e a
  Application ou release responsável. Não sobrescrever, adotar ou remover CRDs
  existentes sem resolver a responsabilidade de gerenciamento e a compatibilidade.
- Conferir também a existência da política `safe-upgrades.gateway.networking.k8s.io`
  e seu binding, bem como uma eventual GatewayClass `nginx` já instalada.
- Confirmar Traefik e ServiceLB desabilitados no estado efetivo.
- Inspecionar `hostPort` 80/443 e `hostNetwork` nos specs dos pods; conferir
  Services `NodePort`/`LoadBalancer` e publicações Docker. Ausência de listeners
  no `ss` não basta para concluir que as portas estão livres, pois publicações
  podem usar regras de rede.
- Confirmar que firewall e regras do provedor permitem o HTTP e HTTPS públicos.
- Registrar o estado do Compose, o procedimento aprovado de retorno ao serviço
  anterior e o backup necessário antes de alterar a exposição.

A parada ou reconfiguração do Compose pertence à migração autorizada. Só liberar
80/443 depois de confirmar como o serviço atual será preservado ou retomado.
Antes de retornar ao Compose, liberar essas portas no data plane pelo
procedimento de contingência aprovado; não manter os dois disputando as portas.

## Ordem de sincronização

1. Confirmar as permissões do AppProject `apae-infra` e verificar se já existem
   CRDs da Gateway API na VPS. Se existirem, identificar a versão e quem os
   gerencia antes de sincronizar.
2. Sincronizar `gateway-api-crds` e aguardar os CRDs ficarem `Established` e o
   namespace `nginx-gateway` ficar `Active`.
3. Sincronizar `nginx-gateway-fabric` e confirmar que o Job de certificados
   concluiu, o controller está disponível e a GatewayClass `nginx` foi aceita.
4. Sincronizar `nginx-gateway` e confirmar `Accepted=True` e `Programmed=True`
   no Gateway `apae-gateway`.

As três sincronizações são manuais. As duas Applications que instalam CRDs
usam `ServerSideApply=true`.

Em cada etapa, revisar o diff no ArgoCD e sincronizar somente a Application
indicada. Não sincronizar as três em conjunto. Se uma etapa falhar, registrar
o erro e corrigir a causa antes de iniciar a próxima.

Na primeira etapa, aguardar também o estabelecimento das políticas de admissão
incluídas no pacote. Na segunda, confirmar os CRDs `gateway.nginx.org` e guardar
o resultado do Job de certificados assim que terminar: o chart configura
`ttlSecondsAfterFinished: 30`, e o Job pode ser removido automaticamente.
Não registrar o conteúdo dos Secrets gerados.

Após a última etapa, conferir o Service e os pods **do data plane**, além do
Deployment do controller. O Service do controller não comprova a exposição do
Gateway. Verificar no pod gerado os `hostPort` 80/443 e no Service gerado o tipo
`ClusterIP`, sem `NodePort` ou `LoadBalancer`.

## Validação externa

Executar somente depois de concluir os três syncs e ainda dentro da janela
autorizada. O diretório `kubernetes/infra/nginx-gateway-smoke/` não é origem de
nenhuma das três Applications. O `kubernetes/infra/kustomization.yaml` agrega
recursos para lint e inclui a rota temporária; não aplicá-lo em bloco na VPS.

### Preparação do smoke test

1. Em um diretório temporário protegido, gerar certificado de teste com SAN
   `DNS:gateway-smoke.test` e sua chave privada. Usar validade suficiente para
   concluir os testes, incluindo os dois reinícios. Não versionar a chave.
2. Criar o Secret TLS `gateway-smoke-tls` no namespace `nginx-gateway` com esse
   certificado e chave. Não substituir os Secrets internos `server-tls` e
   `agent-tls` do controller.
3. Inspecionar os listeners atuais do `apae-gateway`. Aplicar como JSON Patch
   `kubernetes/infra/nginx-gateway-smoke/https-listener-patch.yaml`, que acrescenta
   o listener `https-smoke` em 443. Não reaplicar o patch se esse listener já
   existir; ele contém uma operação de adição à lista.
4. Aplicar `kubernetes/infra/nginx-gateway-smoke/httproute.yaml`, que cria a rota
   `gateway-smoke`. A rota referencia os listeners `http` e `https-smoke`.
5. Aguardar `Accepted=True` e `Programmed=True` no Gateway, resolução válida
   da referência TLS no listener e `Accepted=True`/`ResolvedRefs=True` nos dois
   vínculos da HTTPRoute com o Gateway. Conferir `observedGeneration` quando
   presente para evitar interpretar condições de uma geração anterior.

O listener temporário deixa o Gateway diferente do manifesto Git e pode indicar
`OutOfSync` na filha `nginx-gateway`. Ela continua com sync manual: não fazer
novo sync dessa filha durante o smoke test, pois isso pode remover o listener.

### Requisições de fora da VPS

Copiar somente o certificado público de teste para a estação de validação.
Na estação Linux com fish, definir o IP público e o caminho absoluto desse
certificado, substituindo os exemplos abaixo:

```fish
set -g VPS_IP IP_PUBLICO_DA_VPS
set -g SMOKE_CERT /caminho/absoluto/gateway-smoke.crt

curl --noproxy '*' --connect-timeout 10 --max-time 20 \
    --resolve "gateway-smoke.test:80:$VPS_IP" \
    --dump-header - --output /dev/null \
    http://gateway-smoke.test/__gateway-check

curl --noproxy '*' --connect-timeout 10 --max-time 20 \
    --resolve "gateway-smoke.test:443:$VPS_IP" \
    --cacert "$SMOKE_CERT" \
    --dump-header - --output /dev/null \
    https://gateway-smoke.test/__gateway-check
```

Exigir retorno `302` e cabeçalho `Location` apontando para o caminho `/`.
Não usar `-L`, para não ocultar a resposta de redirecionamento, nem `-k`, para
não desabilitar a verificação TLS. O HTTPS deve concluir a verificação do
certificado e do hostname com o certificado de teste explicitamente confiado.
O `--resolve` dispensa alterações de DNS e mantém o hostname/SNI do teste.

### Persistência e reinícios

Depois de registrar o resultado inicial, reiniciar apenas o serviço k3s na
janela autorizada e aguardar o nó e os workloads voltarem a ficar disponíveis.
Repetir as condições do Gateway/rota, a inspeção do Service/pods e as duas
requisições externas. Em seguida, reiniciar a VPS em uma etapa separada e
repetir todas as verificações após reconectar por SSH.

Não iniciar o segundo reinício se a validação do primeiro falhar. Guardar a
saída e o horário de cada fase; não inferir persistência apenas porque o SSH ou
o serviço k3s voltou. Confirmar que o Compose não voltou a ocupar as portas
80/443 durante o boot e que o data plane recuperou a exposição esperada.

## Limpeza do smoke test

Após concluir as três fases de validação:

1. Excluir somente a HTTPRoute `gateway-smoke` do namespace `nginx-gateway`.
2. Ler novamente o Gateway e remover somente o listener chamado `https-smoke`.
   Se usar JSON Patch, conferir seu índice atual e incluir uma operação `test`
   no nome antes de removê-lo. Não presumir que o índice será sempre o mesmo.
3. Excluir somente o Secret `gateway-smoke-tls`.
4. Remover a chave privada e os arquivos temporários de teste das máquinas
   envolvidas, preservando apenas evidências sanitizadas.
5. Confirmar ausência da rota e do Secret temporários, ausência do listener
   `https-smoke`, permanência do listener `http` e Gateway saudável. Atualizar a
   comparação no ArgoCD e confirmar a filha `nginx-gateway` em `Synced`.

Não remover os CRDs, a GatewayClass, o namespace, o Gateway, os recursos do chart
ou seus Secrets internos como parte da limpeza. O teste de HTTPS é temporário;
ao final, o manifesto principal continua apenas com o listener HTTP. A
reserva de `hostPort` 443 pode permanecer no pod mesmo sem listener HTTPS.
DNS e TLS definitivos continuam no escopo da #112.

## Evidências e critérios de conclusão

Registrar as evidências operacionais nesta seção ou vinculá-las a partir da
issue #111, identificando revisão Git, operador, data/hora com fuso e fase.
Não anexar kubeconfigs, tokens, senhas, chaves privadas ou conteúdo de Secrets.

| Evidência | Resultado nesta preparação |
| --- | --- |
| Revisão promovida para `main` e revisão efetiva de cada Application | Pendente |
| AppProject aplicado pelo Ansible e permissões efetivas | Pendente |
| Versão/saúde do k3s, CRDs anteriores e seus responsáveis | Pendente |
| Transição do Compose e disponibilidade de 80/443 | Pendente |
| CRDs `Established`, namespace `Active`, Job e controller disponíveis | Pendente |
| GatewayClass aceita, Gateway e vínculos da HTTPRoute válidos | Pendente |
| Data plane: uma réplica, hostPorts e Service `ClusterIP` | Pendente |
| HTTP 302 e HTTPS 302 com verificação TLS, de fora da VPS | Pendente |
| Mesmas verificações após reiniciar o k3s | Pendente |
| Mesmas verificações após reiniciar a VPS | Pendente |
| Remoção do smoke test e retorno ao manifesto Git | Pendente |

A documentação e a validação local não substituem essas evidências. Não
considerar a implantação concluída enquanto os itens operacionais estiverem
pendentes.
