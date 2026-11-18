terraform {
  cloud {
    organization = "ifpb-esp-apae"

    workspaces {
      name = "apae-infra-github"
    }
  }
}