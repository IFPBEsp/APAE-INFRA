# Repositório de Infraestrutura
module "apae_infra" {
  source          = "../../modules/github-repo-config"
  repository_name = "APAE-INFRA"
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