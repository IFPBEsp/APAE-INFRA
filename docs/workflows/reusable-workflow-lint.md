# Workflow reutilizável de lint e auditoria de segurança do GitHub Actions

## Objetivo

O workflow `.github/workflows/workflow-lint-reusable.yml` analisa os próprios workflows do GitHub Actions nos Pull Requests dos repositórios da APAE. Os workflows publicam imagens, assinam artefatos e alteram manifests, por isso fazem parte da cadeia de entrega e precisam de revisão automática.

Ele executa duas ferramentas:

- **[actionlint](https://github.com/rhysd/actionlint)**: erros de sintaxe, expressões `${{ }}` inválidas, contextos e inputs inexistentes e problemas nos scripts `run` (via [shellcheck](https://www.shellcheck.net/)).
- **[zizmor](https://docs.zizmor.sh/)**: auditoria de segurança. Detecta actions sem SHA fixado, permissões amplas, injeção de expressões em `run`, uso inseguro de `pull_request_target`, credenciais persistidas pelo `actions/checkout`, entre outros.

---

## Inputs

| Input | Tipo | Obrigatório | Padrão | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `run-actionlint` | `boolean` | Não | `true` | Executa o actionlint. |
| `run-zizmor` | `boolean` | Não | `true` | Executa o zizmor. |
| `zizmor-min-severity` | `string` | Não | `medium` | Severidade mínima do zizmor que bloqueia o PR: `informational`, `low`, `medium` ou `high`. |

---

## Versões fixadas

As ferramentas são baixadas dos releases oficiais e verificadas por SHA-256 antes da execução. Nenhuma action de terceiros é usada para instalá-las.

| Ferramenta | Versão |
| :--- | :--- |
| actionlint | `1.7.12` |
| shellcheck | `0.11.0` |
| zizmor | `1.31.1` |

Para atualizar, altere as variáveis `*_VERSION` e `*_SHA256` no workflow e valide em um PR no APAE-INFRA. As actions (`actions/checkout` e `github/codeql-action/upload-sarif`) estão fixadas por SHA e são atualizadas pelo Renovate.

---

## Saídas e bloqueio

1. **Anotações no PR**: os findings do actionlint e os do zizmor com severidade igual ou superior a `zizmor-min-severity` aparecem como anotações na aba *Files changed*.
2. **Aba Security**: o zizmor gera um relatório SARIF com **todas** as severidades, publicado em **Security > Code scanning** na categoria `zizmor`. Os findings abaixo do limite ficam visíveis ali sem bloquear o PR.
3. **Bloqueio**:
   - qualquer erro do actionlint falha o job `actionlint`;
   - qualquer finding do zizmor com severidade igual ou superior a `zizmor-min-severity` falha o job `zizmor`;
   - qualquer workflow ou action com erro de sintaxe ou de schema falha o job `zizmor` (`--strict-collection`). Isso cobre as composite actions em `.github/actions/`, que o actionlint não valida. Nesse caso o SARIF não é publicado.

> [!NOTE]
> Em PRs abertos a partir de forks, o token não tem `security-events: write`. Nesse caso a publicação do SARIF é pulada, mas as anotações e o bloqueio continuam funcionando.

---

## Como aderir

### 1. Criar o workflow no repositório

Crie `.github/workflows/workflow-lint.yml`:

```yaml
name: GitHub Actions Workflow Lint

on:
  pull_request:
    paths:
      - ".github/workflows/**"
      - ".github/actions/**"
      - ".github/actionlint.yaml"
      - ".github/zizmor.yml"
  push:
    branches:
      - dev
      - main
    paths:
      - ".github/workflows/**"
      - ".github/actions/**"
      - ".github/actionlint.yaml"
      - ".github/zizmor.yml"

permissions:
  contents: read

jobs:
  workflow-lint:
    name: Workflow Lint
    uses: IFPBEsp/APAE-INFRA/.github/workflows/workflow-lint-reusable.yml@<commit-sha>
    permissions:
      contents: read
      actions: read
      security-events: write
    with:
      zizmor-min-severity: "medium"
```

O gatilho `push` nas branches principais mantém uma análise de referência na aba Security, para que o GitHub mostre nos PRs apenas os alertas novos.

> [!IMPORTANT]
> Substitua `<commit-sha>` pelo SHA completo do commit aprovado no `APAE-INFRA`. Não use referências mutáveis como `@main` ou `@dev`.

### 2. Corrigir os findings existentes

Antes de tornar o check obrigatório, rode o workflow em um PR e corrija os findings. As correções mais comuns:

| Finding | Correção |
| :--- | :--- |
| `unpinned-uses` | Fixar a action por SHA completo, com a tag em comentário: `uses: actions/checkout@<sha> # v4`. |
| `artipacked` | Adicionar `persist-credentials: false` ao `actions/checkout`, salvo se o job precisar fazer `git push`. |
| `template-injection` | Mover a expressão para `env:` e usar a variável no script: `env: { NOME: ${{ inputs.nome }} }` e `echo "$NOME"`. |
| `excessive-permissions` | Declarar `permissions:` no workflow ou no job com o mínimo necessário. |
| `dangerous-triggers` | Evitar `pull_request_target`; se for indispensável, nunca fazer checkout do código do PR nesse contexto. |

### 3. Exceções justificadas

Quando um finding for um falso positivo, registre a exceção com justificativa:

- **actionlint**: `.github/actionlint.yaml`, com expressões regulares em `paths.<glob>.ignore`.
- **zizmor**: comentário `# zizmor: ignore[<regra>]` na linha do finding ou entrada em `.github/zizmor.yml`. Comentários dentro de um bloco `run: |` fazem parte do script e **não** são reconhecidos; nesses casos use o arquivo de configuração.

Exemplo de `.github/zizmor.yml`:

```yaml
rules:
  github-env:
    ignore:
      # Justificativa da exceção.
      - action.yml:11
```

As exceções são versionadas e passam pelo Code Review do PR. Veja as do próprio APAE-INFRA em [`.github/actionlint.yaml`](../../.github/actionlint.yaml) e [`.github/zizmor.yml`](../../.github/zizmor.yml).

### Aviso sobre filtros `paths` e checks obrigatórios

> **Não torne obrigatório um check que pode deixar de ser criado por causa dos filtros de caminho.** Se o workflow for ignorado por `paths`, o check obrigatório fica pendente e bloqueia o merge. Para torná-lo obrigatório, remova os filtros ou use uma estratégia que gere resultado em todos os PRs.

---

## Situação de adesão

| Repositório | Situação |
| :--- | :--- |
| `APAE-INFRA` | Aplicado em [`.github/workflows/workflow-lint.yml`](../../.github/workflows/workflow-lint.yml), sem findings bloqueantes. |
| `APAE` | Pendente. Workflows usam actions sem SHA fixado. |
| `APAE-gestao-escolar` | Pendente. Workflows usam actions sem SHA fixado. |
| `APAE-atendimento` | Pendente. |
| `apae-site-comemorativo` | Não se aplica (sem workflows). |

---

## Permissões necessárias

```yaml
permissions:
  contents: read          # Leitura dos workflows
  actions: read           # Exigido pelo upload-sarif em repositórios privados
  security-events: write  # Publicação do SARIF na aba Security
```

O workflow reutilizável declara `permissions: {}` no nível superior e concede a cada job apenas o que ele usa: o job `actionlint` recebe somente `contents: read`.
