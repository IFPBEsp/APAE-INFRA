# Fluxo do ArgoCD (GitOps)

## Visão geral

O **APAE-INFRA** é o repositório GitOps: a única fonte de verdade lida pelo ArgoCD dentro do cluster Kubernetes. Os 4 repositórios de aplicação (`APAE`, `APAE-atendimento`, `APAE-gestao-escolar`, `apae-site-comemorativo`) nunca aplicam manifestos diretamente no cluster — eles apenas publicam imagens de container no **GHCR**. Quem atualiza o estado desejado do cluster é sempre um commit no APAE-INFRA, e quem aplica esse estado é sempre o ArgoCD.

Isso garante o princípio central do GitOps: **o Git é a única fonte de verdade** e o histórico de commits do APAE-INFRA é, ao mesmo tempo, o histórico de deploys.

## AppProject: governança compartilhada

Antes de falar de Applications, existe um único **`AppProject`** (`apae`) que todas elas compartilham. O `AppProject` não implanta nada sozinho — ele é a camada de permissão/segurança que orienta e padroniza como as Applications dos repositórios envolvidos podem se comportar:

- `sourceRepos`: só o próprio APAE-INFRA pode ser usado como fonte de manifestos (nenhuma Application pode apontar para um repositório fora do GitOps);
- `destinations`: só os namespaces `apae-*` no cluster interno são destinos válidos;
- `clusterResourceWhitelist`: restringe quais tipos de recurso Kubernetes uma Application pode criar (evita, por exemplo, que uma Application de aplicação crie um `ClusterRole` sem necessidade).

```yaml
# argocd/project.yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: apae
  namespace: argocd
spec:
  description: Projeto único orientando as Applications da APAE
  sourceRepos:
    - https://github.com/IFPBEsp/APAE-INFRA.git
  destinations:
    - namespace: 'apae-*'
      server: https://kubernetes.default.svc
  clusterResourceWhitelist:
    - group: '*'
      kind: Namespace
```

## Padrão adotado: App of Apps

Usaremos o padrão **[App of Apps](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/)**: existe uma única `Application` raiz (`apae-root`), criada uma única vez no bootstrap do cluster, que aponta para a pasta `argocd/apps/` do próprio APAE-INFRA. Todas as demais Applications (as **4 Applications filhas**: `apae`, `apae-gestao-escolar`, `apae-atendimento`, `apae-site-comemorativo`) são definidas como arquivos YAML dentro dessa pasta e passam a existir no cluster assim que a raiz sincroniza.

**Importante — são dois loops de sincronização independentes, rodando em paralelo o tempo todo:**

1. **Loop da raiz**: garante que os 4 objetos `Application` (definições) existam no cluster exatamente como estão descritos em `argocd/apps/*.yaml`. Ela só entra em Out-of-Sync se alguém alterar/adicionar/remover um desses arquivos YAML (ex.: criar uma 5ª Application). Um bump de tag de imagem **não afeta** esse loop.
2. **Loop de cada Application filha**: cada uma monitora seu próprio `source.path` (o overlay Kustomize da aplicação dela) e garante que o Deployment/Service/etc. estejam como descrito lá. É esse loop que entra em Out-of-Sync quando a tag da imagem é atualizada.

Ou seja, a raiz não "descobre" as filhas reagindo a um push de imagem — ela já as mantém registradas continuamente. Quem reage ao push de imagem é diretamente a Application filha correspondente, porque foi o overlay dela que mudou.

Vantagens do App of Apps neste contexto:

- Adicionar uma nova Application (ex. `apae-outro-serviço`, no futuro) é só criar um arquivo em `argocd/apps/` — a raiz sincroniza e cria a Application sozinha, sem `kubectl apply` manual;
- O próprio conjunto de Applications fica versionado e auditável junto com o resto da infraestrutura;
- Segue a mesma separação por pasta já definida na issue #7 (`argocd/{aplicacao}/`).

### Estrutura de diretórios

```
argocd/
  app-of-apps.yaml       # Application raiz (apae-root), aponta para argocd/apps/
  project.yaml           # AppProject único (apae)
  apps/
    apae.yaml                    # Application filha: repositório APAE
    apae-gestao-escolar.yaml     # Application filha: repositório APAE-gestao-escolar
    apae-atendimento.yaml        # Application filha: repositório APAE-atendimento
    apae-site-comemorativo.yaml        # Application filha: repositório APAE-site-comemorativo
```

> Neste primeiro momento cada Application filha aponta para um único ambiente (ver seção de Sync abaixo). Conforme os ambientes hml/prod forem estruturados, o padrão se repete: um arquivo por combinação aplicação+ambiente dentro de `argocd/apps/`.

### Applications estáticas

Será adotado uma abordagem para escrever manualmente um YAML de `Application` por repositório — abordagem mais simples de entender e depurar enquanto o time ainda está validando o funcionamento do ArgoCD. Ela tem caminho de evolução direto: quando o número de aplicações/ambientes crescer, o mesmo padrão de pastas pode ser consumido por um `ApplicationSet` sem precisar reestruturar nada.

```yaml
# argocd/app-of-apps.yaml — Application raiz
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: apae-root
  namespace: argocd
spec:
  project: apae
  source:
    repoURL: https://github.com/IFPBEsp/APAE-INFRA.git
    targetRevision: main
    path: argocd/apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      selfHeal: true
      prune: true
```

```yaml
# argocd/apps/apae.yaml — Application filha
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: apae
  namespace: argocd
spec:
  project: apae
  source:
    repoURL: https://github.com/IFPBEsp/APAE-INFRA.git
    targetRevision: main
    path: kubernetes/overlays/dev/apae     # Kustomize overlay
  destination:
    server: https://kubernetes.default.svc
    namespace: apae-dev
  syncPolicy: {}   # sync manual — ver seção de Política de Sincronização
```

> A raiz (`apae-root`) mantém `automated` porque ela só gerencia a existência das *definições* de Application — baixo risco. As Applications filhas (workloads reais) ficam sem `automated`, exigindo aprovação manual, decisão para essa fase do projeto inicial.

Repita a mesma estrutura para `apae-gestao-escolar.yaml`, `apae-atendimento.yaml` e `apae-site-comemorativo.yaml`, mudando `name`, `path` e `namespace`.

### Evolução futura: ApplicationSet

Quando o número de aplicações/ambientes crescer o suficiente para tornar repetitivo escrever um YAML por combinação, o mesmo padrão de pastas pode ser consumido por um único `ApplicationSet`, que gera as Applications automaticamente:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: apae-apps
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/IFPBEsp/APAE-INFRA.git
        revision: main
        directories:
          - path: kubernetes/overlays/*/*   # ex: dev/apae, hml/apae-atendimento...
  template:
    metadata:
      name: '{{path.basenameNormalized}}-{{path[1]}}'   # ex: apae-dev
    spec:
      project: apae
      source:
        repoURL: https://github.com/IFPBEsp/APAE-INFRA.git
        targetRevision: main
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basenameNormalized}}-{{path[1]}}'
      syncPolicy: {}   # manter manual até a decisão de automatizar prod
```

Essa migração não é destrutiva: pode ser feita substituindo os arquivos estáticos de `argocd/apps/` pelo `ApplicationSet` quando fizer sentido, sem alterar a estrutura de pastas do Kustomize.

## De onde cada Application lê os manifestos

Cada `Application` lê exclusivamente do próprio **APAE-INFRA**, usando **Kustomize**:

- `kubernetes/base/{aplicacao}/` — manifestos comuns (Deployment, Service, etc.) da aplicação;
- `kubernetes/overlays/{ambiente}/{aplicacao}/` — patches específicos do ambiente (réplicas, recursos, variáveis, tag de imagem via `kustomization.yaml`).

## Política de sincronização

**Decisão para este momento do projeto: sync manual (aprovação humana) em todas as Applications filhas.**

| Configuração | Valor definido | Motivo |
|---|---|---|
| `syncPolicy.automated` (Applications filhas) | **desabilitado** | o ArgoCD sinaliza "Out of Sync", mas só aplica quando alguém aprovar manualmente (UI ou `argocd app sync`) |
| `syncPolicy.automated` (Application raiz) | habilitado (`selfHeal` + `prune`) | a raiz só gerencia a existência das definições de Application, risco baixo — não afeta workloads diretamente |
| `selfHeal` (filhas) | desabilitado por enquanto | consequência do sync manual: mudanças manuais no cluster não são revertidas automaticamente até a transição abaixo |
| `prune` (filhas) | avaliar caso a caso durante o sync manual | evita remoção automática de recursos sem revisão humana |

### Por quê começar manual

O pipeline de CI/CD dos 4 repositórios de aplicação ainda está em maturação (sem gate de testes obrigatório, sem processo de release consolidado). Sync manual garante um checkpoint humano antes de qualquer mudança chegar ao cluster, reduzindo o risco de um bump de imagem ruim ou um manifesto com erro já impactar o ambiente sem ninguém perceber.

### Critério de transição para automático

A migração de manual para `automated` (com `selfHeal`/`prune`) deve ocorrer quando:

- o pipeline de CI/CD dos repositórios de aplicação tiver testes automatizados obrigatórios antes do merge; e
- houver um histórico de releases consecutivas sem necessidade de rollback manual.

Até lá, cada Application filha permanece com `syncPolicy: {}` (sem `automated`), exigindo que alguém revise o "Out of Sync" no ArgoCD e aprove o sync manualmente.

## Image Updater: GitHub Actions (não o ArgoCD Image Updater)

A responsabilidade de identificar uma nova imagem e atualizar a tag no APAE-INFRA fica em um **job dentro do próprio pipeline de GitHub Actions** dos repositórios de aplicação — não no componente separado "ArgoCD Image Updater". Motivo: evita rodar mais um controller com credenciais de escrita dentro do cluster, mantém rastreabilidade direta entre o commit de infra e o run de CI que o gerou, e reage imediatamente ao push (sem espera de polling).

## Como uma mudança se propaga até o cluster

Duas origens de mudança, dois fluxos — mas **ambos terminam exigindo aprovação manual no ArgoCD**, já que o sync das Applications filhas não é automático.

### 1. Novo manifesto / config (mudança direta no APAE-INFRA)

1. Alguém abre um PR no APAE-INFRA alterando `kubernetes/base/...` ou `kubernetes/overlays/.../...`;
2. PR é revisado e mergeado em `main`;
3. O **ArgoCD Controller** (que já monitora continuamente todas as Applications, raiz e filhas, em paralelo) detecta que a Application filha correspondente está **Out-of-Sync** em relação ao Git;
4. Como o `syncPolicy` dessa Application filha é manual, o ArgoCD **não aplica sozinho** — apenas sinaliza o estado Out-of-Sync;
5. Alguém do time revisa a diferença no ArgoCD (UI ou CLI) e aprova o sync manualmente;
6. O ArgoCD aplica (`kubectl apply`/`prune`) os recursos correspondentes, atualizando os Pods/Deployments do namespace afetado.

### 2. Nova imagem de aplicação (deploy de código)

1. Um push/merge em um dos repositórios de aplicação (APAE, APAE-gestão escolar, APAE-atendimento ou APAE-site-comemorativo) dispara o pipeline de **CI** (GitHub Actions);
2. O CI builda a imagem e faz o **push da imagem** para o **GHCR** (Container Registry);
3. Um **job do próprio GitHub Actions (Image Updater)** identifica que uma nova imagem foi publicada e atualiza a tag no `kustomization.yaml` do overlay correspondente do APAE-INFRA (ex.: `kubernetes/overlays/dev/apae`), via PR para revisão adicional antes do commit;
4. A partir daqui o fluxo é o mesmo do caso 1: o ArgoCD Controller detecta que **a Application filha daquele repositório** está Out-of-Sync (a raiz não é afetada, pois a definição das Applications em `argocd/apps/` não mudou — apenas o conteúdo do overlay que a Application filha já apontava);
5. Alguém aprova o sync manualmente no ArgoCD;
6. O ArgoCD sincroniza a Application filha: normalmente isso é um **rolling update** do Deployment já existente (novos Pods sobem com a imagem nova do GHCR e os antigos são removidos gradualmente) — só no primeiro deploy daquela aplicação/ambiente é que os Pods são criados do zero.

Em ambos os casos, **a única forma de o cluster mudar é através de um commit no APAE-INFRA seguido de aprovação manual no ArgoCD** — nunca há `kubectl apply` manual nem alteração direta do GHCR/CI no cluster.

### Comportamento da Application raiz dentro do ArgoCD

A Application raiz (`apae-root`) já mantém as 4 filhas registradas no cluster o tempo todo, desde o bootstrap — ela roda seu próprio loop de sincronização continuamente, independente de qualquer push de imagem. O que acontece a cada deploy é a Application filha *já existente* entrando em Out-of-Sync porque o conteúdo do overlay que ela aponta mudou — não a criação de uma Application nova.

## Relação entre as Applications e os repositórios de aplicação

Escopo atual (4 Applications filhas administradas pelo ArgoCD):

| Repositório de aplicação | Application filha no ArgoCD | Overlay consumido |
|---|---|---|
| `APAE` | `apae` | `kubernetes/overlays/dev/apae` |
| `APAE-gestao-escolar` | `apae-gestao-escolar` | `kubernetes/overlays/dev/apae-gestao-escolar` |
| `APAE-atendimento` | `apae-atendimento` | `kubernetes/overlays/dev/apae-atendimento` |
| `APAE-site-comemorativo` | `apae-site-comemorativo` | `kubernetes/overlays/dev/apae-site-comemorativo` |

Cada repositório de aplicação é responsável apenas pelo seu código, pelo build/push da imagem e pelo job de Image Updater no CI; o *deploy* em si (quais recursos existem, quantas réplicas, em qual namespace) é responsabilidade exclusiva do APAE-INFRA e das Applications do ArgoCD.

## Observabilidade

As Applications de workload rodam no mesmo cluster monitorado pela stack de observabilidade (também gerenciada via GitOps, no mesmo padrão App of Apps):

- **Prometheus** coleta métricas dos Pods/Deployments de todas as aplicações;
- **Grafana** visualiza as métricas do Prometheus em dashboards;
- **Loki** centraliza os logs dos Pods, também visualizados no Grafana.