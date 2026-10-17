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

# Plugins de provider: adicione aqui só quando o provider passar a ser usado
# em terraform/. Exemplo para o provider do GitHub (issue #88), se existir
# plugin para ele na época:
#
# plugin "<provider>" {
#   enabled = true
#   version = "x.y.z"
#   source  = "github.com/terraform-linters/tflint-ruleset-<provider>"
# }
