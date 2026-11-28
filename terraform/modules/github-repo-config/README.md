# Módulo Terraform: Configuração de Repositório GitHub (`github-repo-config`)

Módulo reutilizável para padronização e governança de configurações em repositórios da organização `IFPBEsp`.

## Recursos Gerenciados

1. **Labels (`github_issue_label`):**
   - Escala de Fibonacci: `1`, `2`, `3`, `5`, `8`, `13`.
   - Categorias padrão: `feature`, `bug`, `infra`, `terraform`, `docs`, `ci`, `blocked`.
   - Permite inclusão de rótulos específicos através da variável `custom_labels`.
2. **Branch Protection (`github_branch_protection`):**
   - Aplicado por padrão nas branches `main` e `dev`.
   - Exige revisão de Pull Request com pelo menos 1 aprovação (`dismiss_stale_reviews = true`).
   - Suporte a status checks obrigatórios parametrizáveis por branch via `branch_status_checks`.
   - Impede force push (`allows_force_pushes = false`) e exclusão de branch (`allows_deletions = false`).
3. **Environments (`github_repository_environment`):**
   - Cria os ambientes `development`, `staging` e `production` para pipelines de CI/CD.
   - Opcionalmente aplica proteções por ambiente via `environment_protection`: revisores obrigatórios (por login, de 1 a 6), `prevent_self_review`, bloqueio de bypass por administradores e restrição das branches que podem fazer deploy (`github_repository_environment_deployment_policy`).
   - Ambientes sem entrada em `environment_protection` são criados sem regras.
   - Secrets e variáveis dos ambientes não são gerenciados aqui, para não gravar valores sensíveis no state.

## Testes

```bash
cd terraform/modules/github-repo-config
terraform init -backend=false
terraform test
```

Os testes em `tests/` usam provider mockado e não acessam o GitHub.

## Como Utilizar

```hcl
module "meu_repositorio" {
  source          = "../../modules/github-repo-config"
  repository_name = "NOME-DO-REPOSITORIO"

  # Opcional: proteger um ambiente de deploy.
  environment_protection = {
    production = {
      reviewer_users      = ["login-do-revisor"]
      prevent_self_review = true
      can_admins_bypass   = false
      deployment_branches = ["main"]
    }
  }
}
```
