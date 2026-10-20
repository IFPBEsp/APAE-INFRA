# Workflow reutilizável de validação de commits e título de PR

## Objetivo

O workflow `.github/workflows/commitlint-reusable.yml` valida, em cada Pull Request:

1. as mensagens de todos os commits do PR, com [commitlint](https://commitlint.js.org/);
2. o título do PR, no formato `[TIPO] Descrição` definido no [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

Ele roda a mesma validação em qualquer repositório da APAE. O padrão de commit é o da issue #5 e o de título de PR é o da issue #6.

O workflow não escreve nada no repositório e usa apenas as permissões `contents: read` e `pull-requests: read`.

---

## Como funciona

- Valida só os commits do PR, do commit base até o head. Commits de merge são ignorados.
- A configuração padrão do commitlint é o [`commitlint.config.js`](../../commitlint.config.js) da raiz do APAE-INFRA. O workflow baixa esse arquivo na mesma versão do próprio workflow, então fixar o SHA do workflow também fixa a configuração.
- O commitlint é instalado com versão fixa (`@commitlint/cli` e `@commitlint/config-conventional`).
- Se os commits falharem, o título ainda é validado, para que os dois problemas apareçam na mesma execução.
- PRs abertos por bots (como o Renovate) não são validados.
- As actions usadas são fixadas por SHA.

---

## Inputs

| Input | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- |
| `config-file` | Não | configuração compartilhada do APAE-INFRA | Caminho, a partir da raiz do repositório chamador, de uma configuração própria do commitlint |
| `validate-pr-title` | Não | `true` | Habilita a validação do título do PR |
| `pr-title-pattern` | Não | `^\[(FEAT\|FIX\|DOCS\|CHORE\|CI\|REFACTOR\|TEST\|BUILD)\] .+` | Expressão regular (ERE do bash) aplicada ao título do PR |

---

## Como aderir

Crie o arquivo `.github/workflows/commitlint.yml` no repositório:

```yaml
name: Lint Commit Messages

on:
  pull_request:
    types: [opened, edited, synchronize, reopened]

permissions:
  contents: read
  pull-requests: read

jobs:
  commitlint:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/commitlint-reusable.yml@<commit-sha>
```

Substitua `<commit-sha>` pelo SHA completo de um commit do APAE-INFRA. Evite referências mutáveis como `@main`, `@dev` ou `@v1`.

O evento `edited` é necessário para que o título seja validado de novo quando alguém o altera.

### Configuração própria

Se o repositório precisar de regras diferentes, aponte para o arquivo dele:

```yaml
jobs:
  commitlint:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/commitlint-reusable.yml@<commit-sha>
    with:
      config-file: commitlint.config.js
```

A configuração própria precisa estender apenas `@commitlint/config-conventional`, que já vem instalado. Plugins e outros presets não são instalados. O arquivo deve ser CommonJS (`.js` sem `"type": "module"`, ou `.cjs`).

### Outro padrão de título

```yaml
with:
  pr-title-pattern: '^\[(FEAT|FIX|DOCS)\] .+'
```

Para desligar a validação do título:

```yaml
with:
  validate-pr-title: false
```

---

## Uso no APAE-INFRA

O workflow `.github/workflows/commitlint.yml` chama o reutilizável do próprio repositório (`./.github/workflows/commitlint-reusable.yml`) com os valores padrão.

---

## Como corrigir um PR reprovado

### Commit fora do padrão

Se for o último commit:

```bash
git commit --amend -m "tipo: descrição corrigida"
git push --force-with-lease
```

Se for um commit mais antigo:

```bash
git rebase -i <commit-anterior-ao-que-precisa-mudar>
# marque o commit com problema como "reword" (ou "r")
# salve, edite a mensagem, salve novamente
git push --force-with-lease
```

O log do check mostra qual commit foi reprovado e qual regra foi violada.

### Título do PR fora do padrão

Edite o título do PR no GitHub, no formato `[TIPO] Descrição`, igual ao título da issue vinculada. O check roda de novo sozinho, sem novo push.

---

## Decisões

| Ponto | Decisão |
| --- | --- |
| Lista de tipos de commit | A lista do APAE-INFRA (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `build`) é o padrão. O APAE-atendimento, que usa também `style`, `perf`, `revert`, `cleanup` e `remove`, mantém a configuração dele via `config-file` |
| Tags do título do PR | `FEAT`, `FIX`, `DOCS`, `CHORE`, `CI`, `REFACTOR`, `TEST` e `BUILD` |
| Squash merge | Mantido por enquanto. Nele, o título do PR vira a mensagem do commit final e não segue o Conventional Commits. A decisão de desabilitar o squash fica para a gestão das configurações do GitHub (issue #88) |
| Commits de bots | Ignorados. PRs abertos por bots não passam pela validação |

---

## Limitações

- O APAE-INFRA precisa ser público, porque o workflow baixa a configuração compartilhada sem credenciais extras.
- Tornar o check obrigatório na proteção de branch não faz parte deste workflow. É tratado na issue #88.
- Hooks locais (Husky) continuam opcionais e não substituem a validação na CI.
