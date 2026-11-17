terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

data "github_repository" "repo" {
  name = var.repository_name
}

locals {
  default_labels = {
    "1"  = { color = "0E8A16", description = "1 Story Point - Esforço mínimo" }
    "2"  = { color = "1D76DB", description = "2 Story Points - Esforço pequeno" }
    "3"  = { color = "5319E7", description = "3 Story Points - Esforço médio-baixo" }
    "5"  = { color = "FBCA04", description = "5 Story Points - Esforço médio" }
    "8"  = { color = "D93F0B", description = "8 Story Points - Esforço grande" }
    "13" = { color = "B60205", description = "13 Story Points - Esforço muito grande" }

    "feature"     = { color = "0E8A16", description = "Nova funcionalidade" }
    "bug"         = { color = "D73A4A", description = "Algo não está funcionando corretamente" }
    "infra"       = { color = "5319E7", description = "Tarefas relacionadas à infraestrutura" }
    "terraform"   = { color = "844FBA", description = "Configurações e recursos Terraform" }
    "docs"        = { color = "0075CA", description = "Melhorias ou adições à documentação" }
    "ci"          = { color = "FEF2C0", description = "Workflows e automações de CI/CD" }
    "blocked"     = { color = "000000", description = "Impedido por dependência externa" }
  }

  all_labels = merge(local.default_labels, var.custom_labels)
}

resource "github_issue_label" "labels" {
  for_each    = local.all_labels
  repository  = data.github_repository.repo.name
  name        = each.key
  color       = each.value.color
  description = each.value.description
}

resource "github_branch_protection" "protection" {
  for_each      = toset(var.protected_branches)
  repository_id = data.github_repository.repo.node_id
  pattern       = each.key

  enforce_admins = true

  required_pull_request_reviews {
    dismiss_stale_reviews           = true
    required_approving_review_count = var.required_approving_review_count
    require_code_owner_reviews      = false
  }

  allows_deletions    = false
  allows_force_pushes = false
}

resource "github_repository_environment" "environments" {
  for_each    = toset(var.environments)
  repository  = data.github_repository.repo.name
  environment = each.key
}