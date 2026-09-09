terraform {
  required_version = ">= 1.0"
}

variable "message" {
  type    = string
  default = "APAE"
}

output "message" {
  value = var.does_not_exist
}
