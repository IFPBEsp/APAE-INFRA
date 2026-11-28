# Repositório de Infraestrutura
module "apae_infra" {
  source          = "../../modules/github-repo-config"
  repository_name = "APAE-INFRA"

  branch_status_checks = {
    dev = {
      strict   = false
      contexts = ["Commitlint / Validate commits and PR title"]
    }
  }

  # Aplicação do Ansible na VPS (.github/workflows/ansible-apply.yml, #110):
  # somente código da main, com aprovação de outra pessoa e sem bypass de admin.
  # Os secrets do Environment (chave SSH, host, Vault) são cadastrados fora do
  # Terraform, para não ficarem no state.
  environment_protection = {
    production = {
      reviewer_users      = ["henriquetomazzz", "LuizArtur29"]
      prevent_self_review = true
      can_admins_bypass   = false
      deployment_branches = ["main"]
    }
  }
}

# No futuro, basta descomentar para padronizar os demais repositórios da APAE:
# module "apae_backend" {
#   source          = "../../modules/github-repo-config"
#   repository_name = "APAE-BACKEND"
# }

# module "apae_frontend" {
#   source          = "../../modules/github-repo-config"
#   repository_name = "APAE-FRONTEND"
# }