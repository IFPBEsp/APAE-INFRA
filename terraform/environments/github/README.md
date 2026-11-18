# Gerenciamento de Configurações dos Repositórios GitHub com Terraform

Este diretório gerencia a governança e padronização das configurações dos repositórios da organização **`IFPBEsp`** (iniciando por `APAE-INFRA`) como código (IaC).

## O que é gerenciado

- **Branch Protection Rules:** Regras de proteção para as branches `main` e `dev` (revisões obrigatórias, status checks, bloqueio de force-push e exclusão).
- **Labels padronizadas:** Rótulos comuns de trabalho e a escala Fibonacci para estimativa de esforço (`1`, `2`, `3`, `5`, `8`, `13`).
- **Environments:** Ambientes padronizados para fluxos de deploy (`development`, `staging`, `production`).

> **Fora de escopo:** Criação ou exclusão de repositórios. O Terraform utiliza o data source `data.github_repository` para gerenciar apenas configurações de repositórios pré-existentes.

---

## Autenticação com GitHub App (Escopo Mínimo)

O provider `integrations/github` é autenticado através de uma **GitHub App** instalada na organização `IFPBEsp`, garantindo privilégio mínimo e auditabilidade sem depender de Personal Access Tokens (PATs) pessoais.

### Permissões Mínimas da GitHub App

| Categoria | Permissão | Justificativa |
| --- | --- | --- |
| **Administration** | `Read and write` | Configurar e aplicar regras de Branch Protection em `main` e `dev`. |
| **Issues** | `Read and write` | Criar, atualizar e padronizar labels do repositório. |
| **Environments** | `Read and write` | Gerenciar os ambientes de deploy e suas proteções. |
| **Metadata** | `Read-only` | Acesso básico a metadados do repositório (exigido pelo GitHub). |

### Variáveis Necessárias

As seguintes variáveis são exigidas para executar o Terraform:

| Variável | Descrição |
| --- | --- |
| `github_app_id` | ID numérico da GitHub App (obtido na página *General* da App). |
| `github_app_installation_id` | ID da instalação da App na organização `IFPBEsp`. |
| `github_app_pem_file` | Conteúdo da chave privada `.pem` gerada para a App. |

Essas variáveis são passadas localmente via `terraform.tfvars` (ou variáveis de ambiente `TF_VAR_*`) e no HCP Terraform / CI como secrets sensíveis.

---

## Execução e Importação de Repositórios

O ambiente utiliza o arquivo `imports.tf` com blocos `import` declarativos (Terraform >= 1.5) para importar as labels e proteções de branch já configuradas na interface web:

```bash
# 1. Inicializar providers e backend
terraform init

# 2. Executar o plano de execução (verificar se as importações são reconhecidas)
terraform plan

# 3. Aplicar as configurações
terraform apply
```
