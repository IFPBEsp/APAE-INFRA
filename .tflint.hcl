# Configuração do TFLint usada pelo workflow terraform-validate.yml.
# Para rodar localmente: tflint --init && tflint --recursive

config {
  # Também analisa os módulos locais chamados pelos ambientes.
  call_module_type = "local"
}

# Regras gerais da linguagem Terraform (variáveis sem uso, versões
# não fixadas, sintaxe antiga etc.).
plugin "terraform" {
  enabled = true
  version = "0.15.0"
  source  = "github.com/terraform-linters/tflint-ruleset-terraform"

  preset = "recommended"
}

