# Fluxo de comunicação entre os repositórios

Este documento descreve o caminho percorrido desde um commit em um repositório de aplicação até essa aplicação estar rodando no cluster, e qual o papel do repositório **APAE-INFRA** nesse processo.

## Repositórios envolvidos

- **APAE**
- **APAE-atendimento**
- **APAE-gestao-escolar**
- **apae-site-comemorativo**
- **APAE-INFRA** (orquestração / GitOps repo)

Os quatro primeiros são repositórios de aplicação. Cada um segue exatamente o mesmo fluxo, de forma independente dos demais.

## Etapas do fluxo

**1. Commit no repositório de aplicação**

O desenvolvedor abre um PR e faz merge em um dos quatro repositórios de aplicação (por exemplo, APAE-atendimento).

**2. GitHub Actions (CI)**

O merge dispara o workflow de CI configurado naquele repositório. Ele executa build, roda os testes automatizados e, se tudo passar, gera a imagem da aplicação.

**3. Push da imagem**

A imagem gerada recebe uma nova tag e é enviada ao **GHCR (GitHub Container Registry)**. Essa tag é o que identifica de forma única a nova versão da aplicação.

**4. Detecção e atualização do APAE-INFRA**

O **ArgoCD Image Updater** monitora o GHCR e identifica que uma nova imagem foi publicada. Ele então abre um Pull Request no repositório APAE-INFRA (GitOps repo) atualizando a tag da imagem no manifesto correspondente. Esse PR passa por aprovação manual antes do merge — é essa aprovação que efetivamente confirma que a nova versão deve ir para o cluster.

**5. ArgoCD detecta a mudança**

O ArgoCD monitora continuamente o repositório APAE-INFRA. Ao identificar que o manifesto mudou (estado do cluster passa a "Out of Sync"), ele reconhece que o estado desejado é diferente do estado atual.

**6. Aplicação no cluster (padrão App of Apps)**

O ArgoCD Controller não sincroniza cada aplicação diretamente. Ele aponta para uma **Aplicação Raiz (App of Apps)**, responsável por garantir que as Applications filhas existam e estejam corretas. Essa Aplicação Raiz gerencia as 4 Applications, uma para cada repositório (APAE, APAE-atendimento, APAE-gestao-escolar, apae-site-comemorativo). Cada Application faz seu próprio `sync`, garantindo que os Pods/Deployments no cluster fiquem idênticos ao que está declarado no manifesto — e é assim que cada repositório é atualizado de forma independente.

## Papel de cada repositório

| Repositório | Responsabilidade |
|---|---|
| APAE, APAE-atendimento, APAE-gestao-escolar, apae-site-comemorativo | Código da aplicação, testes e geração da imagem via CI |
| APAE-INFRA | GitOps repo: fonte da verdade do estado do cluster (manifestos), ponto de entrada para o ArgoCD |

## Observação

Os quatro repositórios de aplicação não se comunicam entre si nem diretamente com o cluster. Toda a orquestração passa pelo APAE-INFRA, que centraliza o que deve estar rodando e em qual versão. A observabilidade (métricas, logs, dashboards) roda em cima dessa mesma estrutura de Pods/Deployments, mas é tratada em documento separado (issue #13).
