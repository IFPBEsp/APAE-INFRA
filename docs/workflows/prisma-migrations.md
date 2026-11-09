# Workflow reutilizável de validação de migrations do Prisma

## Objetivo

O workflow `.github/workflows/reusable-prisma-migration-check.yml` centraliza a validação das migrations do Prisma em um PostgreSQL descartável.

A lógica de validação fica no `APAE-INFRA`, enquanto cada repositório de aplicação continua responsável pelo próprio `schema.prisma` e pelo diretório `prisma/migrations`.

O workflow é executado em Pull Requests e verifica se as migrations existentes permanecem imutáveis, se o schema é válido, se as migrations são aplicáveis em um banco limpo e se não existe diferença entre o schema e as migrations.

## Localização

O workflow está localizado em:

```text
.github/workflows/reusable-prisma-migration-check.yml
```

Ele pode ser chamado por outros workflows através de:

```yaml
on:
  workflow_call:
```

## O que o workflow valida

O componente realiza as seguintes validações:

- Impede a modificação ou remoção de migrations já existentes na branch base;
- Valida a sintaxe do schema com `prisma validate`;
- Aplica todas as migrations em um banco PostgreSQL vazio com `prisma migrate deploy`;
- Compara as migrations com o schema usando um banco shadow e `prisma migrate diff --exit-code`;
- Falha quando existir alteração no schema sem a migration correspondente.

## Inputs

Todos os inputs são opcionais e devem ser informados através da chave `with` na chamada do job.

| Nome | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- |
| `working-directory` | Não | `.` | Diretório do repositório que contém o `package.json` da aplicação. A instalação das dependências e os comandos do Prisma são executados nesse diretório. |
| `schema-path` | Não | `prisma/schema.prisma` | Caminho do arquivo de schema do Prisma, relativo ao `working-directory`. O diretório de migrations é derivado como `migrations` ao lado do schema. |
| `postgres-version` | Não | `16` | Versão da imagem do PostgreSQL usada no service container e nos comandos administrativos. |
| `package-manager` | Não | `pnpm` | Gerenciador de pacotes usado na instalação das dependências. Valores aceitos: `pnpm` e `npm`. |
| `node-version` | Não | `20` | Versão do Node.js usada no setup do job. |
| `pnpm-version` | Não | `9` | Versão do pnpm CLI usada no setup do job. |

### Diretório de migrations

O diretório de migrations não possui um input próprio. Ele é calculado a partir do `schema-path`:

```text
schema-path: prisma/schema.prisma
migrations:  prisma/migrations
```

Em um monorepo, informe o `working-directory` e mantenha o `schema-path` relativo a ele:

```yaml
with:
  working-directory: "apps/site"
  schema-path: "prisma/schema.prisma"
```

Nesse exemplo, as migrations ficam em `apps/site/prisma/migrations`.

## Exemplo de uso

O repositório consumidor deve criar um caller que dispare a validação em Pull Requests que alterem o schema ou as migrations. No `apae-site-comemorativo`, o arquivo pode ser `.github/workflows/prisma-migrations.yml`:

```yaml
name: Prisma Migrations Check

on:
  pull_request:
    paths:
      - "prisma/**"
      - ".github/workflows/prisma-migrations.yml"

permissions:
  contents: read

jobs:
  prisma:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-prisma-migration-check.yml@<commit-sha>
    with:
      working-directory: "."
      schema-path: "prisma/schema.prisma"
      postgres-version: "16"
      package-manager: "pnpm"
```

A referência `<commit-sha>` deve ser substituída pelo SHA completo do commit aprovado no APAE-INFRA. Evite referências mutáveis como `@dev` ou `@main`.

## Permissões

O workflow utiliza apenas a permissão mínima de leitura do conteúdo do repositório:

```yaml
permissions:
  contents: read
```

Não são necessários secrets adicionais. O PostgreSQL utilizado durante o job é temporário e descartável.

## Imutabilidade das migrations

O workflow compara o Pull Request com `origin/${{ github.base_ref }}` usando `git diff --name-status` no diretório de migrations. A execução falha quando o diff contém qualquer arquivo com status `M` (Modified) ou `D` (Deleted).

Novas migrations com status `A` (Added) são permitidas. O diff é executado sem detecção de renomeação, portanto uma migration renomeada aparece como uma remoção seguida de uma adição e também é bloqueada.

Exemplo permitido:

```text
Branch base: 20240101000000_init
Pull Request: 20240101000000_init, 20240202000000_add_campaign
```

Alterar ou remover `20240101000000_init` faz a validação falhar.

## Validação do schema e aplicação das migrations

O workflow executa `prisma validate` para verificar a sintaxe e a consistência do schema. Em seguida, executa `prisma migrate deploy` em um banco PostgreSQL vazio, garantindo que todas as migrations possam ser aplicadas na ordem correta.

A conexão com o banco principal é fornecida pela variável `DATABASE_URL`, apontando para o banco `app` do service container.

## Banco shadow e detecção de drift

Depois da aplicação das migrations, o workflow cria o banco `app_shadow` e executa:

```bash
prisma migrate diff \
  --from-migrations <diretório-de-migrations> \
  --to-schema-datamodel <schema-path> \
  --shadow-database-url <shadow-database-url> \
  --exit-code
```

Quando o schema possui alterações que não estão representadas por uma migration, o comando retorna um código de saída diferente de zero e o job falha. Isso evita que o banco de produção divergente do schema seja publicado sem a migration correspondente.

## Requisitos do repositório consumidor

O repositório consumidor deve possuir:

- `package.json` com o Prisma instalado como dependência do projeto;
- `pnpm-lock.yaml` quando usar `pnpm` ou `package-lock.json` quando usar `npm`;
- `schema.prisma` e o diretório de migrations no caminho configurado;
- workflow caller executado em eventos de `pull_request`.

O workflow utiliza Node.js 20 e o gerenciador informado no input `package-manager`. A instalação usa `pnpm install --frozen-lockfile` ou `npm ci`, conforme o gerenciador selecionado.

## Referências relacionadas

- Workflow: [reusable-prisma-migration-check.yml](../../.github/workflows/reusable-prisma-migration-check.yml)
- Documentação do Prisma Migrate: [Prisma Migrate](https://www.prisma.io/docs/orm/prisma-migrate)
