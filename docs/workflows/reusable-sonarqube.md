# Workflows Reutilizáveis de Análise de Código (SonarQube)

## Objetivo

Os workflows reutilizáveis de SonarQube centralizam a análise estática de código, acompanhamento de dívida técnica, vulnerabilidades, code smells e cobertura de testes para os repositórios da organização APAE.

Para atender à diversidade de tecnologias dos projetos de produto, a solução é componentizada em dois workflows:

1. `.github/workflows/reusable-sonarqube-maven.yml`: Análise para aplicações Java que utilizam Apache Maven (ex: API/backend da APAE).
2. `.github/workflows/reusable-sonarqube-node.yml`: Análise para aplicações JavaScript / TypeScript utilizando `npm` ou `pnpm` (ex: frontends e portais).

Ambos os workflows realizam a verificação obrigatória de **Quality Gate**, falhando a pipeline de integração contínua (CI) caso os critérios mínimos de qualidade e cobertura definidos com o time de QA não sejam atingidos.

---

## Modelos de Hospedagem Suportados

Os workflows são agnósticos e suportam dois modelos de hospedagem:

1. **SonarQube Cloud (SaaS)**:
   - Host padrão: `https://sonarcloud.io`
   - Requer `organization` e `project-key`.
2. **SonarQube Server (Self-hosted)**:
   - Instância interna (ex: laboratório IDE.IA ou VM externa).
   - Não requer o parâmetro `organization`.
   - Pode ser configurado informando `sonar-host-url` ou definindo a secret `SONAR_HOST_URL` no repositório.

---

## 1. Workflow Java / Maven (`reusable-sonarqube-maven.yml`)

### Inputs

| Input | Descrição | Obrigatório | Padrão |
| --- | --- | --- | --- |
| `project-key` | Chave única do projeto no SonarQube / SonarCloud | Sim | - |
| `organization` | Identificador da organização (obrigatório no SonarQube Cloud) | Não | `""` |
| `working-directory` | Caminho do subdiretório onde está localizado o `pom.xml` | Não | `.` |
| `java-version` | Versão do JDK utilizada para build e scan | Não | `21` |
| `sonar-host-url` | URL do servidor SonarQube / SonarCloud | Não | `https://sonarcloud.io` |

### Secrets

| Secret | Descrição | Obrigatório |
| --- | --- | --- |
| `SONAR_TOKEN` | Token de autenticação gerado no SonarQube / SonarCloud | Sim |
| `SONAR_HOST_URL` | URL do servidor SonarQube (se definida globalmente via secrets) | Não |

---

## 2. Workflow Node.js / TypeScript (`reusable-sonarqube-node.yml`)

### Inputs

| Input | Descrição | Obrigatório | Padrão |
| --- | --- | --- | --- |
| `project-key` | Chave única do projeto no SonarQube / SonarCloud | Sim | - |
| `organization` | Identificador da organização (obrigatório no SonarQube Cloud) | Não | `""` |
| `working-directory` | Caminho do subdiretório onde está o `package.json` | Não | `.` |
| `node-version` | Versão do Node.js | Não | `22` |
| `sonar-host-url` | URL do servidor SonarQube / SonarCloud | Não | `https://sonarcloud.io` |
| `run-tests` | Executa suíte de testes com cobertura (`--coverage`) antes do scan | Não | `true` |

### Secrets

| Secret | Descrição | Obrigatório |
| --- | --- | --- |
| `SONAR_TOKEN` | Token de autenticação gerado no SonarQube / SonarCloud | Sim |
| `SONAR_HOST_URL` | URL do servidor SonarQube (se definida globalmente via secrets) | Não |

---

## Exemplos de Uso nos Repositórios de Produto

Cada repositório chamador ("caller") precisa apenas de um arquivo enxuto em `.github/workflows/`, referenciando o workflow reutilizável correspondente.

### 1. Repositório `IFPBEsp/APAE` (Monorepo com Backend Java e Frontend React)

Arquivo `.github/workflows/sonar.yml` no repositório `APAE`:

```yaml
name: Code Quality Scan

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]

permissions:
  contents: read

jobs:
  sonar-backend:
    name: Backend Analysis
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-maven.yml@main
    with:
      project-key: "ifpbesp_apae-backend"
      organization: "ifpbesp"
      working-directory: "backend"
      java-version: 21"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  sonar-frontend:
    name: Frontend Analysis
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-node.yml@main
    with:
      project-key: "ifpbesp_apae-frontend"
      organization: "ifpbesp"
      working-directory: "frontend"
      node-version: "22"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### 2. Repositório `IFPBEsp/apae-site-comemorativo` (Frontend / Estático)

Arquivo `.github/workflows/sonar.yml`:

```yaml
name: Code Quality Scan

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]

permissions:
  contents: read

jobs:
  sonar:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-node.yml@main
    with:
      project-key: "ifpbesp_apae-site-comemorativo"
      organization: "ifpbesp"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### 3. Repositórios `IFPBEsp/APAE-atendimento` e `IFPBEsp/APAE-gestao-escolar`

Para serviços em Java/Maven:

```yaml
name: Code Quality Scan

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]

permissions:
  contents: read

jobs:
  sonar:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-maven.yml@main
    with:
      project-key: "ifpbesp_apae-atendimento"
      organization: "ifpbesp"
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

---

## Execução Local do Scanner Antes do PR

Para evitar abrir Pull Requests com reprovação no Quality Gate, os desenvolvedores podem rodar a análise localmente:

### Stack Java / Maven

```bash
mvn clean verify sonar:sonar \
  -Dsonar.projectKey="<SUA_PROJECT_KEY>" \
  -Dsonar.host.url="https://sonarcloud.io" \
  -Dsonar.login="<SEU_SONAR_TOKEN>"
```

### Stack Node / TS

Instalar globalmente o sonar-scanner ou via npx:

```bash
npm test -- --coverage
npx sonar-scanner \
  -Dsonar.projectKey="<SUA_PROJECT_KEY>" \
  -Dsonar.sources="src" \
  -Dsonar.host.url="https://sonarcloud.io" \
  -Dsonar.token="<SEU_SONAR_TOKEN>"
```

---

## Gestão de Credenciais

- **Criação do Token**: Gerado no SonarQube / SonarCloud em `User Account` > `Security` > `Generate Token` (tipo: Global ou Project Analysis).
- **Configuração no GitHub**: Cadastrar o token em cada repositório de produto em `Settings` > `Secrets and variables` > `Actions` com o nome `SONAR_TOKEN`.
- **Organização**: Em caso de SonarCloud, certifique-se de que a secret não seja exposta em logs públicos (`SONAR_TOKEN` é omitido automaticamente pelo GitHub Actions).
