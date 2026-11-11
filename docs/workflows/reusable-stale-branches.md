# Workflow Reutilizável — Remoção de Branches Obsoletas

## O que faz

Remove automaticamente branches que não estão mais em uso, com base no estado
do PR associado e na data do último commit.

## Regras de remoção

|Situação|Ação|
|---|---|
|PR associado aberto (no próprio repositório)|Nunca remove|
|PR associado mergeado|Remove imediatamente|
|PR fechado sem merge e sem commits há mais de `days-before-delete` dias|Remove|
|Sem PR e sem commits há mais de `days-before-delete` dias|Remove|
|Branch padrão, protegida no GitHub ou listada em `protected-branches`|Nunca remove|

PRs abertos são verificados primeiro, e PRs vindos de forks com o mesmo nome de
branch não são considerados.

## Inputs

|Input|Tipo|Padrão|Descrição|
|---|---|---|---|
|`days-before-delete`|number|60|Dias sem commits para considerar a branch abandonada|
|`protected-branches`|string|`main,dev`|Branches que nunca são removidas|
|`dry-run`|boolean|true|Apenas lista o que seria removido, sem remover|

## Resumo da execução

O resumo informa o valor de `dry-run` e lista cada branch avaliada com motivo,
PR associado, SHA do último commit e o resultado:

|Resultado|Significado|
|---|---|
|seria removida|Candidata encontrada em execução com `dry-run: true`|
|removida|Branch excluída com sucesso|
|preservada após revalidação|O SHA mudou ou surgiu PR aberto antes da exclusão|
|falhou|Erro ao consultar ou excluir a branch (o job termina com erro)|

Se a listagem de branches falhar, o job termina com erro e informa isso no resumo.

## Como adicionar ao seu repositório

Crie o arquivo `.github/workflows/stale-branches.yml`. As `permissions` são
obrigatórias: o reusable não consegue elevar o acesso recebido do caller.

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
    permissions:
      contents: write
      pull-requests: read
    uses: IFPBEsp/APAE-INFRA/.github/workflows/stale-branches-reusable.yml@dev
    with:
      protected-branches: "main,dev"
      dry-run: ${{ inputs.dry-run != false }}
```

> Para o `APAE-gestao-escolar`, use `protected-branches: "main,dev,dev-database"`.

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
