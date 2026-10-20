# Validação da Pipeline Reutilizável do SonarQube

## Objetivo

Este documento registra a validação da integração do SonarQube Cloud com os workflows reutilizáveis centralizados no repositório `APAE-INFRA`.

A validação teve como objetivo comprovar que os workflows reutilizáveis conseguem:

- executar análise estática em projetos Java/Maven e Node.js/TypeScript;
- consumir credenciais por meio de `GitHub Actions Secrets`;
- publicar análises no SonarQube Cloud;
- aguardar e respeitar o resultado do Quality Gate;
- operar com projetos localizados na raiz do repositório ou em subdiretórios;
- funcionar em diferentes repositórios consumidores sem duplicação da lógica de CI.

## Pull Requests relacionados

A validação foi realizada a partir dos seguintes Pull Requests:

- `IFPBEsp/APAE-INFRA#54`: workflows reutilizáveis de análise SonarQube;
- `IFPBEsp/APAE#975`: caller do repositório APAE;
- `IFPBEsp/apae-site-comemorativo#61`: caller do site comemorativo.

## Estratégia de validação

Para evitar impacto em projetos oficiais do SonarQube Cloud e nas branches principais dos repositórios, a validação utilizou:

- organização de teste no SonarQube Cloud;
- projetos temporários de teste;
- branch `test/sonarqube-pipeline`;
- token específico de análise armazenado em `SONAR_TOKEN`;
- referência temporária ao commit do PR de infraestrutura enquanto o reusable ainda não estava disponível em `dev`.

A branch de teste foi criada a partir da branch já utilizada pelo Pull Request de cada repositório consumidor.

## Credenciais

O token utilizado durante os testes foi configurado exclusivamente como GitHub Actions Secret:

```text
SONAR_TOKEN
```

O valor do token não foi armazenado em arquivos do repositório, variáveis versionadas ou logs.

## Projetos de teste no SonarQube Cloud

### APAE Backend

```text
Organization Key: teste-apae
Project Key: teste-apae_apae-geral-backend
```

### APAE Frontend

```text
Organization Key: teste-apae
Project Key: teste-apae_apae-geral-frontend
```

### APAE Site Comemorativo

```text
Organization Key: teste-apae
Project Key: teste-apae_site-comemorativo
```

## Validação do backend Java/Maven

O backend do repositório `IFPBEsp/APAE` foi utilizado para validar o workflow reutilizável Maven.

Configuração utilizada no caller:

```yaml
sonar-backend:
  name: Backend Analysis (Maven)
  uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-maven.yml@<commit-validado>
  with:
    project-key: "teste-apae_apae-geral-backend"
    organization: "teste-apae"
    working-directory: "apps/api"
    java-version: "21"
    sonar-host-url: "https://sonarcloud.io"
  secrets:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

O workflow executou:

```text
mvn clean verify sonar:sonar
```

com espera obrigatória pelo Quality Gate.

### Resultado

A análise foi enviada com sucesso ao SonarQube Cloud e o Quality Gate foi processado corretamente.

Durante a primeira execução foi identificado que o projeto de teste havia sido criado com `master` como branch principal, enquanto o repositório utilizava `test/sonarqube-pipeline`.

Após alinhar a branch principal do projeto de teste no SonarQube Cloud, a análise foi reexecutada e o Quality Gate foi validado com sucesso.

## Validação do frontend do APAE

O frontend do repositório `IFPBEsp/APAE` foi utilizado para validar o workflow reutilizável Node.js em um subdiretório:

```text
apps/apae
```

Configuração utilizada:

```yaml
sonar-frontend:
  name: Frontend Analysis (Node)
  uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-node.yml@<commit-validado>
  with:
    project-key: "teste-apae_apae-geral-frontend"
    organization: "teste-apae"
    working-directory: "apps/apae"
    node-version: "22"
    sonar-host-url: "https://sonarcloud.io"
    run-tests: true
  secrets:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### Problema identificado: metadata do scanner

A primeira implementação utilizava uma action separada para consultar o Quality Gate:

```text
SonarSource/sonarqube-quality-gate-action
```

Como o scanner utilizava:

```text
projectBaseDir: apps/apae
```

o arquivo de metadata era criado em:

```text
apps/apae/.scannerwork/report-task.txt
```

enquanto a action procurava inicialmente em:

```text
.scannerwork/report-task.txt
```

O problema foi identificado durante a execução real da pipeline.

### Ajuste aplicado

A abordagem foi simplificada para permitir que o próprio scanner aguarde o Quality Gate:

```text
-Dsonar.qualitygate.wait=true
-Dsonar.qualitygate.timeout=300
```

Com isso:

- deixou de ser necessária uma etapa separada para leitura de `report-task.txt`;
- o workflow Maven e o workflow Node passaram a utilizar comportamento equivalente para Quality Gate;
- a execução passou a falhar diretamente quando o Quality Gate reprova.

### Resultado

Após o ajuste e o alinhamento da branch principal no projeto de teste do SonarQube Cloud, a análise do frontend foi processada corretamente.

## Validação do APAE Site Comemorativo

O repositório `IFPBEsp/apae-site-comemorativo` foi utilizado para validar o workflow Node.js quando o projeto está localizado na raiz do repositório.

Configuração utilizada:

```yaml
sonar-frontend:
  name: Frontend Analysis (Node)
  uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-sonarqube-node.yml@<commit-validado>
  with:
    project-key: "teste-apae_site-comemorativo"
    organization: "teste-apae"
    working-directory: "."
    node-version: "22"
    sonar-host-url: "https://sonarcloud.io"
    run-tests: true
  secrets:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### Problema identificado: scripts de build do pnpm

Durante a instalação das dependências, o pnpm bloqueou scripts de build de pacotes que precisam executar etapas de instalação, incluindo dependências como:

```text
@prisma/client
@prisma/engines
bcrypt
esbuild
prisma
sharp
unrs-resolver
```

O erro observado foi:

```text
ERR_PNPM_IGNORED_BUILDS
```

### Ajuste aplicado

O workflow reutilizável foi ajustado para permitir os scripts necessários durante a instalação no CI:

```text
pnpm install --frozen-lockfile --dangerously-allow-all-builds
```

Esse ajuste foi necessário para permitir a instalação completa das dependências do site comemorativo durante a análise.

## Projetos sem script de teste

O site comemorativo possui `vitest` instalado, mas não possui um script `test` definido no `package.json`.

A primeira implementação tentou executar:

```text
pnpm run test --if-present -- --coverage
```

e o pnpm retornou:

```text
ERR_PNPM_NO_SCRIPT
Missing script: test
```

O reusable foi alterado para verificar explicitamente se o script existe antes da execução.

Comportamento esperado:

```text
script test existe
→ executa testes com cobertura

script test não existe
→ registra mensagem no log
→ ignora cobertura
→ continua para o scan do SonarQube
```

Esse comportamento permite reutilizar o mesmo workflow em projetos com e sem suíte de testes configurada.

## Quality Gate e branches de teste

Durante os testes, projetos recém-criados no SonarQube Cloud utilizaram inicialmente a branch:

```text
master
```

como branch principal.

Como os testes eram executados em:

```text
test/sonarqube-pipeline
```

foi necessário alinhar a branch principal dos projetos de teste no SonarQube Cloud.

Após o primeiro processamento, algumas análises apresentaram temporariamente:

```text
Quality Gate: Not computed
```

Uma execução posterior estabeleceu a baseline necessária e permitiu o cálculo normal do Quality Gate.

## Comportamento final validado

Após os ajustes realizados, o fluxo validado ficou:

```text
push na branch de teste
        ↓
GitHub Actions
        ↓
workflow caller
        ↓
workflow reutilizável do APAE-INFRA
        ↓
checkout
        ↓
setup da runtime
        ↓
instalação de dependências
        ↓
testes com cobertura, quando disponíveis
        ↓
SonarQube Scan
        ↓
upload da análise
        ↓
processamento no SonarQube Cloud
        ↓
Quality Gate
        ↓
sucesso ou falha da pipeline
```

## Ajustes identificados durante a validação

A execução real das pipelines permitiu identificar e corrigir os seguintes pontos:

1. consulta do Quality Gate em projetos Node localizados em subdiretórios;
2. substituição da action separada de Quality Gate pela espera nativa do scanner;
3. suporte a dependências pnpm que necessitam executar scripts de build;
4. suporte a projetos Node sem script `test`;
5. necessidade de alinhar a branch principal de projetos temporários no SonarQube Cloud;
6. validação de projetos Node tanto na raiz quanto em subdiretórios;
7. validação do workflow Maven com Quality Gate obrigatório.

## Resultado

A integração centralizada com SonarQube foi validada com sucesso para:

```text
APAE Backend
→ Java 21
→ Maven
→ subdiretório apps/api

APAE Frontend
→ Node.js 22
→ pnpm
→ subdiretório apps/apae

APAE Site Comemorativo
→ Node.js 22
→ pnpm
→ raiz do repositório
```

Os testes confirmaram que a estratégia de workflows reutilizáveis permite centralizar a lógica de análise estática no `APAE-INFRA`, mantendo os repositórios consumidores responsáveis apenas por informar seus parâmetros específicos.

## Limpeza após a validação

Após a conclusão e registro das evidências, os recursos temporários podem ser removidos:

- branches `test/sonarqube-pipeline`;
- projetos temporários da organização `teste-apae`;
- token utilizado exclusivamente para os testes, caso não seja mais necessário;
- alterações temporárias dos callers que apontavam diretamente para commits do PR de infraestrutura.

Os callers definitivos devem voltar a utilizar a referência estabelecida pela estratégia oficial do projeto, após o merge do workflow reutilizável.
