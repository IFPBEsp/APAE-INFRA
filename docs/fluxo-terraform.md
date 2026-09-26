# Fluxo e Arquitetura do Terraform — APAE-INFRA

## Visão Geral

O Terraform é utilizado para provisionar e gerenciar a infraestrutura base do projeto APAE em uma VPS na **Contabo**, incluindo a instalação do cluster Kubernetes, configuração de rede e recursos de computação.

## Organização de Módulos

Os módulos ficam em `/terraform/modules/` e são blocos reutilizáveis de infraestrutura:

| Módulo | Responsabilidade |
|---|---|
| `kubernetes-cluster/` | Instala e configura o Kubernetes na VPS |
| `network/` | Configura rede e regras de firewall |
| `compute/` | Provisiona e configura a VPS |
| `object-storage/` | Gerencia armazenamento de objetos na VPS |

## Separação por Ambiente

Os ambientes ficam em `/terraform/environments/` e cada um consome os módulos com configurações diferentes:

- **dev/** — configurações mínimas para desenvolvimento
- **hml/** — configurações intermediárias para homologação
- **prod/** — configurações completas para produção

## Terraform State

O state do Terraform é armazenado **localmente na própria VPS Contabo**, no caminho definido pelo backend do Terraform.

- **Localização:** arquivo `terraform.tfstate` na VPS Contabo
- **Acesso:** o executor do Terraform (GitHub Actions) acessa o state via SSH ou mount remoto configurado no backend
- **Concorrência:** apenas um `apply` deve ser executado por vez — o controle é feito pelo próprio fluxo GitOps, onde o `apply` só ocorre após merge na branch principal, evitando execuções simultâneas

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

Após o merge na branch principal, o mecanismo de reconciliação executa o `terraform apply`, aplicando as mudanças na VPS Contabo. O Git é a fonte da verdade — toda mudança de infraestrutura passa obrigatoriamente por PR e revisão antes de ser aplicada.

## Recursos Provisionados

- VPS Contabo
- Cluster Kubernetes (instalado via Terraform)
- Configuração de rede e firewall
- Armazenamento de objetos na VPS