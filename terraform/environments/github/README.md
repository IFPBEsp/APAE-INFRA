# Gerenciamento de Configurações dos Repositórios GitHub com Terraform

Este diretório gerencia a governança e padronização das configurações dos repositórios da organização **`IFPBEsp`** (iniciando por `APAE-INFRA`) como código (IaC).

## O que é gerenciado

- **Branch Protection Rules:** Regras de proteção para as branches `main` e `dev` (revisões obrigatórias, status checks, bloqueio de force-push e exclusão).
- **Labels padronizadas:** Rótulos comuns de trabalho e a escala Fibonacci para estimativa de esforço (`1`, `2`, `3`, `5`, `8`, `13`).
- **Environments:** Ambientes padronizados para fluxos de deploy (`development`, `staging`, `production`). No `APAE-INFRA`, o `production` exige aprovação de `henriquetomazzz` ou `LuizArtur29`, impede autoaprovação e bypass de administradores e aceita deploy somente da `main`. É usado pelo [`ansible-apply.yml`](../../../docs/workflows/ansible-apply.md).

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
| `github_app_pem_file` | Conteúdo da chave privada `.pem` gerada para a App (em caso de arquivo local, passe com `file(...)`). |

Essas variáveis devem ser configuradas como **Terraform Variables** (marcadas como sensíveis, especialmente `github_app_pem_file`) na aba **Variables** do workspace no **HCP Terraform**. Em execuções locais de teste, podem ser passadas via `terraform.tfvars` (ignorado pelo git, utilizando heredoc para o conteúdo do PEM) ou via variáveis de ambiente `TF_VAR_*`.

---

## Configuração do HCP Terraform (Pré-requisitos)

O estado e a execução deste ambiente utilizam o **HCP Terraform** (antigo Terraform Cloud) através do bloco `cloud` em `backend.tf`:

- **Organização:** `ifpb-esp-apae`
- **Workspace:** `apae-infra-github`
- **Versão do Terraform:** `1.17.2` (ou `>= 1.5.0` conforme `providers.tf`).

### Configurações do Workspace

Para que a execução remota localize corretamente os módulos compartilhados referenciados relativamente (como `../../modules/github-repo-config`), o workspace está configurado com:

1. **Execution Mode:** `Project default` (definido como **Remote**, onde os planos e aplicações rodam na infraestrutura do HCP Terraform).
2. **Terraform Version:** `1.17.2`
3. **Terraform Working Directory:** `terraform/environments/github`
   - *Importante:* O HCP Terraform executa a partir da raiz do repositório e altera o diretório de trabalho para `terraform/environments/github` antes de rodar os comandos, permitindo que módulos fora do diretório (como `../../modules/github-repo-config`) sejam empacotados e referenciados sem erros.
4. **Variables:**
   - Cadastradas no workspace em **Variables** as variáveis do tipo Terraform `github_app_id`, `github_app_installation_id` e `github_app_pem_file` (marcada como **Sensitive**).

---

## Execução e Importação de Repositórios

Após configurar o workspace no HCP Terraform e autenticar o CLI (`terraform login`), o ambiente utiliza o arquivo `imports.tf` com blocos `import` declarativos (Terraform >= 1.5) para importar as labels e proteções de branch já existentes:

```bash
# 1. Navegar até o diretório do ambiente
cd terraform/environments/github

# 2. Inicializar providers e backend remoto
terraform init

# 3. Executar o plano de execução (verificar se as importações são reconhecidas remotamente)
terraform plan

# 4. Aplicar as configurações
terraform apply
```
