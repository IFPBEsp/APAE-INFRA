# Fluxo e Arquitetura do Terraform — APAE-INFRA

## Visão Geral

O Terraform é utilizado para provisionar e gerenciar a infraestrutura base do projeto APAE em uma VPS na **Contabo**, incluindo a instalação do cluster Kubernetes, configuração de rede e recursos de computação.

## Organização de Módulos

Os módulos ficam em `/terraform/modules/` e são blocos reutilizáveis de infraestrutura:

|Módulo|Responsabilidade|
|---|---|
|`kubernetes-cluster/`|Instala e configura o Kubernetes na VPS|
|`network/`|Configura rede e regras de firewall|
|`compute/`|Provisiona e configura a VPS|
|`object-storage/`|Gerencia armazenamento de objetos na VPS|

## Separação por Ambiente

Os ambientes ficam em `/terraform/environments/` e cada um consome os módulos com configurações diferentes:

- **dev/** — configurações mínimas para desenvolvimento
- **hml/** — configurações intermediárias para homologação
- **prod/** — configurações completas para produção

## Terraform State

A decisão atual é armazenar o state remotamente no **HCP Terraform**, fora da VPS e do cluster, conforme a implementação do [PR #101](https://github.com/IFPBEsp/APAE-INFRA/pull/101). A proposta anterior de manter `terraform.tfstate` na VPS foi substituída por esse backend.

- **Ambientes:** o workspace `apae-infra-dev` está configurado e validado. Os workspaces independentes `apae-infra-hml` e `apae-infra-prod` permanecem planejados.
- **Executor e acesso:** na CI de Pull Requests, o Terraform CLI executa no runner do GitHub Actions e acessa o HCP Terraform pela API autenticada do backend. O workspace usa o modo de execução local: o HCP armazena o state e controla seu lock, mas não executa o Terraform. Não há acesso ao state por SSH nem por montagem de um diretório da VPS.
- **Credenciais:** a inicialização autenticada e o `plan` usam a credencial do HCP disponibilizada ao job aprovado no ambiente `terraform-plan`. A configuração do executor e das credenciais do futuro `apply` ainda precisa ser definida; não é implementada neste PR.

### Concorrência, serialização e locking

Executar o `apply` somente após o merge **não impede execuções simultâneas**: merges consecutivos, reexecuções e comandos locais podem disputar o mesmo state. O fluxo de aplicação deve combinar duas proteções:

1. **Serialização no executor:** o futuro workflow de `apply` deverá usar um grupo de `concurrency` por ambiente/workspace, compartilhado pelas execuções que alteram o mesmo state, com `cancel-in-progress: false` para não interromper uma aplicação em andamento. Agrupar apenas pelo número do PR não serializa aplicações de PRs diferentes. Essa automação permanece pendente.
2. **Locking no backend:** o locking nativo do HCP Terraform protege o state também contra operações concorrentes originadas fora daquele workflow. Todas as operações devem usar o workspace correto e manter o locking habilitado. Uma falha ao adquirir o lock deve interromper a operação; não deve ser contornada com `-lock=false`.

O PR #101 registrou a validação do bloqueio administrativo e do desbloqueio do workspace `dev`. Não foi realizado um teste específico com duas operações concorrentes tentando adquirir o mesmo lock. Portanto, a configuração do backend não comprova que a serialização do futuro `apply` já esteja implementada ou validada.

## Fluxo de plan/apply

O fluxo é dividido em duas etapas distintas:

### Etapa 1 — CI em Pull Requests

A cada PR aberto contra `dev` ou `main`, o GitHub Actions executa automaticamente:

1. `terraform fmt` — verifica formatação
2. `terraform init` — inicializa os módulos e o backend
3. `terraform validate` — valida a sintaxe dos arquivos
4. `terraform plan` — exibe o que será criado/alterado/destruído

O `terraform apply` **não é executado nesta etapa**. O resultado do `plan` serve como evidência para revisão do time antes do merge.

### Etapa 2 — Apply pós-merge (GitOps)

O fluxo desejado é aplicar as mudanças revisadas após o merge na branch principal. O mecanismo e o executor definitivo do `terraform apply`, suas aprovações e a serialização por workspace ainda precisam ser definidos e implementados; este PR não configura uma aplicação automática pós-merge.

Antes de habilitar essa etapa, o executor deverá acessar o backend remoto autenticado e atender aos requisitos de serialização e locking descritos acima. O Git permanece como fonte da configuração desejada, com mudanças revisadas por PR antes da aplicação.

## Recursos Provisionados

- VPS Contabo
- Cluster Kubernetes (instalado via Terraform)
- Configuração de rede e firewall
- Armazenamento de objetos na VPS
