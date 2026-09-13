# Fluxo e Arquitetura do Terraform — APAE-INFRA

## Visão Geral

O Terraform é utilizado para provisionar e gerenciar a infraestrutura base do projeto APAE na Oracle Cloud (OCI), incluindo o cluster Kubernetes (OKE), VMs, redes e o bucket de armazenamento do state.

## Organização de Módulos

Os módulos ficam em `/terraform/modules/` e são blocos reutilizáveis de infraestrutura:

| Módulo | Responsabilidade |
|---|---|
| `kubernetes-cluster/` | Provisiona o cluster OKE |
| `network/` | Cria VPC e subnets |
| `compute/` | Provisiona VMs |
| `object-storage/` | Cria bucket para armazenar o state |

## Separação por Ambiente

Os ambientes ficam em `/terraform/environments/` e cada um consome os módulos com configurações diferentes:

- **dev/** — configurações mínimas para desenvolvimento
- **hml/** — configurações intermediárias para homologação
- **prod/** — configurações completas para produção

## Backend de State

O state do Terraform é armazenado remotamente no **Oracle Object Storage** para garantir consistência entre execuções e membros do time:

- **Bucket:** Oracle Object Storage
- **Arquivo:** `terraform.tfstate`
- **Lock:** OCI Lock para evitar execuções simultâneas

## Fluxo de plan/apply

As mudanças de infraestrutura seguem o seguinte fluxo:

1. Desenvolvedor faz push no GitHub
2. GitHub Actions dispara automaticamente
3. `terraform init` — inicializa o backend e os módulos
4. `terraform plan` — exibe o que será criado/alterado/destruído
5. Aprovação manual por membro autorizado da squad
6. `terraform apply` — aplica as mudanças na Oracle Cloud

## Recursos Provisionados

- Cluster Kubernetes (OKE)
- VMs
- VPC e Subnets
- Object Storage (bucket do state)