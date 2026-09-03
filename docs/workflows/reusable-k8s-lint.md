# Workflow reutilizável de lint de manifests Kubernetes

## Objetivo

O workflow `.github/workflows/k8s-lint-reusable.yml` centraliza a validação de manifests Kubernetes utilizados pelos repositórios APAE.

A validação é executada em três camadas:

1. `yamllint` para sintaxe e estrutura YAML;
2. `kubeconform` para validação de schema Kubernetes e CRDs;
3. `kube-linter` para boas práticas e segurança.

O workflow não realiza deploy e não requer acesso ao cluster.

---

## Inputs

### `manifests-path`

Diretório que contém os manifests Kubernetes.

Valor padrão:

```text
kubernetes
```

Exemplo:

```yaml
with:
  manifests-path: "kubernetes"
```

### `kubernetes-version`

Versão Kubernetes utilizada pelo `kubeconform` para validação de schema.

Esse valor é opcional e deve refletir, quando definido, a versão Kubernetes correspondente ao K3s do ambiente alvo.

Exemplo:

```yaml
with:
  kubernetes-version: "1.xx.x"
```

Enquanto a versão alvo não estiver definida, o input pode permanecer vazio.

### `ignore-missing-schemas`

Controla o comportamento quando um recurso customizado não possui schema disponível.

Valor padrão:

```text
false
```

O comportamento padrão é intencionalmente estrito para evitar que CRDs sem schema sejam ignorados silenciosamente.

---

## Uso no APAE-INFRA

O workflow local:

```text
.github/workflows/k8s-lint.yml
```

chama o reusable workflow para:

```text
kubernetes/
argocd/
```

A execução ocorre em Pull Requests que alterem esses diretórios.

---

## Reutilização em repositórios de aplicação

Caso um repositório de aplicação passe a possuir manifests próprios, ele pode reutilizar o workflow central.

Exemplo:

```yaml
name: Kubernetes Manifests Lint

on:
  pull_request:
    paths:
      - "kubernetes/**"

permissions:
  contents: read

jobs:
  k8s-lint:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/k8s-lint-reusable.yml@<commit-sha>
    with:
      manifests-path: "kubernetes"
```
A referência <commit-sha> deve ser substituída pelo SHA completo do commit do PR aprovado no APAE-INFRA.

Evitar referências mutáveis como:

```text
@main
@dev
@v1
```

---

## Repositórios previstos

O workflow poderá ser reutilizado futuramente por:

- `IFPBEsp/APAE`
- `IFPBEsp/APAE-gestao-escolar`
- `IFPBEsp/APAE-atendimento`
- `IFPBEsp/apae-site-comemorativo`

Nenhum desses repositórios precisa adotar o workflow enquanto não possuir manifests Kubernetes próprios.

---

## Ferramentas utilizadas

```text
yamllint
kubeconform
kube-linter
```

Responsabilidades:

```text
yamllint     → sintaxe YAML
kubeconform  → schema Kubernetes e CRDs
kube-linter  → boas práticas e segurança
```
