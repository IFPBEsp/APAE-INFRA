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