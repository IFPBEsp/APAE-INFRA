# Workflows Reutilizáveis de Análise Estática (SonarCloud / SonarQube)

> **Repositório mantenedor:** [`IFPBEsp/APAE-INFRA`](https://github.com/IFPBEsp/APAE-INFRA)
> **Workflows:** [`.github/workflows/reusable-sonarqube-maven.yml`](../../.github/workflows/reusable-sonarqube-maven.yml) e [`.github/workflows/reusable-sonarqube-node.yml`](../../.github/workflows/reusable-sonarqube-node.yml)
> **Guia operacional do SonarCloud:** [Configuração e Governança do SonarCloud](../sonarcloud.md)
> **Issues relacionadas:** #172 (SonarCloud) e #34 (SonarQube self-hosted)

## Objetivo

Os workflows reutilizáveis de análise estática centralizam a execução do scanner Sonar, o envio de relatórios de cobertura (JaCoCo e LCOV) e a verificação obrigatória da **Quality Gate** para todos os repositórios de produto da organização `IFPBEsp`.

A solução é dividida por stack:

1. **Java / Maven** (`.github/workflows/reusable-sonarqube-maven.yml`): executa build/testes via Maven (`./mvnw` ou `mvn`) e envia a análise usando `org.sonarsource.scanner.maven:sonar-maven-plugin:sonar`.
2. **Node.js / TypeScript** (`.github/workflows/reusable-sonarqube-node.yml`): instala dependências (`pnpm` ou `npm`), executa testes com cobertura quando configurados e executa o scan via `SonarSource/sonarqube-scan-action`.

Ambos os workflows utilizam `sonar-host-url` parametrizado com padrão `https://sonarcloud.io` e aguardam o resultado da Quality Gate (`-Dsonar.qualitygate.wait=true`), reprovando o pipeline de CI caso a Quality Gate falhe.

---

## 1. Workflow Java / Maven (`reusable-sonarqube-maven.yml`)

### Inputs (Maven)

| Input | Tipo | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- | --- |
| `project-key` | `string` | Sim | — | Chave única do projeto no SonarCloud / SonarQube |
| `organization` | `string` | Não | `""` | Chave da organização no SonarCloud (deixar vazio no SonarQube self-hosted) |
| `working-directory` | `string` | Não | `.` | Diretório raiz do projeto Maven (`pom.xml`), relativo à raiz do repositório |
| `java-version` | `string` | Não | `21` | Versão do JDK Temurin |
| `sonar-host-url` | `string` | Não | `https://sonarcloud.io` | URL do servidor SonarCloud / SonarQube |
| `exclusions` | `string` | Não | `""` | Padrões glob de exclusão de análise (`sonar.exclusions`), separados por vírgula |
| `coverage-exclusions` | `string` | Não | `""` | Padrões glob de exclusão de cobertura (`sonar.coverage.exclusions`), separados por vírgula |
| `coverage-report-path` | `string` | Não | `target/site/jacoco/jacoco.xml` | Caminho do relatório XML do JaCoCo relativo ao `working-directory` |
| `maven-args` | `string` | Não | `clean verify` | Metas e flags Maven executadas antes da análise Sonar |
| `quality-gate-timeout` | `number` | Não | `300` | Tempo máximo em segundos aguardando a Quality Gate |

### Secrets (Maven)

| Secret | Obrigatório | Descrição |
| --- | --- | --- |
| `SONAR_TOKEN` | Não (obrigatório em runs internos) | Token de autenticação no SonarCloud / SonarQube. Declarado opcional no contrato para permitir tratamento seguro em PRs de forks |
| `SONAR_HOST_URL` | Não | URL alternativa via secret (sobrescreve o input `sonar-host-url` quando definida) |

### Funcionamento (Maven)

1. Faz checkout completo (`fetch-depth: 0`, `persist-credentials: false`) para habilitar detecção de *New Code* e *blame* pelo Sonar.
2. Valida caminhos, presença de `pom.xml`, disponibilidade de `./mvnw` ou `mvn`, formato da URL e disponibilidade de `SONAR_TOKEN`.
3. Configura JDK Temurin com cache Maven e cache de pacotes Sonar (`~/.sonar/cache`).
4. Executa `./mvnw -B <maven-args>` (por padrão `clean verify`).
5. Em runs internos com `SONAR_TOKEN`, verifica a existência do XML do JaCoCo (tentando `jacoco:report` caso ainda não exista) e executa `org.sonarsource.scanner.maven:sonar-maven-plugin:sonar` com `-Dsonar.qualitygate.wait=true`.

---

## 2. Workflow Node.js / TypeScript (`reusable-sonarqube-node.yml`)

### Inputs (Node)

| Input | Tipo | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- | --- |
| `project-key` | `string` | Sim | — | Chave única do projeto no SonarCloud / SonarQube |
| `organization` | `string` | Não | `""` | Chave da organização no SonarCloud (deixar vazio no SonarQube self-hosted) |
| `working-directory` | `string` | Não | `.` | Diretório raiz do projeto Node (`package.json`), relativo à raiz do repositório |
| `node-version` | `string` | Não | `22` | Versão do Node.js |
| `sonar-host-url` | `string` | Não | `https://sonarcloud.io` | URL do servidor SonarCloud / SonarQube |
| `exclusions` | `string` | Não | `""` | Padrões glob de exclusão de análise (`sonar.exclusions`), separados por vírgula |
| `coverage-exclusions` | `string` | Não | `""` | Padrões glob de exclusão de cobertura (`sonar.coverage.exclusions`), separados por vírgula |
| `coverage-report-path` | `string` | Não | `coverage/lcov.info` | Caminho do relatório LCOV relativo ao `working-directory` |
| `run-tests` | `boolean` | Não | `true` | Executa a suíte de testes com cobertura antes do scan |
| `test-command` | `string` | Não | `""` | Comando customizado para execução dos testes (quando vazio, detecta `test:coverage` ou `test`) |
| `quality-gate-timeout` | `number` | Não | `300` | Tempo máximo em segundos aguardando a Quality Gate |

### Secrets (Node)

| Secret | Obrigatório | Descrição |
| --- | --- | --- |
| `SONAR_TOKEN` | Não (obrigatório em runs internos) | Token de autenticação no SonarCloud / SonarQube |
| `SONAR_HOST_URL` | Não | URL alternativa via secret (sobrescreve o input `sonar-host-url` quando definida) |

### Funcionamento (Node)

1. Faz checkout completo (`fetch-depth: 0`, `persist-credentials: false`).
2. Valida caminhos, `package.json`, gerenciador de pacotes (`pnpm` quando há `pnpm-lock.yaml` no subprojeto ou na raiz; caso contrário `npm`) e disponibilidade de `SONAR_TOKEN`.
3. Instala dependências (`pnpm install --frozen-lockfile --dangerously-allow-all-builds` ou `npm ci`).
4. Se `run-tests` for `true`, executa `test-command` (se informado), `test:coverage` ou `test` com `--coverage`. Caso não haja script de teste configurado, registra aviso e segue para o scan.
5. Monta os argumentos do scanner (passando `-Dsonar.organization`, `-Dsonar.exclusions`, `-Dsonar.coverage.exclusions` e `-Dsonar.javascript.lcov.reportPaths` apenas quando preenchidos/existentes, preservando propriedades locais de `sonar-project.properties` quando não sobrescritas).
6. Executa `SonarSource/sonarqube-scan-action` (fixado por SHA completo) com `projectBaseDir` apontando para `working-directory` e `-Dsonar.qualitygate.wait=true`.

---

## Comportamento para Pull Requests de Forks

Por política de segurança do GitHub Actions, secrets (como `SONAR_TOKEN`) **não são expostos** em eventos `pull_request` originados de repositórios *fork*.

Para evitar falhas falsas em contribuições externas e sem recorrer a `pull_request_target` (que traz risco de execução de código não confiável com acesso a secrets):

1. Ambos os workflows declaram `SONAR_TOKEN` com `required: false`.
2. Durante a validação inicial:
   - **Se `SONAR_TOKEN` estiver presente:** executa build/testes e envia a análise ao SonarCloud / SonarQube normalmente.
   - **Se `SONAR_TOKEN` estiver ausente e o PR vier de um fork:** executa normalmente o build e os testes automatizados (garantindo validação funcional do PR), registra aviso (`::notice::` e resumo no *Job Summary*) e **pula apenas a etapa de envio ao Sonar**, concluindo o job sem falha.
   - **Se `SONAR_TOKEN` estiver ausente em PR interno ou `push`:** falha imediatamente com erro explícito de configuração ausente.

> [!NOTE]
> Caso o repositório chamador prefira nem disparar o job de Sonar em forks, pode também adicionar `if: github.event_name != 'pull_request' || github.event.pull_request.head.repo.fork == false` no job chamador. A implementação padrão nos workflows reutilizáveis já protege ambos os cenários.

---

## Configuração de Cobertura nos Repositórios de Produto

Os workflows sobrescrevem `sonar.host.url` e `sonar.projectKey` via CLI, permitindo manter as configurações locais (`docker-compose.sonar.yml` / `.scripts/sonar-scan-frontend.sh`) funcionando sem conflito.

### Backend Java / Maven (JaCoCo XML)

O `pom.xml` deve incluir o `jacoco-maven-plugin` gerando o relatório XML durante a fase `verify`:

```xml
<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
  <version>0.8.12</version>
  <executions>
    <execution>
      <goals>
        <goal>prepare-agent</goal>
      </goals>
    </execution>
    <execution>
      <id>report</id>
      <phase>verify</phase>
      <goals>
        <goal>report</goal>
      </goals>
    </execution>
  </executions>
</plugin>
```

Caso o projeto ainda não possua o `sonar-maven-plugin` declarado, o workflow invoca `org.sonarsource.scanner.maven:sonar-maven-plugin:sonar` explicitamente.

### Frontend Node.js / TypeScript (LCOV)

Para envio de cobertura ao SonarCloud, o test runner deve gerar `coverage/lcov.info`.

Exemplo com **Vitest** (`vitest.config.ts`):

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      reportsDirectory: "./coverage",
    },
  },
});
```

Exemplo com **Jest** (`jest.config.js`):

```js
module.exports = {
  collectCoverage: true,
  coverageReporters: ["text", "lcov"],
  coverageDirectory: "coverage",
};
```

> [!IMPORTANT]
> Certifique-se de que `coverage/` esteja no `.gitignore` do repositório de aplicação e que o pacote de cobertura (ex.: `@vitest/coverage-v8`) esteja nas `devDependencies` do `package.json`.

---

## Exemplos de Uso (Callers nos Repositórios de Produto)

Em todos os repositórios consumidores, substitua `<commit-sha>` pelo **SHA completo de 40 caracteres** do commit aprovado no `IFPBEsp/APAE-INFRA` (evitando referências mutáveis como `@main` ou `@dev`).

### 1. `IFPBEsp/APAE` (Monorepo: Backend Java + Frontend Node)

Arquivo `.github/workflows/sonar.yml`:

```yaml
name: SonarCloud Analysis

on:
  push:
    branches:
      - main
      - dev
  pull_request:
    branches:
      - main
      - dev

permissions:
  contents: read

jobs:
  sonar-api:
    name: Sonar Analysis (API)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-maven.yml@<commit-sha>
    with:
      project-key: "IFPBEsp_APAE_api"
      organization: "ifpbesp"
      working-directory: "apps/api"
      java-version: "21"
      coverage-report-path: "target/site/jacoco/jacoco.xml"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  sonar-apae:
    name: Sonar Analysis (Frontend)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-node.yml@<commit-sha>
    with:
      project-key: "IFPBEsp_APAE_frontend"
      organization: "ifpbesp"
      working-directory: "apps/apae"
      node-version: "22"
      coverage-report-path: "coverage/lcov.info"
      exclusions: "node_modules/**,dist/**,coverage/**"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### 2. `IFPBEsp/APAE-gestao-escolar` (Monorepo: Backend Java + Frontend Node)

Arquivo `.github/workflows/sonar.yml`:

```yaml
name: SonarCloud Analysis

on:
  push:
    branches:
      - main
      - dev
  pull_request:
    branches:
      - main
      - dev

permissions:
  contents: read

jobs:
  sonar-backend:
    name: Sonar Analysis (Backend)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-maven.yml@<commit-sha>
    with:
      project-key: "IFPBEsp_APAE-gestao-escolar_backend"
      organization: "ifpbesp"
      working-directory: "backend"
      java-version: "21"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  sonar-frontend:
    name: Sonar Analysis (Frontend)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-node.yml@<commit-sha>
    with:
      project-key: "IFPBEsp_APAE-gestao-escolar_frontend"
      organization: "ifpbesp"
      working-directory: "frontend"
      node-version: "22"
      exclusions: "node_modules/**,dist/**,coverage/**"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

*(Ajuste `working-directory` conforme a estrutura real dos diretórios no repositório.)*

### 3. `IFPBEsp/APAE-atendimento` (Monorepo: Backend Java + Frontend Node)

Arquivo `.github/workflows/sonar.yml`:

```yaml
name: SonarCloud Analysis

on:
  push:
    branches:
      - main
      - dev
  pull_request:
    branches:
      - main
      - dev

permissions:
  contents: read

jobs:
  sonar-backend:
    name: Sonar Analysis (Backend)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-maven.yml@<commit-sha>
    with:
      project-key: "IFPBEsp_APAE-atendimento_backend"
      organization: "ifpbesp"
      working-directory: "backend/atendimento"
      java-version: "21"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  sonar-frontend:
    name: Sonar Analysis (Frontend)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-node.yml@<commit-sha>
    with:
      project-key: "IFPBEsp_APAE-atendimento_frontend"
      organization: "ifpbesp"
      working-directory: "frontend/atendimento-app"
      node-version: "22"
      exclusions: "node_modules/**,dist/**,coverage/**"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### 4. `IFPBEsp/apae-site-comemorativo` (Aplicação Única Node/TS)

Arquivo `.github/workflows/sonar.yml`:

```yaml
name: SonarCloud Analysis

on:
  push:
    branches:
      - main
      - dev
  pull_request:
    branches:
      - main
      - dev

permissions:
  contents: read

jobs:
  sonar-frontend:
    name: Sonar Analysis (Site Comemorativo)
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-node.yml@<commit-sha>
    with:
      project-key: "IFPBEsp_apae-site-comemorativo"
      organization: "ifpbesp"
      working-directory: "."
      node-version: "22"
      coverage-report-path: "coverage/lcov.info"
      exclusions: "node_modules/**,.next/**,dist/**,coverage/**"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

---

## Execução Local Antes do PR

Para rodar a análise manualmente contra o SonarCloud (ou contra a instância local via Docker):

### Java / Maven Local

```bash
export SONAR_TOKEN="<seu-token>"
./mvnw clean verify org.sonarsource.scanner.maven:sonar-maven-plugin:sonar \
  -Dsonar.projectKey="<project-key>" \
  -Dsonar.organization="ifpbesp" \
  -Dsonar.host.url="https://sonarcloud.io"
```

### Node / TypeScript Local

```bash
export SONAR_TOKEN="<seu-token>"
pnpm test --coverage
npx sonar-scanner \
  -Dsonar.projectKey="<project-key>" \
  -Dsonar.organization="ifpbesp" \
  -Dsonar.host.url="https://sonarcloud.io" \
  -Dsonar.javascript.lcov.reportPaths="coverage/lcov.info"
```

---

## Caminho de Migração para o SonarQube Self-Hosted (#34)

Quando a instância self-hosted prevista na issue #34 estiver operacional:

1. **Não é necessário reescrever os workflows reutilizáveis** no `APAE-INFRA` nem alterar a estrutura dos callers.
2. Nos arquivos `.github/workflows/sonar.yml` dos repositórios de produto:
   - Defina `sonar-host-url: "https://<url-do-sonarqube-self-hosted>"` (ou configure a secret `SONAR_HOST_URL` nos repositórios/organização);
   - Remova ou deixe vazio o input `organization: ""` (o SonarQube Server não utiliza chave de organização);
   - Atualize `project-key` caso os projetos criados no servidor interno utilizem outra nomenclatura;
   - Atualize o valor do secret `SONAR_TOKEN` no GitHub com o token gerado na instância self-hosted.
3. Caso o SonarQube self-hosted utilize runners privados isolados em rede interna (como previsto originalmente para a #34), apenas ajuste `runs-on` (ou adicione input `runs-on`) nos workflows reutilizáveis do `APAE-INFRA`.
