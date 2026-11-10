# NGINX Gateway Fabric no k3s

## Estado e condição para implantação

A implantação de validação da #111 foi executada pelo administrador, com
o modo cluster ativado pelo procedimento Ansible da #140. Controller, data
plane, GatewayClass e Gateway foram instalados pelo ArgoCD. Os testes externos
HTTP/HTTPS passaram inicialmente, após reiniciar o k3s e após reiniciar a VPS.
O smoke test foi removido do cluster, e as três Applications retornaram a
`Synced/Healthy`. As evidências e os limites estão registrados ao final.

A validação precede a integração da #111 ao Git: as Applications de teste
foram registradas pelo Ansible, fora da descoberta da raiz, com revisões
fixadas. O AppProject também foi aplicado pelo Ansible a partir do manifesto
local. A promoção da #111 para `main` e a posterior adoção das Applications
pela raiz ainda precisam ser verificadas; os testes não comprovam essa etapa.

| Verificação | Estado nesta preparação |
| --- | --- |
| Base da #91 / PR #119 | Integrada à `dev` em `0563119ff77c57afdd4509c9452305070a50d55b` e incorporada à branch da #111 em `8605ab7`. |
| Preparação inicial da #111 | Commit `282a624`. |
| Chart Helm | Renderizado localmente no commit fixado, com 26 recursos, incluindo CRDs e hooks. |
| AppProject | Lista de permissões conferida localmente para 43 recursos: chart, Gateway API, Gateway e três Applications. |
| Validação estática anterior | Kubeconform aprovou 15 recursos de infraestrutura e três Applications; KubeLinter sem erros. Esses resultados não incluem a validação completa do chart no cluster. |
| Revisão local final | Helm renderizou os 26 recursos com `Recreate`; Kubeconform aprovou os 70 recursos do CI integrado à #92, sem erros ou skips; 35 testes GitOps, YAML, Markdown e KubeLinter aprovados. |
| Implantação e testes do Gateway na VPS | Executados; HTTP/HTTPS validados nas três fases e smoke test removido do cluster. |

Os resultados operacionais referem-se à instalação e às revisões descritas
neste documento; não substituem a validação de mudanças futuras.

## Exposição na VPS

O data plane do NGINX Gateway Fabric usa uma réplica e mapeamentos de `hostPort`
para os listeners 80 e 443. O Service do data plane usa `ClusterIP`.
Essa configuração reserva apenas as portas de entrada necessárias e mantém
a rede do pod separada da rede do host.

| Opção | Avaliação |
| --- | --- |
| `hostPort` | Escolhido para expor 80 e 443 no nó único da VPS. |
| ServiceLB | Exigiria reativar o componente desabilitado na #90 e publicar um Service `LoadBalancer`. |
| `hostNetwork` | Colocaria o pod na rede do host. O gateway precisa de apenas dois mapeamentos de porta. |

A configuração versionada do k3s desabilita Traefik e ServiceLB conforme a #90.
Essa configuração foi conferida na VPS durante a preparação. As portas 80 e 443 precisam
estar livres antes do sync que cria o data plane. Não interromper o Compose
para liberá-las fora da janela de migração.

O controller gera portas de acordo com os listeners: com apenas HTTP, foi
observado somente `hostPort` 80 e Service em 80; com o listener temporário HTTPS,
foram observados `hostPort` 80/443 e Service em 80/443. A configuração de dois
mapeamentos nos valores Helm não comprova, sozinha, que ambos estão publicados.

### Atualizações no nó único

O Deployment do data plane usa `Recreate`, configurado em `nginx.patches` no
chart e propagado pelo `NginxProxy`. O `RollingUpdate` padrão tentou criar um
segundo pod antes de encerrar o primeiro, e o scheduler recusou o agendamento
porque o pod antigo ocupava o `hostPort` 80. `Recreate` resolveu o bloqueio no
teste de adição e remoção do listener HTTPS.

Há interrupção durante a substituição do único pod; essa configuração não
oferece alta disponibilidade. Não editar diretamente o Deployment gerado:
o ajuste deve permanecer nos valores Helm administrados pelo ArgoCD.

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
No fluxo definitivo, manter essas revisões em `main`.

A promoção pelo PR #148 disponibilizou os objetos de bootstrap e as Applications
de produtos na `main`, revisão `1e95556a18e02358b0dc767d2281ff8fca5e49bf`.
Essa promoção não incluiu a #111. Para validar a infraestrutura antes do PR,
o administrador registrou as três Applications pelo Ansible, sem alterar a
raiz. Nas duas Applications do APAE-INFRA, somente as cópias aplicadas usam
`282a62423465718a138211cae73023aaa5ae4ea4`, revisão publicada contendo os
manifests testados. O chart mantém seu commit NGINX fixado.

Após promover a #111 para `main`, conferir a adoção das três Applications
existentes pela raiz, as revisões efetivas e o diff dos workloads. Preservar
os nomes atuais; não excluir/recriar as Applications nem remover CRDs como
parte dessa transição. A raiz deve reconciliar as filhas para as revisões
declaradas nos arquivos versionados. Conferir também a permanência do patch
`Recreate` antes de sincronizar o chart.

Checklist da adoção, para executar somente depois da promoção:

1. Confirmar que a revisão de `main` contém as três Applications, o AppProject
   ampliado e os diretórios de manifests, incluindo a correção `Recreate`.
2. Conferir a revisão e os recursos gerenciados pela raiz. Atualizar sua
   comparação se necessário, preservando o filtro `apps/*/*.yaml`.
3. Confirmar que as três Applications existentes foram incorporadas à árvore
   da raiz: `gateway-api-crds` e `nginx-gateway` devem passar a acompanhar
   `main`; o chart deve manter o commit NGINX fixado.
4. Conferir que as filhas continuam com sync manual, SSA nas duas Applications
   de CRDs e valores Helm incluindo `Recreate`. Não executar sync conjunto
   nem prune para eliminar os recursos existentes.
5. Revisar eventuais diferenças antes de sincronizar na ordem documentada.
   Registrar as revisões reconciliadas, a saúde do Gateway e a permanência
   do estado limpo, sem recursos de smoke test.

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

Na validação, foi usado o módulo `ansible.builtin.command` com
`k3s kubectl apply -f -`, recebendo somente o manifesto local de `apae-infra`+pelo stdin. Isso atualizou o projeto sem executar instalação, upgrade ou
segurança do ArgoCD e sem alterar o AppProject `apae` dos produtos.

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

### Sync manual por operação Kubernetes

Preferir o sync pela interface ou CLI do ArgoCD, que prepara a operação usando
as opções da Application. Se solicitar o sync escrevendo diretamente o campo
`operation` via Kubernetes, incluir explicitamente as opções em
`operation.sync.syncOptions`, além da configuração em `spec.syncPolicy`:

```json
{
  "operation": {
    "sync": {
      "revision": "REVISAO_FIXADA_DA_APPLICATION",
      "prune": false,
      "syncOptions": ["ServerSideApply=true"]
    }
  }
}
```

Na primeira tentativa, a operação manual omitiu essa opção e o CRD
`nginxproxies.gateway.nginx.org` falhou com `metadata.annotations: Too long:
may not be more than 262144 bytes`. O controller entrou em `CrashLoopBackOff`
por ausência de `NginxProxy/v1alpha2`. O administrador encerrou a operação
pendente e repetiu o sync com SSA explícito. O CRD ficou `Established`, o
`NginxProxy` foi criado e o controller recuperou na tentativa seguinte.
Não foi necessário excluir recursos ou aplicar CRDs fora do ArgoCD.

Um sync `Succeeded` não substitui conferir `Synced/Healthy`, CRDs e workloads.
Na primeira instalação da Gateway API, uma nova comparação (`refresh=hard`)
atualizou o estado inicialmente transitório para `Synced/Healthy`, sem novo sync.

### Verificação de cada etapa

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
configuração dos mapeamentos 80/443 permanece nos valores Helm, mas no teste
o pod gerado publicou 443 somente enquanto existia o listener HTTPS.
DNS e TLS definitivos continuam no escopo da #112.

## Evidências e critérios de conclusão

As evidências abaixo foram fornecidas pelo administrador na sessão de
implantação, executada por SSH como `ansible`; os testes externos foram
executados no Linux local com fish. Horários estão em `America/Recife` (UTC−03).
As saídas representam o estado observado naquela execução, não monitoramento
contínuo do ambiente.
Não anexar kubeconfigs, tokens, senhas, chaves privadas ou conteúdo de Secrets.

| Evidência | Resultado observado |
| --- | --- |
| Revisões das Applications de teste | APAE-INFRA: `282a62423465718a138211cae73023aaa5ae4ea4`; NGINX: `ed383f6aaa256a3e0b75c89f6d6e9f75fbe5faa3`. |
| Integração da #111 à raiz em `main` | Pendente de promoção e verificação da adoção; não faz parte dos testes já executados. |
| AppProject aplicado pelo Ansible | `apae-infra configured`, geração 2, com origens, destinos e tipos explícitos; projeto dos produtos preservado. |
| k3s e estado inicial | `v1.36.5+k3s1`, nó `Ready`; nenhum CRD Gateway API/NGINX existente e nenhum listener TCP em 80/443 antes da instalação. |
| Transição do Compose | Executada pela #140; apenas PostgreSQL e MinIO compartilhado continuaram ativos no Docker. |
| Gateway API | Dez CRDs `Established`, namespace `Active`, política `safe-upgrades` e binding criados; política com `observedGeneration: 1` e sem avisos de tipagem. |
| NGINX Gateway Fabric | 14 CRDs instalados, Job de certificados concluído, controller disponível e GatewayClass `nginx` aceita. |
| Gateway e rota durante o teste | Gateway geração 2 com `Accepted=True`/`Programmed=True`; listeners HTTP/HTTPS válidos, rota com `Accepted=True`/`ResolvedRefs=True` em ambos os vínculos. |
| Data plane | Uma réplica disponível; `hostNetwork: false`, `hostPort` 80/443 no smoke test, métricas 9113 sem `hostPort`; Service `ClusterIP`. |
| Estado após limpeza | Gateway geração 3 aceito/programado, somente listener HTTP, `attachedRoutes: 0`, rota e Secret temporários ausentes; dois Deployments disponíveis e todas as Applications `Synced/Healthy`. |
| Arquivos temporários de certificado/chave | Diretório temporário da VPS removido e ausência confirmada; na revisão local final, nenhum `tls.crt` foi encontrado nos diretórios `/tmp/apae-gateway-external.*` usados no teste. Recursos temporários do cluster removidos. |
| Auditoria final de exposição | Todos os Services listados são `ClusterIP`, sem IP externo; somente o data plane declara `hostPort` 80 após a limpeza e nenhum pod listado usa `hostNetwork`. PostgreSQL e MinIO sem publicação de portas Docker no host. |

### Respostas externas registradas

Os testes acessaram o IP público da VPS com `--resolve`, sem proxy, sem seguir
redirecionamentos e sem desabilitar a verificação TLS. Em todas as fases,
`remote_ip` correspondeu ao IP público e o `Location` apontou para `/`.

| Fase | HTTP | HTTPS | Verificação TLS |
| --- | --- | --- | --- |
| Inicial, 09/11/2026 às 23:59:14 / 23:59:34 | HTTP/1.1 `302` | HTTP/2 `302` | `tls_verify=0` |
| Após reinício do k3s, 10/11/2026 às 00:02:43 / 00:02:51 | HTTP/1.1 `302` | HTTP/2 `302` | `tls_verify=0` |
| Após reboot da VPS, 10/11/2026 às 00:06:19 / 00:06:24 | HTTP/1.1 `302` | HTTP/2 `302` | `tls_verify=0` |

O reinício do serviço k3s foi iniciado às 00:00:31 de 10/11/2026; depois,
`/readyz` retornou `ok`, o nó ficou `Ready` e os rollouts concluíram. Os
containers de PostgreSQL e MinIO permaneceram ativos sem reinício observado
nessa etapa. O reboot da VPS teve horário de boot observado às 00:03:53;
após ele, k3s e Docker estavam ativos, o modo registrado era `cluster`,
os dois Deployments do Gateway estavam disponíveis e os containers de dados
retornaram, com PostgreSQL saudável. Os produtos Compose permaneceram parados.

A limpeza atualizou o Gateway para geração 3, com condições observadas nessa
geração às 00:07:45 de 10/11/2026. A remoção do listener também concluiu o
rollout com `Recreate`, sem o conflito de portas observado anteriormente.

Na auditoria posterior, o Service do controller manteve 443/9113 somente no
cluster; o data plane manteve o Service em 80 e seu único `hostPort` em 80.
O `ss` não mostrou listeners das portas auxiliares do Gateway no host. A saída
do `ss` também mostrou os listeners administrativos do k3s em 6443/10250;
essa leitura, sozinha, não comprova sua acessibilidade externa nem a eficácia
do firewall, cuja proteção permanece sob responsabilidade da #90.

### Validações locais após as correções

- `helm template` no chart `2.8.1`, commit fixado, com `--include-crds`,
  `--kube-version 1.36.5` e os valores extraídos da Application: 26 recursos.
  A validação dos valores Helm passou, e o `NginxProxy` renderizado contém
  uma réplica, `Recreate`, os mapeamentos 80/443 e Service `ClusterIP`.
- Kubeconform com `-strict`, sem ignorar schemas ausentes e com as origens de
  schemas configuradas no workflow: primeiro, infraestrutura renderizada e
  diretório `argocd/`, com 21 recursos válidos. Após integrar a base da #92 e
  resolver o workflow preservando os overlays e `kubernetes/infra`, os nove
  caminhos Kustomize do CI mais `argocd/` totalizaram 70 recursos em 12 arquivos,
  todos válidos, zero erros e skips.
- `GatewayClass`, `NginxGateway`, `NginxProxy`, `Gateway` e `HTTPRoute`
  validados também contra os schemas dos CRDs obtidos das revisões fixadas.
  Essa validação estrutural não executa regras CEL; a aplicação real no
  cluster complementou a verificação.
- Cobertura das whitelists do AppProject para os 43 recursos administrados,
  origens/destinos e ausência de sync automático nas três filhas conferidas.
- KubeLinter dos nove caminhos Kubernetes renderizados e de `argocd/` sem
  erros; yamllint com as regras do CI no manifesto e workflow alterados,
  markdownlint na documentação e `git diff --check` aprovados.
- Os 35 testes existentes de `test_update_image_overlay.py` passaram com
  Kustomize `v5.8.1`, instalado temporariamente e verificado pelo checksum
  fixado na action do repositório. O binário global não foi alterado.

### Limites e acompanhamento

Os testes cobrem a entrada do Gateway e sua persistência; não comprovam
TLS/DNS definitivos (#112), conexão de produtos aos dados ou funcionalidades
dos produtos. Não foi executada nesta sessão uma nova alternância completa
cluster → Compose → cluster depois de instalar o Gateway. A #140 deve incorporar
os Deployments `ngf-nginx-gateway-fabric` e `apae-gateway-nginx` às verificações
obrigatórias de disponibilidade do cluster quando essa integração for realizada.

Ainda é necessário conferir a integração definitiva da #111 na raiz após a
promoção dos manifests. Não interpretar os resultados de teste como evidência
dessa etapa pendente.
