# Kubernetes — APAE-INFRA

## Visão geral

Este diretório contém os manifests Kubernetes dos produtos da APAE, organizados com Kustomize para permitir configurações específicas por ambiente sem duplicar os recursos base.

A infraestrutura utiliza o ArgoCD para implementar o fluxo GitOps, mantendo o repositório APAE-INFRA como fonte declarativa das configurações dos workloads Kubernetes.

As responsabilidades são divididas entre:

- **Terraform:** provisionamento da infraestrutura fundacional.
- **Ansible:** provisionamento do k3s, instalação do ArgoCD e aplicação dos objetos de bootstrap.
- **ArgoCD:** descoberta das Applications filhas e reconciliação dos recursos Kubernetes dos produtos.
- **GitHub Actions:** integração contínua, publicação de imagens e automação de Pull Requests para atualização dos manifests.

O Ansible permanece responsável pelos AppProjects e pela Application raiz. O ArgoCD não deve gerenciar esses objetos para evitar conflitos de responsabilidade.

## Estrutura

Os manifests são organizados por produto, com separação entre recursos base e configurações específicas dos ambientes.

```text
kubernetes/
├── apae-geral/
│   ├── base/
│   └── overlays/
│       └── dev/
│           └── kustomization.yaml
├── apae-atendimento/
│   ├── base/
│   └── overlays/
│       └── dev/
│           └── kustomization.yaml
├── gestao-escolar/
│   ├── base/
│   └── overlays/
│       └── dev/
│           └── kustomization.yaml
├── site-comemorativo/
│   ├── base/
│   └── overlays/
│       └── dev/
│           └── kustomization.yaml
└── README.md
```

### Manifests base

Os diretórios `base/` contêm as definições compartilhadas dos serviços, incluindo:

- Deployments;
- Services;
- ConfigMaps não sensíveis;
- Probes de inicialização, disponibilidade e integridade;
- Limites e requisições de recursos computacionais;
- Configurações de segurança dos containers.

Os recursos base devem permanecer independentes dos ambientes sempre que possível.

### Overlays

Os diretórios `overlays/` utilizam Kustomize para aplicar configurações específicas de cada ambiente.

Os overlays podem definir:

- Namespace de destino;
- Quantidade de réplicas;
- Imagens e versões utilizadas;
- Configurações específicas do ambiente.

O escopo inicial da issue #92 contempla somente o overlay `dev`.

Os overlays `hml` e `prod` serão implementados posteriormente, conforme a evolução da infraestrutura e do fluxo de promoção.

## Ambiente de desenvolvimento

O ambiente `dev` utiliza inicialmente o namespace Kubernetes `apae-dev`.

Os serviços possuem a seguinte configuração:

| Produto | Serviço | Réplicas | Situação |
| --- | --- | ---: | --- |
| APAE Geral | `apae` | 0 | Publicação e acesso à imagem pendentes de confirmação |
| APAE Geral | `api` | 0 | Publicação e acesso à imagem pendentes de confirmação |
| APAE Geral | `management-app` | 0 | Sem imagem publicada |
| APAE Atendimento | `atendimento` | 0 | Sem imagem publicada |
| APAE Atendimento | `atendimento-app` | 0 | Sem imagem publicada |
| APAE Gestão Escolar | `gestao-escolar-backend` | 0 | Publicação e acesso à imagem pendentes de confirmação |
| APAE Gestão Escolar | `gestao-escolar-frontend` | 0 | Publicação e acesso à imagem pendentes de confirmação |
| Site Comemorativo | `site-comemorativo` | 0 | Sem imagem publicada |

Os serviços sem imagem publicada permanecem com `replicas: 0`, evitando tentativas de inicialização com imagens indisponíveis.

A existência de uma referência de imagem no manifesto não comprova sua disponibilidade no registro.

Antes de aumentar a quantidade de réplicas, confirmar que a tag exata referenciada
no overlay existe e pode ser baixada pelo cluster: pacote público ou acesso via
`imagePullSecret`, conforme a estratégia da #93. A referência `:dev` não garante
que a imagem tenha sido publicada. Verificar também as configurações necessárias
e a disponibilidade de recursos no cluster. Habilitar as réplicas em uma alteração
revisada somente após essas verificações.

### Namespace

Todos os recursos definidos pelos overlays iniciais são direcionados ao namespace:

```text
apae-dev
```

A criação desse namespace não é responsabilidade das Applications dos produtos.

As Applications utilizam:

```yaml
syncOptions:
  - CreateNamespace=false
```

O namespace é declarado em `argocd/namespaces.yaml` e aplicado pelo Ansible
em `ansible/roles/argocd_bootstrap/tasks/bootstrap.yml`, antes dos AppProjects
e da Application raiz. Executar esse bootstrap antes da primeira sincronização
das Applications dos produtos. O manifesto permanece fora da descoberta da
raiz (`apps/*/*.yaml`), e o AppProject dos produtos continua sem permissão para
criar recursos de cluster.

O namespace compartilhado exige que cada recurso tenha uma identificação única para evitar conflitos entre Applications.

## Imagens e versionamento

Os overlays utilizam inicialmente referências de imagens com a tag `dev`.

Exemplos:

```yaml
images:
  - name: ghcr.io/ifpbesp/apae-geral-frontend
    newTag: dev
  - name: ghcr.io/ifpbesp/apae-geral-backend
    newTag: dev
```

Essas referências representam a configuração inicial dos overlays, não uma estratégia definitiva de versionamento.

A issue [#82](https://github.com/IFPBEsp/APAE-INFRA/issues/82) implementará o workflow reutilizável responsável pela atualização das referências de imagem após sua publicação.

O fluxo previsto consiste em:

1. O repositório do produto executa os testes e publica a imagem no GHCR.
2. O workflow de publicação disponibiliza a tag imutável e o digest.
3. A automação propõe um Pull Request no APAE-INFRA atualizando o overlay correspondente.
4. O Pull Request passa pela revisão exigida para o ambiente.
5. Após o merge, o ArgoCD detecta a alteração na revisão Git acompanhada pela Application.
6. A mudança é aplicada conforme a política de sincronização do ambiente.

A atualização dos manifests não deve exigir acesso direto das pipelines ao cluster Kubernetes.

A utilização de tags imutáveis ou digests permite rastrear a versão de imagem associada a cada implantação.

## Integração com ArgoCD

A infraestrutura utiliza o padrão **App of Apps** para registrar e gerenciar as Applications dos produtos.

Essa decisão mantém a arquitetura iniciada na issue [#91](https://github.com/IFPBEsp/APAE-INFRA/issues/91), sem introduzir ApplicationSet no escopo atual.

### Estrutura das Applications

As definições das Applications ficam no diretório `argocd/`, separadas por ambiente.

```text
argocd/
├── namespaces.yaml       # Criado pelo Ansible antes da raiz
├── app-of-apps.yaml
├── project.yaml
├── project-infra.yaml
├── README.md
└── apps/
    └── dev/
        ├── apae-geral-dev.yaml
        ├── apae-atendimento-dev.yaml
        ├── gestao-escolar-dev.yaml
        └── site-comemorativo-dev.yaml
```

Os arquivos `namespaces.yaml`, `app-of-apps.yaml`, `project.yaml` e
`project-infra.yaml` pertencem ao bootstrap administrado pelo Ansible.

As Applications filhas são declaradas na issue #92.

Cada Application aponta para o overlay correspondente:

| Application | Caminho do overlay |
| --- | --- |
| `apae-geral-dev` | `kubernetes/apae-geral/overlays/dev` |
| `apae-atendimento-dev` | `kubernetes/apae-atendimento/overlays/dev` |
| `gestao-escolar-dev` | `kubernetes/gestao-escolar/overlays/dev` |
| `site-comemorativo-dev` | `kubernetes/site-comemorativo/overlays/dev` |

As Applications utilizam o AppProject `apae` e direcionam os recursos ao namespace `apae-dev`.

### Separação entre ambientes

A Application raiz `apae-root`, definida na issue #91, acompanha a branch `main`
e registra as Applications dos ambientes no mesmo cluster k3s. Os workloads
são separados logicamente por namespace, conforme a #90.

As Applications de desenvolvimento ficam organizadas no diretório:

```text
argocd/apps/dev/
```

A raiz utiliza busca recursiva em `argocd/` com o filtro
`include: 'apps/*/*.yaml'`, incluindo `dev` e os futuros `hml` e `prod`.
Os objetos de bootstrap na raiz de `argocd/`, incluindo `namespaces.yaml`,
não correspondem ao filtro e continuam administrados pelo Ansible.

O bootstrap cria `apae-dev` antes dos AppProjects e da Application raiz.
Cada filha define sua política de sincronização: automática em `dev` e manual
nos demais ambientes quando implementados. A organização por diretório e
namespace não substitui os controles de RBAC e de rede.

As definições precisam estar disponíveis na revisão acompanhada pela raiz para
serem descobertas. A existência dos manifests no repositório não comprova sua
sincronização no cluster.

### Revisões Git

É necessário distinguir as revisões acompanhadas pelo ArgoCD:

- **Application raiz:** revisão Git utilizada para descobrir os manifests das Applications filhas.
- **Application filha:** revisão Git utilizada para carregar os manifests Kubernetes do produto.
- **Overlay:** caminho que contém as configurações do ambiente de destino.

As Applications iniciais da issue #92 utilizam `targetRevision: main`, conforme os manifests preparados.

Isso significa que alterações realizadas somente na branch `dev` do APAE-INFRA não são automaticamente consumidas por essas Applications.

Para um futuro fluxo de desenvolvimento que acompanhe diretamente a branch `dev`, as revisões Git e o bootstrap correspondente deverão ser ajustados explicitamente.

Não se deve presumir que o nome do overlay determina a branch Git acompanhada.

## AppProjects e controle de acesso

O bootstrap da issue #91 define dois AppProjects:

| AppProject | Responsabilidade |
| --- | --- |
| `apae-infra` | Application raiz e objetos GitOps autorizados |
| `apae` | Applications dos produtos APAE |

O AppProject `apae` restringe a origem dos manifests ao repositório:

```text
https://github.com/IFPBEsp/APAE-INFRA.git
```

E os destinos aos namespaces compatíveis com:

```text
apae-*
```

O projeto não concede permissões gerais para recursos de escopo global.

As permissões de recursos dentro dos namespaces devem ser limitadas aos tipos necessários para os workloads.

A configuração inicial da issue #91 já contempla recursos como Deployments, Services e ConfigMaps, utilizados pelos overlays da issue #92.

A aplicação e eventual alteração dos AppProjects continuam sob responsabilidade do Ansible.

Os AppProjects complementam, mas não substituem, os controles de acesso e RBAC nativos do Kubernetes.

## Política de sincronização

As políticas de sincronização são definidas de acordo com o ambiente.

| Ambiente | Política | Situação |
| --- | --- | --- |
| `dev` | Automática | Configurada nas Applications |
| `hml` | Manual | Implementação futura |
| `prod` | Manual | Implementação futura |

### Desenvolvimento

As Applications de desenvolvimento possuem:

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
  syncOptions:
    - CreateNamespace=false
```

Com essa configuração:

- O ArgoCD pode aplicar automaticamente alterações detectadas na revisão Git acompanhada.
- `selfHeal` permite reconciliar divergências entre o estado declarado e o estado do cluster.
- `prune` permite remover recursos gerenciados que deixaram de existir nos manifests desejados.
- O namespace de destino precisa existir previamente.

A configuração automática será efetiva somente após as Applications serem registradas em uma instância do ArgoCD com destino apropriado.

### Homologação e produção

Os ambientes `hml` e `prod` devem utilizar sincronização manual para os workloads, conforme o fluxo de aprovação e promoção a ser implementado.

A sincronização automática da Application raiz não deve ser interpretada como autorização para implantar workloads em produção.

## Validação local

Os overlays podem ser renderizados com Kustomize sem conexão com o cluster Kubernetes.

Execute na raiz do repositório:

```bash
kubectl kustomize kubernetes/apae-geral/overlays/dev
kubectl kustomize kubernetes/apae-atendimento/overlays/dev
kubectl kustomize kubernetes/gestao-escolar/overlays/dev
kubectl kustomize kubernetes/site-comemorativo/overlays/dev
```

Esses comandos não criam, modificam ou removem recursos no cluster.

### Verificações necessárias

A validação local deve conferir:

1. Renderização bem-sucedida dos quatro overlays.
2. Namespace `apae-dev` em todos os recursos.
3. Quantidade de réplicas de acordo com o ambiente.
4. Referências de imagens conforme a configuração dos overlays.
5. Preservação de Services, ConfigMaps, probes e configurações de segurança.
6. Ausência de recursos Kubernetes duplicados entre Applications.
7. Sintaxe YAML das Applications.

Na validação de 09/11/2026, foram renderizados **22 recursos sem conflitos de identificação** entre os quatro produtos:

| Produto | Recursos |
| --- | ---: |
| APAE Geral | 8 |
| APAE Atendimento | 5 |
| APAE Gestão Escolar | 6 |
| Site Comemorativo | 3 |
| **Total** | **22** |

O overlay de Gestão Escolar inclui frontend e backend, cada um com Deployment,
Service e ConfigMap. A validação conjunta dos quatro overlays confirmou o
namespace `apae-dev` e zero réplicas em todos os Deployments.

A validação de sintaxe YAML não substitui a validação de schema dos CRDs do ArgoCD.

Da mesma forma, a renderização com Kustomize não comprova que os serviços estejam funcionando no cluster.

### Validação no ArgoCD

Após a integração das dependências, verificar:

- Existência dos AppProjects `apae` e `apae-infra`;
- Namespace `apae-dev` provisionado;
- Applications registradas no namespace `argocd`;
- Caminhos e revisões Git acessíveis pelo ArgoCD;
- Ausência de recursos compartilhados gerenciados por Applications concorrentes;
- Estados de sincronização e saúde dos recursos;
- Funcionamento das políticas `prune` e `selfHeal` em ambiente apropriado.

A sincronização efetiva só deve ser habilitada depois da confirmação dos pré-requisitos de implantação.

## Pré-requisitos para implantação

Antes de sincronizar os workloads, verificar:

1. Cluster k3s operacional, conforme a issue #90.
2. Bootstrap do ArgoCD instalado e validado, conforme a issue #91.
3. AppProjects aplicados pelo Ansible.
4. Namespace de destino existente.
5. Applications descobertas pela raiz correspondente ao ambiente.
6. Manifests disponíveis na revisão Git acompanhada.
7. Imagens publicadas e acessíveis para os serviços com réplicas habilitadas.
8. ConfigMaps e demais configurações exigidas pelas aplicações disponíveis.
9. Ausência de conflitos de propriedade ou recursos duplicados.
10. Política de sincronização compatível com o cluster de destino.

É necessário considerar os recursos disponíveis na VPS antes de habilitar simultaneamente novos workloads.

A existência de manifests válidos não garante que os containers serão inicializados ou permanecerão saudáveis.

## Limites e dependências

A issue #92 estabelece a estrutura inicial dos overlays e das Applications dos produtos com manifests base disponíveis.

As principais dependências são:

- **Issue [#37](https://github.com/IFPBEsp/APAE-INFRA/issues/37):** manifests base do APAE Geral.
- **Issue [#38](https://github.com/IFPBEsp/APAE-INFRA/issues/38):** manifests base do APAE Gestão Escolar, presentes nesta branch.
- **Issue [#39](https://github.com/IFPBEsp/APAE-INFRA/issues/39):** manifests base do APAE Atendimento.
- **Issue [#40](https://github.com/IFPBEsp/APAE-INFRA/issues/40):** manifests base do Site Comemorativo.
- **Issue [#82](https://github.com/IFPBEsp/APAE-INFRA/issues/82):** atualização automatizada das referências das imagens.
- **Issue [#91](https://github.com/IFPBEsp/APAE-INFRA/issues/91):** instalação, configuração e bootstrap do ArgoCD.

Permanecem fora do escopo inicial:

- Overlays de homologação e produção;
- Gerenciamento de Secrets;
- Configuração de Ingress;
- Implementação de ApplicationSet;
- Separação definitiva dos clusters de desenvolvimento, homologação e produção;
- Implementação de pipelines de promoção entre ambientes.

## Estado da implementação

A issue #92 contempla a criação dos overlays `dev`, das Applications filhas e da documentação da estrutura Kubernetes.

As validações locais confirmaram os quatro overlays e 22 recursos sem conflitos.
Em 09/11/2026, uma validação temporária autorizada no cluster confirmou a
descoberta das quatro Applications, sincronização `Synced`/`Healthy` no commit
`3e124a260de1483837fbda35f813cd1d8f66477f`, zero réplicas e funcionamento de
`selfHeal` e `prune`. Os recursos temporários foram removidos após os testes.

A integração com o bootstrap da #91 está presente nesta branch: o Ansible cria
`apae-dev` e aplica a raiz com descoberta de `apps/*/*.yaml`. A CI renderiza os
quatro overlays `dev`, além das bases, para validar os manifests resultantes.

A sincronização definitiva pela raiz permanente ainda depende de disponibilizar
os manifests na `main`. O PR #120 tem `dev` como destino: integrá-lo somente
nessa branch não altera a revisão acompanhada pelo ArgoCD. A validação temporária
usou o commit do PR apenas nas cópias de teste, mantendo `targetRevision: main`
nos manifests versionados. Os serviços continuam com zero réplicas;
sincronização não significa disponibilidade dos produtos.

Consulte as [evidências e o procedimento após integração à main](../docs/argocd/validacao-applications-overlays.md).
