terraform {
  required_version = ">= 1.5.0"

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
    "1"  = { color = "1b9e4b", description = "Fibonacci: trivial, mudança pontual sem investigação" }
    "2"  = { color = "55b95c", description = "Fibonacci: pequeno, escopo claro e baixo risco" }
    "3"  = { color = "9ecb5d", description = "Fibonacci: moderado, mais de uma etapa sem incerteza" }
    "5"  = { color = "d9cb5a", description = "Fibonacci: considerável, múltiplas etapas ou dependência externa" }
    "8"  = { color = "e8a33d", description = "Fibonacci: grande, escopo amplo ou parcialmente indefinido" }
    "13" = { color = "e2683d", description = "Fibonacci: muito grande, alta incerteza, candidata a divisão" }

    "feature"   = { color = "61f378", description = "Nova capacidade ou funcionalidade para infraestrutura ou plataforma." }
    "bug"       = { color = "d73a4a", description = "Correção de comportamento incorreto ou inesperado." }
    "infra"     = { color = "bfd4f2", description = "Tarefas relacionadas à infraestrutura" }
    "terraform" = { color = "862078", description = "Infraestrutura como código, módulos e configurações Terraform." }
    "ci"        = { color = "5c90b2", description = "Pipelines de build, testes e integração contínua." }
    "docs"      = { color = "0075CA", description = "Melhorias ou adições à documentação" }
    "blocked"   = { color = "000000", description = "Impedido por dependência externa" }
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