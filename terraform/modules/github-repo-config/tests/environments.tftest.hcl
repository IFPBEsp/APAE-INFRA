mock_provider "github" {
  mock_data "github_repository" {
    defaults = { name = "APAE-INFRA", node_id = "R_x" }
  }
  mock_data "github_user" {
    defaults = { id = "12345" }
  }
}

variables {
  repository_name = "APAE-INFRA"
  environment_protection = {
    production = {
      reviewer_users      = ["henriquetomazzz", "LuizArtur29"]
      deployment_branches = ["main"]
    }
  }
}

run "production_protegido" {
  command = plan
  override_data {
    target = data.github_user.environment_reviewers["LuizArtur29"]
    values = { id = "67890" }
  }
  assert {
    condition     = github_repository_environment.environments["production"].prevent_self_review == true
    error_message = "prevent_self_review"
  }
  assert {
    condition     = github_repository_environment.environments["production"].can_admins_bypass == false
    error_message = "bypass"
  }
  assert {
    condition     = length(github_repository_environment.environments["production"].reviewers[0].users) == 2
    error_message = "reviewers"
  }
  assert {
    condition     = github_repository_environment.environments["production"].deployment_branch_policy[0].custom_branch_policies == true
    error_message = "branch policy"
  }
  assert {
    condition     = keys(github_repository_environment_deployment_policy.branches) == ["production:main"]
    error_message = "deployment policy"
  }
  assert {
    condition     = length(github_repository_environment.environments["staging"].reviewers) == 0 && length(github_repository_environment.environments["staging"].deployment_branch_policy) == 0
    error_message = "staging sem regras"
  }
}

run "rejeita_environment_desconhecido" {
  command = plan
  variables {
    environment_protection = { qa = { reviewer_users = ["x"] } }
  }
  expect_failures = [var.environment_protection]
}

run "rejeita_sem_revisor" {
  command = plan
  variables {
    environment_protection = { production = { deployment_branches = ["main"] } }
  }
  expect_failures = [var.environment_protection]
}
