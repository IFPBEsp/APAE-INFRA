# Fluxo de comunicação entre os repositórios

Este documento descreve o caminho percorrido desde um commit em um repositório de aplicação até essa aplicação estar rodando no cluster, e qual o papel do repositório **APAE-INFRA** nesse processo.

## Repositórios envolvidos

- [**APAE**](https://github.com/IFPBEsp/APAE)
- [**APAE-atendimento**](https://github.com/IFPBEsp/APAE-atendimento)
- [**APAE-gestao-escolar**](https://github.com/IFPBEsp/APAE-gestao-escolar)
- [**apae-site-comemorativo**](https://github.com/IFPBEsp/apae-site-comemorativo)
- **APAE-INFRA**

Os quatro primeiros são repositórios de aplicação. Cada um segue exatamente o mesmo fluxo, de forma independente dos demais.

## Etapas do fluxo

### 1. Commit no repositório de aplicação

O desenvolvedor abre um PR a partir de uma feature branch em um dos quatro repositórios de aplicação (por exemplo, APAE-atendimento).

### 2. Pipeline de CI (GitHub Actions)

A #106 padronizará a publicação rastreável a partir da `main`. O fluxo previsto
para cada repositório de aplicação passa por um pipeline de CI em 3 estágios, conforme o código avança até a branch principal:

1. **PR para a `dev`** — dispara a pipeline de validação da feature: lint, testes, build e validação do Dockerfile.
2. **Merge na `dev`** — abre um novo PR para a `main`, que dispara a pipeline de validação de integração: testes completos e testes de integração.
3. **Merge na `main`** — dispara a pipeline de build da release: testes finais, build da imagem Docker, scan de segurança e versionamento.

> O receptor GitOps é implementado pelo PR #97 no APAE-INFRA. A integração
> dos produtos, a proveniência e a promoção serão implementadas na #106.

### 3. Push da imagem

Ao final da pipeline de release (estágio 3 do CI), a imagem gerada recebe uma nova tag e é enviada ao **GHCR (GitHub Container Registry)**. Essa tag é o que identifica de forma única a nova versão da aplicação.

### 4. Detecção e atualização do APAE-INFRA

Após a integração dos produtos pela #106, uma publicação bem-sucedida no GHCR fará o pipeline enviar um evento `repository_dispatch` ao APAE-INFRA, que chama internamente o **workflow reutilizável de atualização GitOps**. Ele abre ou atualiza um Pull Request para `main` no APAE-INFRA, gravando o digest da imagem no overlay de `dev` (homologação) e registrando tag, commit e repositório de origem. O PR exige revisão humana antes do merge; o sync no ArgoCD permanece manual. Veja [inputs, credenciais e exemplos de integração](workflows/update-image-overlay.md).

Os caminhos confirmados no PR #120 são:

| Produto | Overlay |
| --- | --- |
| APAE | `kubernetes/apae-geral/overlays/dev` |
| APAE-atendimento | `kubernetes/apae-atendimento/overlays/dev` |
| Site Comemorativo | `kubernetes/site-comemorativo/overlays/dev` |
| Gestão Escolar | Pendente de #38/#92; sem caminho definido |

Os overlays precisam existir em `main`. O receptor aceita apenas `dev`, rejeita
`hml` e `prod` e não recebe caminhos arbitrários no payload. A promoção de
`dev` para `prod` pertence à #106 e preservará a combinação de digests aprovada,
sem novo build.

A conferência da tag e do digest no GHCR não comprova a proveniência do build.
`source_repository` e `source_commit` são declarações; a verificação
criptográfica futura da #106 deve ocorrer após a consulta ao GHCR e antes de
gerar o token de escrita do App. O PR #97 não implementa essa verificação.
A #82 permanece aberta até o teste completo com imagens reais.

O PR #120 declara sync automático em `dev`, divergindo do requisito de sync
manual para homologação. A política precisa ser alinhada com #92/#106 antes
da ativação; este PR não altera Applications ou bootstrap do ArgoCD.

### 5. ArgoCD detecta a mudança

O ArgoCD monitora continuamente o repositório APAE-INFRA — e não o GHCR diretamente. Ao identificar que o manifesto mudou (estado do cluster passa a "Out of Sync"), ele reconhece que o estado desejado é diferente do estado atual.

### 6. Aplicação no cluster (padrão App of Apps)

O ArgoCD Controller não sincroniza cada aplicação diretamente. Ele aponta para uma **Aplicação Raiz (App of Apps)**, responsável por garantir que as Applications filhas existam e estejam corretas. Essa Aplicação Raiz descobre as Applications autorizadas para seu ambiente. O PR #120 define três Applications de produtos; Gestão Escolar ainda depende da #38/#92. Cada Application faz seu próprio `sync`, garantindo que os Pods/Deployments no cluster fiquem idênticos ao que está declarado no manifesto — e é assim que cada repositório é atualizado de forma independente.

## Papel de cada repositório

| Repositório | Responsabilidade |
| --- | --- |
| APAE, APAE-atendimento, APAE-gestao-escolar, apae-site-comemorativo | Código da aplicação, testes e geração da imagem via CI |
| APAE-INFRA | GitOps repo: fonte da verdade do estado do cluster (manifestos), ponto de entrada para o ArgoCD |

## Observação

Os quatro repositórios de aplicação não se comunicam entre si nem diretamente com o cluster. Toda a orquestração passa pelo APAE-INFRA, que centraliza o que deve estar rodando e em qual versão. A observabilidade (métricas, logs, dashboards) roda em cima dessa mesma estrutura de Pods/Deployments, mas é tratada em documento separado (issue #13).
