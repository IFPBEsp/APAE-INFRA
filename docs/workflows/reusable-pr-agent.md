# Workflow reutilizável do PR-Agent

## Objetivo

O workflow `.github/workflows/pr-agent-reusable.yml` centraliza a configuração do PR-Agent utilizada pelos repositórios da APAE.

A proposta é evitar que cada repositório mantenha uma cópia completa da configuração do PR-Agent, concentrando no `APAE-INFRA`:

- versão da imagem utilizada pelo PR-Agent;
- permissões do GitHub Actions;
- filtros de segurança;
- configuração padrão do modelo;
- comportamento de revisão automática;
- controle de concorrência.

Cada repositório de aplicação mantém apenas um workflow caller com as configurações específicas da sua stack.

O PR-Agent é utilizado como ferramenta auxiliar de revisão. Ele não aprova Pull Requests e não bloqueia merge. A revisão e aprovação humana continuam obrigatórias.

---

## Workflow reutilizável

O componente central está localizado em:

```text
.github/workflows/pr-agent-reusable.yml
```

Ele é chamado pelos workflows dos repositórios de aplicação por meio de `workflow_call`.

A referência ao workflow deve utilizar um SHA fixo de commit.

Exemplo:

```yaml
jobs:
  pr-agent:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/pr-agent-reusable.yml@<commit-sha>
```

Evitar referências mutáveis como:

```text
@main
@dev
@master
```

---

## Inputs

### `model`

Modelo LLM utilizado pelo PR-Agent.

Valor padrão:

```text
gemini/gemini-3.6-flash
```

Exemplo:

```yaml
with:
  model: "gemini/gemini-3.6-flash"
```

### `response-language`

Idioma utilizado nas respostas do PR-Agent.

Valor padrão:

```text
pt-BR
```

### `auto-review`

Executa automaticamente a revisão do Pull Request.

Valor padrão:

```text
true
```

### `auto-improve`

Executa automaticamente a geração de sugestões de melhoria.

Valor padrão:

```text
true
```

### `auto-describe`

Controla a geração automática da descrição do Pull Request.

Valor padrão:

```text
false
```

### `num-code-suggestions`

Quantidade máxima de sugestões de código por análise.

Valor padrão:

```text
3
```

O limite reduz ruído nos Pull Requests e segue a configuração validada durante a POC.

### `ignore-globs`

Define os arquivos ignorados durante a análise.

Valor padrão:

```json
["*.lock", "pnpm-lock.yaml", "package-lock.json"]
```

O objetivo é evitar consumo de tokens e sugestões pouco úteis em lockfiles.

### `extra-instructions`

Permite que cada repositório informe contexto adicional para o modelo, como stack, estrutura de diretórios e pontos prioritários da revisão.

Valor padrão:

```text
""
```

Exemplo:

```yaml
extra-instructions: >
  Projeto com backend Java 21 e Spring Boot 3.5.
  Priorizar bugs, validacao de entradas, tratamento de null,
  seguranca e aderencia aos padroes do projeto.
```

---

## Secret

O workflow reutilizável recebe o secret:

```text
LLM_API_KEY
```

O caller deve passar explicitamente a chave configurada no repositório:

```yaml
secrets:
  LLM_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

A configuração preferencial é manter `GEMINI_API_KEY` como secret da organização, liberado somente para os repositórios que utilizam o PR-Agent.

Durante a implementação desta integração não havia acesso administrativo à organização para configurar esse secret globalmente.

Por esse motivo, apenas repositórios que já possuem `GEMINI_API_KEY` conseguem executar efetivamente as chamadas ao modelo.

Os repositórios sem o secret mantêm o caller configurado, mas a geração de reviews e sugestões permanece pendente até que a chave seja disponibilizada.

Nunca adicionar a chave diretamente ao workflow ou a arquivos versionados no repositório.

---

## Permissões

O workflow utiliza somente as permissões necessárias:

```yaml
permissions:
  contents: read
  pull-requests: write
  issues: write
```

Responsabilidades:

```text
contents: read         → leitura do código do Pull Request
pull-requests: write   → publicação de reviews e sugestões
issues: write          → publicação de comentários e comandos em PRs
```

Não é necessário `contents: write`.

---

## Eventos suportados

Os callers utilizam:

```yaml
on:
  pull_request:
    types:
      - opened
      - reopened
      - synchronize
      - ready_for_review

  issue_comment:
    types:
      - created
```

Os eventos de Pull Request permitem executar automaticamente:

```text
/review
/improve
```

O reusable também configura explicitamente as ações consideradas pelo PR-Agent:

```yaml
github_action_config.pr_actions: '["opened", "reopened", "synchronize", "ready_for_review"]'
```

Essa configuração é necessária para que atualizações do Pull Request por novos commits sejam processadas pelo PR-Agent.

---

## Segurança dos comandos por comentário

O evento `issue_comment` é filtrado pelo workflow reutilizável.

O PR-Agent somente executa quando:

- o comentário pertence a um Pull Request;
- o autor não é um bot;
- o `author_association` é um dos seguintes:

```text
OWNER
MEMBER
COLLABORATOR
```

Isso evita que usuários externos utilizem comandos como `/review`, `/improve` ou `/ask` para consumir a cota da API.

---

## Comandos por comentário

O GitHub avalia workflows de `issue_comment` a partir da branch padrão do repositório.

Por isso, comandos como:

```text
/review
/improve
/ask
```

somente podem ser testados depois que o caller `.github/workflows/pr-agent.yml` estiver presente na branch padrão.

Essa limitação é especialmente relevante durante a implantação inicial, porque o workflow existente apenas na branch do Pull Request não é suficiente para receber eventos de comentário.

---

## Pull Requests originados de forks

O workflow utiliza:

```text
pull_request
```

e não:

```text
pull_request_target
```

Secrets do GitHub Actions não são disponibilizados para workflows executados em Pull Requests originados de forks.

Para evitar tentativa de execução sem credenciais, o reusable ignora eventos em que:

```text
github.event.pull_request.head.repo.fork == true
```

Nesse cenário, o PR-Agent não é executado e o workflow não utiliza o secret do provedor.

A análise deve ser feita por revisão humana ou após o código estar disponível em uma branch interna autorizada.

---

## Concorrência

O workflow utiliza um grupo de concorrência por repositório e número do Pull Request.

Novas execuções cancelam execuções anteriores ainda em andamento.

Isso evita consumo desnecessário de cota quando vários commits são enviados rapidamente para o mesmo Pull Request.

---

## Configuração específica por repositório

Um arquivo `.pr_agent.toml` continua sendo suportado pelo PR-Agent.

Entretanto, ele não é necessário para o funcionamento padrão desta integração.

Configurações específicas por repositório devem ser adicionadas apenas quando houver uma necessidade concreta que não possa ser atendida pelos inputs do workflow reutilizável.

---

## Caller

Exemplo de caller:

```yaml
name: PR-Agent

on:
  pull_request:
    types:
      - opened
      - reopened
      - synchronize
      - ready_for_review

  issue_comment:
    types:
      - created

jobs:
  pr-agent:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/pr-agent-reusable.yml@<commit-sha>

    with:
      model: "gemini/gemini-3.6-flash"
      response-language: "pt-BR"
      auto-review: true
      auto-improve: true
      auto-describe: false
      num-code-suggestions: 3
      ignore-globs: '["*.lock", "pnpm-lock.yaml", "package-lock.json"]'

      extra-instructions: >
        Descrever aqui a stack e os pontos prioritarios
        para revisao deste repositorio.

    secrets:
      LLM_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

---

## Repositórios integrados

### `IFPBEsp/APAE`

Stack informada ao PR-Agent:

```text
Java 21 / Spring Boot 3.5 em apps/api
Next.js em apps/apae
Next.js em apps/management-app
```

Status da validação:

```text
caller configurado
workflow reutilizável executado
auto_review validado
auto_improve validado
evento synchronize validado
```

A validação foi realizada em um Pull Request real e o PR-Agent identificou problemas de código, incluindo tratamento de `null`.

O teste de comandos por `issue_comment` permanece pendente até que o caller esteja disponível na branch padrão do repositório.

### `IFPBEsp/APAE-atendimento`

Stack informada ao PR-Agent:

```text
Java 21 / Spring Boot 3.5 em backend/atendimento
Next.js 16 em frontend/atendimento-app
```

Status:

```text
caller configurado
workflow disparado com sucesso
geração de review pendente por ausência de GEMINI_API_KEY
```

### `IFPBEsp/APAE-gestao-escolar`

Branch padrão durante a implementação:

```text
dev-database
```

Stack informada:

```text
Java 21 / Spring Boot 3.3 em api
Next.js 16 em app
```

Status:

```text
caller configurado
workflow disparado
geração de review pendente por ausência de GEMINI_API_KEY
```

### `IFPBEsp/apae-site-comemorativo`

Stack informada:

```text
Next.js 15
Prisma
aplicação na raiz do repositório
```

Status:

```text
caller configurado
workflow disparado
geração de review pendente por ausência de GEMINI_API_KEY
```

---

## Validação do piloto

O piloto realizado no repositório `APAE` confirmou o funcionamento da configuração centralizada.

Foram validados:

```text
modelo Gemini
respostas em pt-BR
auto_review
auto_improve
limite de 3 sugestões
evento synchronize
publicação de comentários no Pull Request
```

Durante a validação foi identificado que apenas habilitar o evento `synchronize` no caller não era suficiente.

Também foi necessário configurar no reusable:

```yaml
github_action_config.pr_actions: '["opened", "reopened", "synchronize", "ready_for_review"]'
```

Sem essa configuração o workflow era iniciado, mas o PR-Agent registrava:

```text
Skipping action: synchronize
```

Após a correção, a revisão passou a ser executada normalmente.

---

## Comportamento quando o modelo falha

O PR-Agent pode capturar internamente falhas do provedor LLM sem fazer o job do GitHub Actions terminar com erro.

Durante as validações em repositórios sem `GEMINI_API_KEY`, o workflow foi iniciado e o container foi executado, mas o PR-Agent publicou:

```text
Failed to generate code suggestions for PR
```

mesmo com o job do GitHub Actions concluído como `success`.

Por isso, um check verde do workflow indica que a execução do PR-Agent ocorreu, mas não deve ser usado isoladamente como confirmação de que o modelo gerou uma revisão válida.

A validação deve considerar também os logs da execução e os comentários publicados no Pull Request.

---

## Uso de dados pelo provedor

O modelo definido atualmente é:

```text
gemini/gemini-3.6-flash
```

utilizando uma chave do Google AI Studio.

Antes de liberar a configuração de forma definitiva para todos os repositórios, o time deve validar as condições de uso de dados aplicáveis ao plano utilizado.

Código enviado ao modelo pode incluir trechos de Pull Requests e contexto necessário para revisão.

Não devem existir dados reais de pacientes, credenciais, secrets ou outros dados sensíveis em código, migrations, seeds, fixtures ou diffs enviados para análise.

A validação e aceite desse uso pelo time permanecem como requisito operacional da integração.

---

## CodeRabbit

O CodeRabbit ainda está instalado em parte dos repositórios e chegou a publicar comentários durante a implantação do PR-Agent.

A remoção requer permissões administrativas na organização que não estavam disponíveis durante esta implementação.

A desinstalação ou remoção do acesso do CodeRabbit aos repositórios permanece como pendência administrativa.

Depois da remoção, o PR-Agent deve permanecer como a ferramenta automatizada de apoio à revisão de Pull Requests.

---

## Limitações atuais

As seguintes pendências não impedem a configuração dos callers, mas ainda precisam ser concluídas para atender integralmente aos critérios de aceite da issue:

```text
disponibilizar GEMINI_API_KEY nos repositórios sem o secret
validar review real nos repositórios restantes
testar pelo menos um comando via issue_comment
validar com o time o uso de dados pelo provedor
remover o CodeRabbit dos repositórios
garantir que os callers estejam mergeados nas branches padrão
```

---

## Referências

POC e estudo inicial:

```text
IFPBEsp/APAE#899
IFPBEsp/APAE#904
```

Issue da implementação definitiva:

```text
IFPBEsp/APAE-INFRA#51
```
