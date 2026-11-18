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

variable "custom_labels" {
  description = "Labels adicionais específicas que queira passar além das padrão"
  type = map(object({
    color       = string
    description = string
  }))
  default = {}
}