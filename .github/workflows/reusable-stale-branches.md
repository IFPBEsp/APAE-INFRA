# Workflow Reutilizável — Remoção de Branches Obsoletas

## O que faz

Remove automaticamente branches que não estão mais em uso, com base no estado
do PR associado e na data do último commit.

## Regras de remoção

|Situação|Ação|
|---|---|
|PR associado mergeado|Remove imediatamente|
|PR fechado sem merge e sem commits há mais de `days-before-delete` dias|Remove|
|Sem PR e sem commits há mais de `days-before-delete` dias|Remove|
|PR associado aberto|Nunca remove|
|Branch padrão, protegida no GitHub ou listada em `protected-branches`|Nunca remove|

## Inputs

|Input|Tipo|Padrão|Descrição|
|---|---|---|---|
|`days-before-delete`|number|60|Dias sem commits para considerar a branch abandonada|
|`protected-branches`|string|`main,dev`|Branches que nunca são removidas|
|`dry-run`|boolean|true|Apenas lista o que seria removido, sem remover|

## Como adicionar ao seu repositório

Crie o arquivo `.github/workflows/stale-branches.yml`:

```yaml
name: Remove Stale Branches

on:
  schedule:
    - cron: "0 3 * * 1"
  workflow_dispatch:
    inputs:
      dry-run:
        description: "Apenas listar, sem remover"
        type: boolean
        default: true

jobs:
  call-stale-branches:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/stale-branches-reusable.yml@dev
    with:
      protected-branches: "main,dev"
      dry-run: ${{ inputs.dry-run != false }}
```

> Para o `APAE-gestao-escolar`, adicionar `dev-database` em `protected-branches`.

## Como recuperar uma branch removida

Com o SHA listado no resumo da execução:

```bash
git push origin <sha>:refs/heads/<nome-da-branch>
```

Branches com PR associado também podem ser restauradas pelo botão
**Restore branch** na página do PR no GitHub.

## Implantação recomendada

1. Mergear o caller na branch padrão do repositório
2. Executar manualmente com `dry-run: true` e conferir a lista gerada
3. Após conferência do time, executar com `dry-run: false`
4. Ativar **Automatically delete head branches** em Settings → General

