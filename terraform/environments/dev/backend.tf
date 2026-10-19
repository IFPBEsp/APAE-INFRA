terraform {
  required_version = "~> 1.13.0"

  cloud {
    organization = "ifpbesp-apae"

    workspaces {
      name = "apae-infra-dev"
    }
  }
}