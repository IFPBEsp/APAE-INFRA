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

> **Origem da imagem:** a infraestrutura aceita somente imagens do commit atual
> da `main` de cada produto, após as verificações de publicação. `dev`, quando
> usado como nome de ambiente, significa homologação, não a branch do build.

### 3. Push da imagem

A pipeline da `main` chama o workflow reutilizável de publicação do APAE-INFRA,
também referenciado em `@main`. Após build, scan, assinatura e verificação de
proveniência, publica a tag por commit e expõe o digest OCI. O digest identifica
o conteúdo exato que pode ser enviado para a infraestrutura.

### 4. Detecção e atualização do APAE-INFRA

O fluxo preparado usa GitHub Actions: o produto envia um evento
`gitops-image-published` para o Site ou `gitops-release-published` para a
combinação frontend/backend dos demais produtos, somente após a publicação
aprovada. O receptor no
APAE-INFRA confirma o digest no GHCR, autentica a proveniência da `main` e
confere se o commit ainda é o HEAD atual da `main` do produto. Só então prepara
um PR para a `main`, atualizando os digests no overlay `dev` e registrando a
versão candidata. Eventos atrasados de builds antigos são
recusados, inclusive quando o build terminou depois de uma revisão mais nova.

O PR exige revisão e merge humanos; o sync no ArgoCD continua manual. Antes do
merge, confirmar se não houve outra atualização da `main` do produto desde a
abertura do PR. A ativação depende dos overlays, das credenciais e da
publicação dos workflows descritos em
[Publicação a partir da main](workflows/publicacao-main-produtos.md).
Veja também [inputs, credenciais e exemplos de integração](workflows/update-image-overlay.md).

Os caminhos confirmados no PR #120 são:

| Produto | Overlay |
| --- | --- |
| APAE | `kubernetes/apae-geral/overlays/dev` |
| APAE-atendimento | `kubernetes/apae-atendimento/overlays/dev` |
| Site Comemorativo | `kubernetes/site-comemorativo/overlays/dev` |
| Gestão Escolar | `kubernetes/gestao-escolar/overlays/dev` |

Os overlays precisam existir em `main`. O receptor aceita apenas `dev`, rejeita
`hml` e `prod` e não recebe caminhos arbitrários no payload. A promoção de
`dev` para `prod` pertence à #106 e preservará a combinação de digests aprovada,
sem novo build.

A #82 permanece aberta até o teste completo com imagens reais.

A #106 configura sync manual na raiz e nas filhas. A automação de dispatch
executa na branch padrão da INFRA, atualmente `dev`; seus PRs alteram os
registros e overlays na `main`.

### 5. ArgoCD detecta a mudança

O ArgoCD monitora continuamente o repositório APAE-INFRA — e não o GHCR diretamente. Ao identificar que o manifesto mudou (estado do cluster passa a "Out of Sync"), ele reconhece que o estado desejado é diferente do estado atual.

### 6. Aplicação no cluster (padrão App of Apps)

O padrão **App of Apps** usa uma raiz para registrar oito Applications filhas:
uma por produto e ambiente (`dev` ou `prod`). A raiz e as filhas acompanham a
`main` e exigem sync manual. A raiz reconcilia as definições das filhas; cada
filha reconcilia os workloads do seu overlay de forma independente.

A promoção para `prod` é solicitada por um workflow separado e só utiliza
digests de um registro aprovado após homologação. O procedimento e as
evidências de rollback estão em [Releases GitOps](workflows/releases-gitops.md).

## Papel de cada repositório

| Repositório | Responsabilidade |
| --- | --- |
| APAE, APAE-atendimento, APAE-gestao-escolar, apae-site-comemorativo | Código da aplicação, testes e geração da imagem via CI |
| APAE-INFRA | GitOps repo: fonte da verdade do estado do cluster (manifestos), ponto de entrada para o ArgoCD |

## Observação

Os quatro repositórios de aplicação não se comunicam entre si nem diretamente com o cluster. Toda a orquestração passa pelo APAE-INFRA, que centraliza o que deve estar rodando e em qual versão. A observabilidade (métricas, logs, dashboards) roda em cima dessa mesma estrutura de Pods/Deployments, mas é tratada em documento separado (issue #13).
