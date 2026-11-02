# Workflow reutilizável de SAST com Semgrep

> **Repositório mantenedor:** [`IFPBEsp/APAE-INFRA`](https://github.com/IFPBEsp/APAE-INFRA)  
> **Arquivo do workflow:** [`.github/workflows/sast-semgrep.yml`](https://github.com/IFPBEsp/APAE-INFRA/blob/dev/.github/workflows/sast-semgrep.yml)  
> **Regras compartilhadas:** [`.semgrep/rules.yml`](https://github.com/IFPBEsp/APAE-INFRA/blob/dev/.semgrep/rules.yml)  
> **Issue de origem:** [APAE-INFRA #69](https://github.com/IFPBEsp/APAE-INFRA/issues/69)

---

## 1. Objetivo

O workflow **Reusable Semgrep SAST** centraliza e padroniza a análise estática de segurança de código (SAST) para todos os repositórios do ecossistema APAE (`APAE`, `APAE-atendimento`, `APAE-gestao-escolar` e `apae-site-comemorativo`).

Suas principais características e benefícios:

- **Versões fixadas e imutáveis:** Semgrep instalado em versão fixada (`1.183.0` por padrão) e GitHub Actions fixadas por SHA completo de commit.
- **Regras compartilhadas centralizadas:** Mantidas no `APAE-INFRA` em `.semgrep/rules.yml`, cobrindo vulnerabilidades críticas comuns às stacks Spring e React (ex.: XSS com `dangerouslySetInnerHTML`, @RequestMapping sem verbo HTTP e XXE em `DocumentBuilderFactory`).
- **Análise Diff-Aware:** Por padrão, analisa apenas os arquivos/linhas alterados no Pull Request em relação à branch de destino (usando `git merge-base` e `--baseline-commit`), prevenindo que débitos técnicos legados bloqueiem novos PRs.
- **Bloqueio por severidade configurável:** Avalia os achados e bloqueia o PR caso haja findings com severidade igual ou superior a `fail-severity` (padrão: `ERROR`).
- **Publicação na aba Security (SARIF):** Converte e envia os resultados via SARIF para a aba **Security > Code scanning** do GitHub.
- **Privilégios mínimos:** Permissões estritamente restritas a `contents: read` e `security-events: write`.

---

## 2. Inputs do Workflow

| Input | Tipo | Obrigatório | Padrão | Descrição |
| :--- | :---: | :---: | :---: | :--- |
| `rulesets` | `string` | Não | `p/default` | Rulesets do Semgrep a serem avaliados, um por linha (ex.: `p/default`, `p/java`, `p/typescript`, `p/react`). |
| `extra-rules-file` | `string` | Não | `""` (vazio) | Caminho relativo de um arquivo de regras customizadas local do próprio repositório chamador (ex.: `.github/semgrep-custom-rules.yml`). |
| `diff-aware` | `boolean` | Não | `true` | Se `true`, ativa a análise incremental contra a base branch do PR (`git merge-base`). |
| `fail-severity` | `string` | Não | `ERROR` | Severidade mínima de achados que reprova o job no PR. Aceita: `ERROR`, `WARNING`, `INFO`. |
| `semgrep-version` | `string` | Não | `1.183.0` | Versão do Semgrep a ser instalada via pip. |

---

## 3. Regras Compartilhadas Centralizadas

O `APAE-INFRA` disponibiliza automaticamente o arquivo compartilhado [`.semgrep/rules.yml`](https://github.com/IFPBEsp/APAE-INFRA/blob/dev/.semgrep/rules.yml), que é carregado em toda execução:

1. **`react-dangerouslysetinnerhtml`** (Severidade: `WARNING`):  
   Detecta o uso de `dangerouslySetInnerHTML` em componentes React, prevenindo riscos de Cross-Site Scripting (XSS).
2. **`spring-unrestricted-request-mapping`** (Severidade: `WARNING`):  
   Detecta anotações `@RequestMapping` sem declaração do método HTTP, exigindo uso de `@GetMapping`, `@PostMapping` ou especificação de `method`.
3. **`spring-xxe-documentbuilderfactory`** (Severidade: `ERROR`):  
   Detecta instâncias de `DocumentBuilderFactory` sem a desativação expressa de DTDs (`disallow-doctype-decl`), prevenindo ataques de XML External Entity (XXE).

---

## 4. Guia de Adesão nos Repositórios

Para adotar o workflow em qualquer repositório do projeto, siga os passos abaixo:

### 4.1. Substituição no `APAE-atendimento`

No arquivo `.github/workflows/ci.yml` do repositório `APAE-atendimento`, o job `security` original rodava:

```yaml
# ANTES (Job legado no ci.yml do APAE-atendimento):
security:
  name: Semgrep Custom Rules
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
    - name: Instalar Semgrep
      run: python3 -m pip install semgrep
    - name: Rodar Semgrep
      run: semgrep scan --config="p/default" --config="p/java" --config="p/typescript" --config=".github/semgrep-custom-rules.yml" --error
```

Substitua pelo chamado do reusable workflow:

```yaml
# DEPOIS (Utilizando o reusable workflow centralizado):
security:
  name: SAST (Semgrep)
  uses: IFPBEsp/APAE-INFRA/.github/workflows/sast-semgrep.yml@dev
  permissions:
    contents: read
    security-events: write
  with:
    rulesets: |
      p/default
      p/java
      p/typescript
    diff-aware: true
    fail-severity: ERROR
```

*(Observação: Como as regras customizadas do `.github/semgrep-custom-rules.yml` agora estão centralizadas no `APAE-INFRA`, o arquivo local do repositório pode ser removido ou mantido vazio se não houver regras exclusivas dele).*

---

### 4.2. Exemplo de Workflow Autônomo para Pull Requests

Para repositórios que desejam um workflow dedicado de segurança (ex.: `.github/workflows/sast.yml`):

```yaml
name: SAST Security Scan

on:
  pull_request:
    branches:
      - main
      - dev

permissions:
  contents: read
  security-events: write

jobs:
  sast:
    name: Semgrep SAST
    uses: IFPBEsp/APAE-INFRA/.github/workflows/sast-semgrep.yml@dev
    with:
      rulesets: |
        p/default
        p/java
        p/typescript
      diff-aware: true
      fail-severity: ERROR
```

---

## 5. Pontos Decididos e Recomendações

### Rulesets recomendados por stack
- **Stack Fullstack (Java + TypeScript / React):**  
  `p/default`, `p/java`, `p/typescript`, `p/react`
- **Stack Backend (Java Spring):**  
  `p/default`, `p/java`, `p/spring`
- **Stack Frontend (TypeScript / React):**  
  `p/default`, `p/typescript`, `p/react`

### Sobreposição com SonarQube (#34)
O Semgrep atua primariamente na camada de **SAST rápido e focado em padrões de segurança / AST matching** no ciclo de feedback do Pull Request (diff-aware, executando em poucos segundos e sem necessidade de compilação completa de dependências). Já o SonarQube (#34) complementa com métricas de cobertura de código, bugs funcionais, code smells e conformidade de qualidade geral.
