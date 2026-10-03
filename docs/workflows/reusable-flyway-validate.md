# Workflow reutilizável de validação de migrations Flyway

## Objetivo

O workflow `.github/workflows/flyway-validate-reusable.yml` centraliza a validação das migrations do Flyway utilizadas pelos repositórios da APAE.

A lógica de validação fica no `APAE-INFRA`, enquanto cada repositório de aplicação continua responsável pelas próprias migrations.

A validação utiliza a CLI do Flyway em container e um PostgreSQL descartável durante o job. O workflow não depende do Maven e não precisa iniciar a aplicação.

## Localização

O workflow está localizado em:

```text
.github/workflows/flyway-validate-reusable.yml
```

Ele pode ser chamado por outros workflows através de:

```yaml
on:
  workflow_call:
```

## O que o workflow valida

O componente realiza as seguintes validações:

- Imutabilidade das migrations existentes;
- Padrão de nomes e versões;
- Versões duplicadas;
- Migrations novas com versão menor ou igual à versão existente na branch base;
- Execução das migrations em um banco PostgreSQL vazio;
- Validação com `flyway validate`;
- Caminho de atualização da branch base para o Pull Request;
- Operações potencialmente destrutivas nas migrations novas;
- Resumo da execução no `GITHUB_STEP_SUMMARY`.

## Inputs

### `migrations-path`

Diretório que contém as migrations principais da aplicação.

- **Tipo:** `string`
- **Obrigatório:** sim

Exemplo:

```yaml
with:
  migrations-path: "apps/api/src/main/resources/db/migration"
```

### `extra-migrations-paths`

Arquivos ou diretórios SQL executados antes das migrations principais. Cada entrada deve ser informada em uma linha. Use esse input quando as migrations dependerem de estruturas que não são criadas pelas migrations principais.

- **Tipo:** `string`
- **Padrão:** vazio

O workflow aceita um arquivo `.sql` ou um diretório contendo arquivos `.sql`. Quando um diretório é informado, os arquivos SQL são executados em ordem alfabética.

Exemplo:

```yaml
with:
  extra-migrations-paths: |
    .scripts/db/apae-geral-contract.sql
```

### `schemas`

Schema ou schemas gerenciados pelo Flyway.

- **Tipo:** `string`
- **Padrão:** `public`

Exemplo:

```yaml
with:
  schemas: "apae_geral"
```

### `postgres-version`

Versão do PostgreSQL utilizada durante a validação. A versão deve corresponder à utilizada pela aplicação.

- **Tipo:** `string`
- **Padrão:** `15`

Exemplo:

```yaml
with:
  postgres-version: "16"
```

### `flyway-version`

Versão da imagem da CLI do Flyway utilizada durante a validação. Quando o projeto utilizar uma versão diferente do padrão, informe-a explicitamente.

- **Tipo:** `string`
- **Padrão:** `11.7.2`

Exemplo:

```yaml
with:
  flyway-version: "11.7.2"
```

Exemplo com outra versão:

```yaml
with:
  flyway-version: "9.22.3"
```

### `check-upgrade-path`

Controla a validação do caminho de atualização.

- **Tipo:** `boolean`
- **Padrão:** `true`

Exemplo:

```yaml
with:
  check-upgrade-path: true
```

Quando habilitado, o workflow simula a aplicação das migrations da branch base, seguida das migrations do Pull Request e de `flyway validate`.

### `fail-on-destructive`

Controla se operações potencialmente destrutivas devem bloquear o job.

- **Tipo:** `boolean`
- **Padrão:** `false`

Exemplo:

```yaml
with:
  fail-on-destructive: true
```

Quando `false`, uma operação destrutiva gera warning e aparece no resumo. Quando `true`, o job exige o label `migration-destrutiva-aprovada`; sem esse label, a execução falha.

## Exemplo de uso

Cada repositório de aplicação pode criar um pequeno caller. A referência `<commit-sha>` deve ser substituída pelo SHA completo do commit aprovado no APAE-INFRA. Evite referências mutáveis como `@dev` ou `@main`.

```yaml
name: Flyway Migrations Validate

on:
  pull_request:
    paths:
      - "apps/api/src/main/resources/db/migration/**"
      - ".github/workflows/flyway-validate.yml"

permissions:
  contents: read
  pull-requests: read

jobs:
  flyway:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/flyway-validate-reusable.yml@<commit-sha>
    with:
      migrations-path: "apps/api/src/main/resources/db/migration"
      schemas: "apae_geral"
      postgres-version: "15"
      flyway-version: "11.7.2"
      check-upgrade-path: true
      fail-on-destructive: false
```

### Caller com dependência externa

Quando as migrations dependem de outro schema, o caller pode fornecer um SQL preparatório. Esse contrato SQL é executado antes das migrations principais.

```yaml
jobs:
  flyway:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/flyway-validate-reusable.yml@<commit-sha>
    with:
      migrations-path: "backend/atendimento/src/main/resources/db/migration"
      extra-migrations-paths: |
        .scripts/db/apae-geral-contract.sql
      schemas: "atendimento"
      postgres-version: "16"
      flyway-version: "11.7.2"
```

## Permissões

O workflow utiliza as seguintes permissões:

```yaml
permissions:
  contents: read
  pull-requests: read
```

Não são necessários secrets adicionais para a validação. O PostgreSQL utilizado durante o job é temporário e descartável.

## Imutabilidade das migrations

O workflow compara a branch base com a branch do Pull Request. Somente migrations novas podem ser adicionadas. Uma migration existente não deve ser:

- Modificada;
- Renomeada;
- Removida.

Neste exemplo, a adição de `V4` é permitida:

```text
Branch base: V1, V2, V3
Pull Request: V1, V2, V3, V4
```

Alterar o conteúdo de `V3` faz a validação falhar.

## Nomenclatura das migrations

As migrations versionadas devem seguir o padrão `V<versão>__<descrição>.sql`.

Exemplo:

```text
V11__add_ativo_for_users.sql
```

Também são aceitas migrations repeatable no padrão `R__<descrição>.sql`.

Exemplo:

```text
R__refresh_views.sql
```

## Versionamento

Uma migration nova deve possuir uma versão superior à maior versão existente na branch base.

Exemplo:

```text
Branch base: V1, V2, V3
Nova migration: V4
```

Uma migration nova com versão menor ou igual à última versão existente faz o job falhar.

## Operações destrutivas

O workflow procura operações potencialmente destrutivas nas migrations novas, incluindo:

- `DROP TABLE`;
- `DROP VIEW`;
- `DROP MATERIALIZED VIEW`;
- `DROP SCHEMA`;
- `DROP TYPE`;
- `DROP SEQUENCE`;
- `DROP INDEX`;
- `TRUNCATE`;
- `ALTER TABLE ... DROP COLUMN`;
- `DELETE` sem `WHERE`;
- `UPDATE` sem `WHERE`.

A detecção utiliza análise textual de SQL. Ela serve como camada de proteção e visibilidade e não substitui a revisão manual da alteração.

## Resumo da execução

Ao final, o workflow registra informações no `GITHUB_STEP_SUMMARY`, incluindo:

- Caminho das migrations;
- Versão do PostgreSQL;
- Versão do Flyway;
- Schemas utilizados;
- Quantidade de migrations novas;
- Versão final;
- Status do upgrade path;
- Configuração de operações destrutivas;
- Migrations novas detectadas.

## Arquitetura de uso

As migrations permanecem nos repositórios das aplicações, enquanto o APAE-INFRA fornece a lógica compartilhada de validação.

```text
Repositório da aplicação
        ↓
      caller
        ↓
    APAE-INFRA
        ↓
flyway-validate-reusable.yml
        ↓
 PostgreSQL + Flyway
```

As responsabilidades ficam distribuídas da seguinte forma:

- **Aplicação:** código e migrations;
- **APAE-INFRA:** workflows reutilizáveis e infraestrutura compartilhada.

## Referências relacionadas

- Boas práticas para alterações destrutivas: [09-alteracoes-destrutivas.md](../boas-praticas/09-alteracoes-destrutivas.md)
- Workflow: [flyway-validate-reusable.yml](../../.github/workflows/flyway-validate-reusable.yml)
