# Análise estática e de segurança do Terraform

Este documento explica os dois checks de análise do código Terraform nos Pull Requests (issue #85) e como tratar exceções justificadas.

Os checks rodam no workflow [`terraform-validate.yml`](../../.github/workflows/terraform-validate.yml), junto com `fmt`, `validate` e `plan`.

## Checks

| Check | Ferramenta | O que procura | Quando bloqueia o PR |
| --- | --- | --- | --- |
| `TFLint` | [TFLint](https://github.com/terraform-linters/tflint) | Más práticas da linguagem e dos providers (variáveis sem uso, versões não fixadas, valores inválidos) | Qualquer problema encontrado |
| `Trivy config` | [Trivy](https://trivy.dev/) em modo `config` | Configurações inseguras (ex.: porta aberta para a internet, disco sem criptografia) | Finding de severidade `HIGH` ou `CRITICAL` |

O workflow roda em todo PR para `dev` e `main`, mas os checks só executam quando o PR altera `terraform/**`, `.tflint.hcl`, `.trivyignore` ou o próprio workflow. Nos demais PRs, os jobs aparecem como **Skipped**, e o GitHub conta job pulado como sucesso. O resultado aparece no resumo do workflow (aba **Summary** da execução).

## Arquivos de configuração

| Arquivo | Para que serve |
| --- | --- |
| [`.tflint.hcl`](../../.tflint.hcl) | Regras e plugins do TFLint, com versões fixas |
| [`.trivyignore`](../../.trivyignore) | Lista de exceções do Trivy |

### Adicionar o plugin de um provider

O TFLint só ganha o plugin de um provider quando ele passa a ser usado em `terraform/`. Para adicionar, inclua um bloco `plugin` no `.tflint.hcl` com `source` e `version` fixa, no mesmo PR que começa a usar o provider.

## Rodar localmente

Com o TFLint e o Trivy instalados:

```bash
tflint --init
tflint --recursive --config "$(pwd)/.tflint.hcl" --chdir terraform

trivy config --severity HIGH,CRITICAL --ignorefile .trivyignore terraform
```

## Tratar exceções

A primeira opção é sempre corrigir o código. Só abra uma exceção quando o finding não se aplica ao caso ou o risco foi aceito de propósito.

Toda exceção precisa de:

- um comentário com o **motivo**, em uma linha separada, acima da linha que ignora a regra;
- a **issue ou PR** onde foi discutida;
- a aprovação de pelo menos uma pessoa do time de infraestrutura na revisão do PR.

### Exceção do Trivy

Prefira ignorar no próprio recurso, para a exceção ficar ao lado do código:

```hcl
# Bucket público de propósito, só serve arquivos estáticos (issue #XX)
# trivy:ignore:AVD-AWS-0086
resource "aws_s3_bucket_public_access_block" "site" {
  # ...
}
```

Quando não for possível comentar no recurso, adicione o ID da regra ao [`.trivyignore`](../../.trivyignore), com o motivo logo acima:

```text
# Motivo: ... (issue #XX)
AVD-AWS-0086
```

Exceções no `.trivyignore` valem para todo o repositório, por isso use esse arquivo só quando a exceção realmente for geral.

### Exceção do TFLint

Ignore a regra na linha ou no bloco, com o motivo em um comentário separado:

```hcl
# Usada só pelo módulo X (issue #XX)
# tflint-ignore: terraform_unused_declarations
variable "exemplo" {
  type = string
}
```

Não escreva o motivo na mesma linha, depois do nome da regra (por exemplo, `# tflint-ignore: regra - motivo`). O TFLint lê esse texto como parte do nome da regra, a exceção não é aplicada e o check continua falhando. Se preferir manter tudo na mesma linha, comece um segundo `#` antes do motivo: `# tflint-ignore: regra # motivo`.

Para desligar uma regra em todo o repositório, use `rule "nome" { enabled = false }` no `.tflint.hcl`, com um comentário explicando o motivo.

## Tornar os checks obrigatórios

Os jobs `TFLint` e `Trivy config` só bloqueiam o merge se estiverem marcados como **required status checks** nas regras de proteção da branch. Essa configuração é feita por quem administra o repositório (Settings → Branches).

É seguro marcar os dois como obrigatórios porque o workflow não usa o filtro `paths` no gatilho. Em PRs sem mudança em Terraform, o job `Detect Terraform Changes` identifica isso e os demais jobs são pulados, o que o GitHub conta como sucesso. Se o filtro `paths` fosse usado, o workflow não seria criado nesses PRs e os checks obrigatórios ficariam **Pending**, bloqueando o merge. Por isso, **não reintroduza `paths` no gatilho** de `terraform-validate.yml`. Veja a explicação do GitHub em [Troubleshooting required status checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks).

Se for necessário mudar os caminhos que disparam os checks, edite o padrão do job `Detect Terraform Changes`.
