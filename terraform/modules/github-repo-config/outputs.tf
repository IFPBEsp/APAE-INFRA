output "repository_name" {
  description = "Nome do repositório configurado"
  value       = data.github_repository.repo.name
}

output "configured_labels" {
  description = "Nomes das labels configuradas"
  value       = keys(local.all_labels)
}

output "protected_branches" {
  description = "Branches protegidas configuradas"
  value       = var.protected_branches
}