variable "github_app_id" {
  description = "ID da GitHub App criada na organização IFPBEsp"
  type        = string
}

variable "github_app_installation_id" {
  description = "ID de instalação da GitHub App na organização IFPBEsp"
  type        = string
}

variable "github_app_pem_file" {
  description = "Conteúdo ou caminho da chave privada (.pem) da GitHub App"
  type        = string
  sensitive   = true
}