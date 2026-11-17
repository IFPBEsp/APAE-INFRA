# Workflow reutilizável de CI para backends Java/Maven

## Objetivo

O workflow `.github/workflows/java-backend-ci.yml` centraliza a validação de backends Java da APAE que utilizam Java 21, Spring Boot e Maven Wrapper.

Ele foi criado para ser chamado por outros repositórios por meio de `workflow_call` e executa, em Pull Requests:

- configuração do JDK Temurin com cache de dependências Maven;
- compilação e execução dos testes com o Maven Wrapper;
- verificação da disponibilidade do Docker para testes com Testcontainers;
- geração e publicação do relatório de cobertura JaCoCo;
- publicação de um resumo de cobertura no `GITHUB_STEP_SUMMARY`;
- publicação do relatório Surefire de forma legível no Pull Request;
- verificação opcional de cobertura mínima de linhas.

O workflow não faz deploy, não publica imagem e não escreve no repositório.

## Localização

```text
.github/workflows/java-backend-ci.yml
```

## Inputs

| Input | Obrigatório | Tipo | Padrão | Descrição |
| --- | --- | --- | --- | --- |
| `working-directory` | Sim | `string` | — | Diretório do backend Maven, relativo à raiz do repositório. Não pode ser absoluto nem conter `..` |
| `java-version` | Não | `string` | `21` | Versão do JDK Temurin utilizada no build |
| `maven-args` | Não | `string` | `verify` | Argumentos executados pelo Maven Wrapper, após `./mvnw -B` |
| `coverage-report-path` | Não | `string` | `target/site/jacoco/jacoco.xml` | Caminho do relatório XML do JaCoCo, relativo ao `working-directory` |
| `coverage-min` | Não | `string` | vazio | Cobertura mínima de linhas em percentual. Vazio desabilita a verificação |

### `working-directory`

O diretório precisa conter `pom.xml` e `mvnw`. O workflow valida esses arquivos antes de executar o build e torna o `mvnw` executável quando necessário.

Exemplo para um backend na raiz do repositório:

```yaml
with:
  working-directory: "."
```

Exemplo para um monorepo:

```yaml
with:
  working-directory: "backends/atendimento"
```

### `java-version`

O valor padrão é `21`. O workflow usa a distribuição Temurin e o cache de dependências Maven do `actions/setup-java`.

```yaml
with:
  java-version: "21"
```

### `maven-args`

O valor padrão é `verify`. O workflow executa `./mvnw -B` seguido dos argumentos informados.

```yaml
with:
  maven-args: "clean verify"
```

Os argumentos são separados por espaços. O input aceita múltiplas linhas, e todas as linhas informadas são consideradas. Evite argumentos que dependam de espaços dentro do mesmo valor.

### `coverage-report-path`

Caminho do XML gerado pelo JaCoCo, relativo ao `working-directory`.

O valor padrão corresponde a um projeto Maven simples:

```text
target/site/jacoco/jacoco.xml
```

Para um relatório agregado em projeto multi-módulo, informe o caminho correspondente:

```yaml
with:
  coverage-report-path: "target/site/jacoco-aggregate/jacoco.xml"
```

Se o arquivo não existir após a execução do Maven, o workflow tenta gerar o relatório com:

```text
./mvnw -B jacoco:report
```

O projeto precisa ter o JaCoCo configurado para que o relatório seja gerado.

### `coverage-min`

Percentual mínimo de cobertura de linhas. O valor pode ser informado com ou sem o símbolo `%`, por exemplo `80`, `80.5` ou `80,5`.

```yaml
with:
  coverage-min: "80"
```

Quando o input está vazio, a verificação de cobertura mínima não é executada.

Quando o input está preenchido e o relatório JaCoCo não é encontrado, o job falha, pois não é possível validar o limite.

## Como aderir

Crie um workflow no repositório de aplicação, por exemplo `.github/workflows/java-backend-ci.yml`:

```yaml
name: Java Backend CI

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  java-ci:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/java-backend-ci.yml@<commit-sha>
    with:
      working-directory: "."
      java-version: "21"
      maven-args: "verify"
      coverage-report-path: "target/site/jacoco/jacoco.xml"
      coverage-min: "80"
```

Substitua `<commit-sha>` pelo SHA completo de um commit do APAE-INFRA. Evite referências mutáveis como `@main`, `@dev` ou `@v1`.

Como o workflow reutilizável publica comentários automáticos no Pull Request, o token precisa das permissões contents: read e pull-requests: write. A permissão pull-requests: write é necessária para criar ou atualizar o comentário com o relatório Surefire. Sem ela, a execução é rejeitada antes de iniciar, porque o workflow reutilizável declara essa permissão.

### Restringindo a execução por caminhos

Para evitar execuções desnecessárias, o repositório chamador pode limitar o gatilho aos arquivos do backend:

```yaml
on:
  pull_request:
    paths:
      - "pom.xml"
      - "mvnw"
      - ".mvn/**"
      - "src/**"
```

Em monorepos, ajuste os caminhos para incluir o diretório do backend.

## Cobertura JaCoCo

O workflow publica o relatório de cobertura de duas formas:

- artefato `jacoco-coverage-<diretório-slugificado>-jdk<java>-<hash>`, com o XML e o diretório do relatório;
- tabela no resumo do workflow, com cobertura de instruções, ramos, linhas, complexidade, métodos e classes.

O nome do artefato mantém o caminho legível, slugificado (por exemplo, `services/api` vira `services-api`) e com a versão do Java, e ainda recebe um sufixo de oito caracteres calculado a partir do `working-directory` completo. Como o `upload-artifact` v4 exige nomes distintos no mesmo run, o sufixo evita que dois backends cujos caminhos colidem após a slugificação, como `services/api` e `services-api`, disputem o mesmo artefato.

O artefato é mantido por 14 dias.

A verificação de `coverage-min` usa a cobertura de linhas do contador `LINE` do relatório JaCoCo e compara o valor exato, sem arredondamento prévio. Quando a cobertura reprova, o log informa o percentual com quatro casas decimais e a contagem de linhas cobertas e perdidas, para que diferenças pequenas, como `99.9950%` contra um mínimo de `100%`, fiquem evidentes.

## Relatório Surefire

O workflow procura arquivos `**/target/surefire-reports/TEST-*.xml` dentro do `working-directory`.

Todo comentário identifica a execução que o produziu, com o backend (`working-directory`), a versão do Java, o SHA do commit (`GITHUB_SHA`) e o link direto para a execução do GitHub Actions, montado com `CI_SERVER_URL` (ou `GITHUB_SERVER_URL`, quando a primeira não existe), `GITHUB_REPOSITORY` e `GITHUB_RUN_ID`.

Quando há relatórios, ele publica no Pull Request um comentário com:

- identificação da execução (backend, Java, commit e link da execução);
- status geral dos testes;
- total de testes, falhas, erros, testes ignorados e tempo;
- tabela por suíte;
- lista das falhas encontradas.

Quando a compilação falha antes de gerar os XMLs do Surefire, nenhum relatório é produzido. Nesse caso o workflow atualiza o mesmo comentário com o aviso de que nenhum relatório Surefire foi gerado nesta execução e a build pode ter falhado antes de gerar os XMLs, acompanhado da mesma identificação: backend, versão do Java, commit e link da execução. Assim, o Pull Request não continua exibindo o resultado antigo do commit anterior. Esse aviso também é enviado ao `GITHUB_STEP_SUMMARY`.

O comentário é atualizado nas execuções seguintes por meio de um marcador fixo, evitando comentários duplicados.

Antes de publicar, o workflow consulta o Pull Request e compara o SHA de origem do run com o HEAD atual do PR. Quando um run antigo termina depois de um commit mais novo, ele é ignorado: o comentário não é criado nem atualizado e o motivo fica registrado no log da execução, preservando o relatório do commit vigente.

A publicação é interrompida sem tocar no comentário existente quando o SHA de origem do run está ausente ou quando a consulta à API do GitHub falha (por exemplo, um erro 503). A mesma checagem de HEAD é repetida logo antes de criar ou editar o comentário, cobrindo mudanças de ponta que ocorram durante a listagem dos comentários: se o HEAD mudou nesse intervalo, nada é publicado.

A publicação do comentário ocorre apenas em eventos `pull_request`. Em execuções por `push` ou por outros eventos, o resumo Surefire continua disponível no `GITHUB_STEP_SUMMARY`, mas nenhum comentário é criado.

## Testcontainers

O workflow usa `ubuntu-latest`, que disponibiliza Docker no runner. Antes do build, ele executa `docker version` e `docker info` para falhar cedo caso o Docker não esteja disponível.

Nenhuma configuração adicional é necessária para testes que usam Testcontainers com o Docker local do runner.

## Segurança e permissões

O workflow adota as seguintes medidas:

- todas as GitHub Actions são fixadas por SHA completo, não por tag ou versão mutável;
- o checkout usa `persist-credentials: false`;
- as permissões declaradas são `contents: read` e `pull-requests: write`, necessárias para o checkout e para a publicação do comentário Surefire no Pull Request;
- os inputs de caminho são validados para rejeitar caminhos absolutos e referências com `..`;
- o workflow não recebe nem utiliza secrets adicionais.

As versões das actions podem ser atualizadas pelo Renovate ou manualmente, sempre mantendo a referência por SHA.

## Limitações

- O relatório Surefire só é comentado no PR em eventos `pull_request`.
- Pull Requests de forks podem ter o token com permissão reduzida; nesse caso, o workflow avisa e não falha por causa do comentário.
- A cobertura depende da configuração do JaCoCo no projeto.
- O workflow não faz deploy nem publicação de imagem.
