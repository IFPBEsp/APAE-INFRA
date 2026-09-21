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

## Separação por Ambiente

Os ambientes ficam em `/terraform/environments/` e cada um consome os módulos com configurações diferentes:

- **dev/** — configurações mínimas para desenvolvimento
- **hml/** — configurações intermediárias para homologação
- **prod/** — configurações completas para produção

## Terraform State

O state do Terraform é armazenado **localmente na própria VPS Contabo**:

- **Localização:** arquivo `terraform.tfstate` na VPS
- **Atenção:** o state local exige que todos os membros do time que executam o Terraform tenham acesso à VPS e ao arquivo de state para evitar conflitos

## Fluxo de plan/apply

As mudanças de infraestrutura seguem o seguinte fluxo:

1. Desenvolvedor faz push no GitHub
2. GitHub Actions dispara automaticamente
3. `terraform init` — inicializa os módulos
4. `terraform plan` — exibe o que será criado/alterado/destruído
5. Aprovação manual por membro autorizado da squad
6. `terraform apply` — aplica as mudanças na VPS Contabo

## Recursos Provisionados

- VPS Contabo
- Cluster Kubernetes (instalado manualmente via Terraform)
- Configuração de rede e firewall