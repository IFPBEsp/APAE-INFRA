# Workflow reutilizável de verificação de dependências vulneráveis (SCA)

## Objetivo

O workflow `.github/workflows/sca-reusable.yml` centraliza a verificação estática de segurança de dependências (SCA — *Software Composition Analysis*) nos Pull Requests dos repositórios da organização APAE.

O objetivo é garantir a prática de *Shift-Left Security*, detectando dependências vulneráveis conhecidas (CVEs/GHSAs) antes que sejam integradas às branches principais (`dev` / `main`).

O workflow analisa os seguintes ecossistemas:

- **Maven (`pom.xml`)**: Aplicações Java / Spring Boot.
- **pnpm (`pnpm-lock.yaml`)**: Aplicações Node.js / TypeScript.
- **npm (`package-lock.json`)**: Aplicações Node.js / JavaScript.

---

## Inputs

| Input | Tipo | Obrigatório | Padrão | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `scan-path` | `string` | Não | `.` | Diretório onde os manifestos ou lockfiles estão localizados. |
| `severity` | `string` | Não | `HIGH,CRITICAL` | Severidades que bloqueiam o Pull Request (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`). |
| `ignore-unfixed` | `boolean` | Não | `true` | Se `true`, ignora vulnerabilidades que ainda não possuem correção oficial disponível. |
| `trivyignores` | `string` | Não | `.trivyignore` | Caminho do arquivo de exceções versionado no repositório. |
| `upload-sarif` | `boolean` | Não | `true` | Se `true`, tenta publicar o relatório SARIF na área de Code scanning do GitHub quando o arquivo for gerado. |
| `fail-on-vulnerabilities` | `boolean` | Não | `true` | Se `true`, falha o job do PR caso vulnerabilidades não suprimidas sejam encontradas. |

---

## Saídas e Integrações

1. **Aba Security (GitHub Code Scanning)**:
   - Os resultados são exportados no formato SARIF e publicados via `github/codeql-action/upload-sarif`.
   - Podem ser visualizados na aba **Security > Code scanning alerts** do repositório.
2. **GitHub Step Summary**:
   - Uma tabela detalhada com cada vulnerabilidade encontrada, severidade, pacote afetado e versão corrigida é adicionada ao resumo da execução da Action.
3. **Bloqueio de PR**:
   - O PR é bloqueado quando vulnerabilidades nas severidades configuradas (por padrão `HIGH` ou `CRITICAL`) possuírem correção disponível e não estiverem justificadas no arquivo de exceções.

---

## Política de Exceções (`.trivyignore`)

Em situações onde uma biblioteca vulnerável não puder ser atualizada imediatamente (por exemplo, ausência de patch compatível ou quebra de arquitetura que exige refatoração), o time pode definir uma **exceção justificada e com prazo determinado**.

O arquivo deve se chamar `.trivyignore` e residir na raiz do repositório da aplicação (ou no caminho configurado no input `trivyignores`).

### Formato aceito

O Trivy aceita identificadores de vulnerabilidade acompanhados de comentários e diretiva de expiração:

```text
# Formato: <ID_CVE_OU_GHSA> [exp:YYYY-MM-DD] [# justificativa]
CVE-2023-34062 exp:2026-12-31 # Spring Framework: patch planejado no sprint 14 (issue #123)
GHSA-w8qv-6jwh-64r5 exp:2026-11-15 # Pacote de build dev; sem impacto em tempo de execução
```

### Regras para aprovação de exceções

1. Toda exceção deve incluir um comentário explicando a **justificativa técnica** e o link da issue de correção planejada.
2. Toda exceção deve conter uma **data limite de expiração (`exp:YYYY-MM-DD`)**. Após a data expirar, o Trivy volta a bloquear a pipeline automaticamente.
3. O `.trivyignore` é versionado no Git e sua alteração deve passar pelo fluxo regular de Code Review no Pull Request.

---

## Exemplos de Adoção nos Repositórios da APAE

### 1. Repositório Monorepo com múltiplos ecossistemas (`IFPBEsp/APAE`)

O repositório `APAE` possui Maven em `apps/api` e pnpm em `apps/apae`. Pode-se criar uma matriz ou jobs dedicados:

```yaml
name: Dependency Vulnerability Check (SCA)

on:
  pull_request:
    paths:
      - "apps/api/**"
      - "apps/apae/**"
      - ".trivyignore"

permissions:
  contents: read
  security-events: write

jobs:
  sca-api:
    name: SCA Maven (apps/api)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/sca-reusable.yml@<commit-sha>
    with:
      scan-path: "apps/api"
      severity: "HIGH,CRITICAL"
      ignore-unfixed: true

  sca-frontend:
    name: SCA pnpm (apps/apae)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/sca-reusable.yml@<commit-sha>
    with:
      scan-path: "apps/apae"
      severity: "HIGH,CRITICAL"
      ignore-unfixed: true
```

### 2. Repositório `IFPBEsp/APAE-gestao-escolar` (Maven e npm)

```yaml
name: Dependency Vulnerability Check (SCA)

on:
  pull_request:
    paths:
      - "api/**"
      - "app/**"
      - ".trivyignore"

permissions:
  contents: read
  security-events: write

jobs:
  sca-backend:
    name: SCA Maven (api)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/sca-reusable.yml@<commit-sha>
    with:
      scan-path: "api"

  sca-frontend:
    name: SCA npm (app)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/sca-reusable.yml@<commit-sha>
    with:
      scan-path: "app"
```

### 3. Repositório `IFPBEsp/apae-site-comemorativo` (pnpm raiz)

```yaml
name: Dependency Vulnerability Check (SCA)

on:
  pull_request:
    paths:
      - "package.json"
      - "pnpm-lock.yaml"
      - ".trivyignore"

permissions:
  contents: read
  security-events: write

jobs:
  sca:
    name: SCA Dependencies
    uses: IFPBEsp/APAE-INFRA/.github/workflows/sca-reusable.yml@<commit-sha>
    with:
      scan-path: "."
```

### Aviso sobre filtros `paths` e checks obrigatórios

> **Não torne obrigatório um check que pode deixar de ser criado devido a filtros de caminho.** Se um workflow de `pull_request` for ignorado por `paths`, o check pode ficar pendente e bloquear o merge. Se o SCA for obrigatório em todos os PRs, remova os filtros de caminho ou adote uma estratégia de workflow/check que produza um resultado conclusivo em todas as alterações relevantes. Valide o comportamento nas regras de proteção/rulesets da organização.

Os filtros dos exemplos são ilustrativos e devem ser adaptados à estrutura real de cada repositório. Considere também arquivos que alteram dependências, como manifestos, lockfiles, `.trivyignore` e configurações do próprio workflow.

> [!IMPORTANT]
> A referência `<commit-sha>` deve ser substituída pelo SHA completo do commit aprovado no `APAE-INFRA`. Evite o uso de tags mutáveis como `@main` ou `@dev`.

---

## Permissões Necessárias

O workflow requer apenas:

```yaml
permissions:
  contents: read          # Leitura do repositório para análise de arquivos
  security-events: write  # Upload de SARIF para a aba Security
```
