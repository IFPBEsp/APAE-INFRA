terraform {
  required_version = ">= 1.0"
}

variable "message" {
  type    = string
  default = "APAE"
}

output "message" {
  value = var.message
}
