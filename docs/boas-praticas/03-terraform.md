# 3. Terraform

[← Voltar ao índice](README.md)

O Terraform deve ser utilizado de forma declarativa e reproduzível.

A estrutura definida no repositório deve ser respeitada:

```text
terraform/
├── modules/
└── environments/
    ├── dev/
    ├── hml/
    └── prod/
```

Os módulos reutilizáveis devem permanecer em `terraform/modules/`, enquanto as configurações específicas de cada ambiente devem permanecer em `terraform/environments/`.

---

## 3.1 Nomenclatura

Os recursos devem utilizar nomes previsíveis e consistentes.

Sempre que aplicável, utilizar informações como:

```text
<projeto>-<ambiente>-<recurso>
```

Exemplo:

```text
apae-prod-network
apae-dev-storage
apae-hml-database
```

Evitar nomes genéricos como:

```text
server1
test
resource-new
```

---

## 3.2 Variables e Outputs

Valores que podem variar entre ambientes não devem ser fixados diretamente nos recursos.

Preferir:

```hcl
variable "environment" {
  type = string
}
```

em vez de valores duplicados em diversos arquivos.

Outputs devem ser utilizados para expor somente informações que serão consumidas por outros módulos, processos ou recursos.

Informações sensíveis não devem ser expostas desnecessariamente por outputs.

---

## 3.3 Providers e dependências

As versões dos providers utilizados pelo Terraform devem possuir restrições explícitas.

Exemplo:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

Isso evita que uma atualização inesperada de provider altere o comportamento da infraestrutura ou quebre pipelines existentes.

Quando gerado, o arquivo:

```text
.terraform.lock.hcl
```

deve ser mantido versionado no repositório.

Esse arquivo registra as versões efetivamente selecionadas dos providers e contribui para builds mais reproduzíveis.

---

## 3.4 State

O state do Terraform contém informações importantes sobre a infraestrutura e não deve ser versionado diretamente no Git.

Para ambientes compartilhados, deve ser utilizado um backend remoto adequado, permitindo centralização e controle do state.

Arquivos como:

```text
terraform.tfstate
terraform.tfstate.*
```

não devem ser commitados.

O state também não deve ser editado manualmente.

---

## 3.5 Locking do state

Quando o backend utilizado oferecer suporte, deve ser utilizado mecanismo de **locking** ou proteção equivalente contra alterações concorrentes.

O objetivo é impedir que duas execuções do Terraform tentem modificar o mesmo state simultaneamente.

Exemplo de situação que deve ser evitada:

```text
terraform apply A
        +
terraform apply B
        ↓
mesmo state
```

Alterações concorrentes podem causar inconsistências ou corrupção do estado da infraestrutura.

---

## 3.6 Validação

Antes de abrir ou aprovar um Pull Request contendo Terraform, executar:

```bash
terraform fmt -check
terraform validate
```

Sempre que possível, também deve ser gerado:

```bash
terraform plan
```

O resultado do `plan` deve ser revisado antes de qualquer `apply`.

O `terraform apply` não deve ser executado sem que as alterações planejadas sejam conhecidas e revisadas.

---

## 3.7 Terraform Plan

O `terraform plan` deve ser tratado como uma etapa importante do processo de revisão.

Durante a análise, verificar principalmente:

* Recursos criados;
* Recursos alterados;
* Recursos removidos;
* Recursos substituídos;
* Mudanças inesperadas.

Alterações destrutivas devem receber atenção especial.

---

## 3.8 Terraform Apply

Em ambientes compartilhados e principalmente em produção, deve-se evitar executar:

```bash
terraform apply
```

diretamente a partir da máquina pessoal de um contribuidor quando existir uma pipeline ou processo automatizado responsável pelo provisionamento.

O fluxo recomendado é:

```text
Alteração Terraform
        ↓
Pull Request
        ↓
terraform plan
        ↓
Revisão
        ↓
Merge
        ↓
Pipeline autorizada
        ↓
terraform apply
```

Essa abordagem melhora:

* Rastreabilidade;
* Controle de acesso;
* Auditoria;
* Reprodutibilidade.

---
