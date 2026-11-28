variable "repository_name" {
  description = "Nome do repositório existente no GitHub (ex: APAE-INFRA)"
  type        = string
}

variable "protected_branches" {
  description = "Lista de branches para aplicar regras de proteção"
  type        = list(string)
  default     = ["main", "dev"]
}

variable "branch_status_checks" {
  description = "Mapa de configurações de required_status_checks indexado pelo nome/padrão da branch"
  type = map(object({
    strict   = optional(bool, false)
    contexts = optional(list(string), [])
  }))
  default = {}
}

variable "required_approving_review_count" {
  description = "Número mínimo de revisões necessárias para aprovar um PR"
  type        = number
  default     = 1
}

variable "environments" {
  description = "Lista de environments a serem criados no repositório"
  type        = list(string)
  default     = ["development", "staging", "production"]
}

variable "environment_protection" {
  description = <<-EOT
    Regras de proteção por environment, indexadas pelo nome (que precisa constar em `environments`).
    - reviewer_users: logins que podem aprovar o deployment (máximo de 6).
    - prevent_self_review: impede que quem disparou a execução a aprove.
    - can_admins_bypass: permite que administradores ignorem as regras.
    - deployment_branches: padrões de branch autorizados a fazer deploy; vazio mantém qualquer branch.
  EOT
  type = map(object({
    reviewer_users      = optional(list(string), [])
    prevent_self_review = optional(bool, true)
    can_admins_bypass   = optional(bool, false)
    deployment_branches = optional(list(string), [])
  }))
  default = {}

  validation {
    condition     = alltrue([for name in keys(var.environment_protection) : contains(var.environments, name)])
    error_message = "Toda chave de environment_protection precisa constar em environments."
  }

  validation {
    condition = alltrue([
      for settings in values(var.environment_protection) :
      length(settings.reviewer_users) >= 1 && length(settings.reviewer_users) <= 6
    ])
    error_message = "Cada environment protegido precisa de 1 a 6 revisores em reviewer_users."
  }
}

variable "custom_labels" {
  description = "Labels adicionais específicas que queira passar além das padrão"
  type = map(object({
    color       = string
    description = string
  }))
  default = {}
}