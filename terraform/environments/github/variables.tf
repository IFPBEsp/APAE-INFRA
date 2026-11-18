variable "github_app_id" {
  description = "ID da GitHub App criada na organização IFPBEsp"
  type        = string
}

variable "github_app_installation_id" {
  description = "ID de instalação da GitHub App na organização IFPBEsp"
  type        = string
}

variable "github_app_pem_file" {
  description = "Conteúdo da chave privada (.pem) da GitHub App. Para carregar a partir de um arquivo local, utilize a função file(\"caminho/para/chave.pem\")"
  type        = string
  sensitive   = true
}