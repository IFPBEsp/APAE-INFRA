terraform {
  required_version = "~> 1.13.0"

  cloud {
    organization = "ifpb-esp-apae"

    workspaces {
      name = "apae-infra-dev"
    }
  }
}