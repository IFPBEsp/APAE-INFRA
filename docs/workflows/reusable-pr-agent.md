# Workflow reutilizável do PR-Agent

## Objetivo

O workflow `.github/workflows/pr-agent-reusable.yml` centraliza a configuração do PR-Agent utilizada pelos repositórios da APAE.

A centralização evita que cada repositório mantenha uma cópia completa da configuração do PR-Agent, concentrando no `APAE-INFRA`:

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
false
```

O `/improve` permanece disponível sob demanda por comentário autorizado no Pull Request.
A execução automática foi desativada para reduzir chamadas e consumo de tokens nos quatro produtos.

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

Esse parâmetro limita a quantidade de sugestões apresentadas pelo `/improve` e reduz ruído nos Pull Requests. **Não limita a quantidade de chamadas ao modelo nem os tokens consumidos pelo `/review`.**

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

A configuração atual utiliza **quatro projetos distintos no Google AI Studio**, um para cada produto, e uma chave `GEMINI_API_KEY` cadastrada como secret em cada repositório. Cada caller passa sua chave ao parâmetro `LLM_API_KEY` do reusable.

O cadastro por repositório permite isolar credenciais e acompanhar o uso individualmente. As cotas da API Gemini são aplicadas por projeto, mas a separação não garante maior disponibilidade do modelo nem elimina outras restrições do provedor.

Os quatro repositórios já tiveram o `/review` validado com suas respectivas chaves. Como utilizam chaves diferentes, **não substituir os quatro secrets por uma única chave compartilhada** sem reavaliar a estratégia de isolamento.

As chaves não devem aparecer em logs, comentários ou arquivos versionados.

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

Os eventos de Pull Request executam automaticamente **somente**:

```text
/review
```

Os comandos `/improve` e `/ask` permanecem disponíveis sob demanda por `issue_comment` de usuário autorizado, após o caller estar presente na branch padrão.

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

Exemplo de caller simplificado, que utiliza os valores padrão de `model`, `response-language`, `auto-review`, `auto-improve`, `auto-describe`, `num-code-suggestions` e `ignore-globs` definidos no reusable. Substitua `<commit-sha>` pelo SHA fixo efetivamente validado:

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
auto_review validado e publicado
auto_improve automatico desativado
fallback Gemini validado
evento synchronize validado
```

A POC inicial identificou problemas no código de teste Java, incluindo tratamento de `null`. A validação da integração definitiva ocorreu em um Pull Request real (APAE #1003), com publicação do `/review`; após um erro `503` no modelo principal, o fallback gerou a revisão e atualizou o comentário persistente.

O teste de comandos por `issue_comment` ainda não foi confirmado nesta atualização; para executá-lo, o caller precisa estar disponível na branch padrão do repositório.

### `IFPBEsp/APAE-atendimento`

Stack informada ao PR-Agent:

```text
Java 21 / Spring Boot 3.5 em backend/atendimento
Next.js 16 em frontend/atendimento-app
```

Status:

```text
caller configurado
GEMINI_API_KEY individual configurada
/review automatico validado e publicado
/improve automatico desativado
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
GEMINI_API_KEY individual configurada
/review automatico validado e publicado
/improve automatico desativado
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
GEMINI_API_KEY individual configurada
/review automatico validado e publicado
/improve automatico desativado
```

---

## Validação do piloto

O piloto realizado no repositório `APAE` confirmou o funcionamento da configuração centralizada.

Foram validados:

```text
/review automatico nos quatro repositorios
chaves individuais de quatro projetos Google AI Studio
respostas em pt-BR
/improve automatico desativado
evento synchronize no APAE Geral
publicacao de comentarios de revisao
fallback para outro modelo Gemini no APAE Geral
```

O limite de três sugestões pertence ao comando `/improve`; como ele não é executado automaticamente na configuração atual, esse parâmetro não deve ser interpretado como limite de consumo de tokens. A POC original testou `/improve`, mas o comportamento atual é diferente.

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

O PR-Agent utiliza o modelo principal `gemini/gemini-3.6-flash` e está configurado para tentar `gemini/gemini-3.5-flash-lite` como fallback, sem recorrer ao fallback padrão para OpenAI que falhava com a chave fictícia `dummy_key`.

Configuração aplicada no `env` do reusable:

```yaml
config.model: ${{ inputs.model }}
config.fallback_models: '["gemini/gemini-3.5-flash-lite"]'
```

Durante a validação do APAE Geral, o Gemini principal retornou `503 UNAVAILABLE`, indicando alta demanda temporária. O PR-Agent tentou o fallback Gemini, gerou uma revisão válida e atualizou o comentário persistente no PR #1003.

Esse erro **não é prova de esgotamento de cota**: `503` indica indisponibilidade do serviço/modelo; `429 RESOURCE_EXHAUSTED` é o erro típico de limite excedido. O fallback melhora a tolerância à indisponibilidade de um modelo, mas usa a cota do mesmo projeto e não garante execução bem-sucedida em todas as condições.

O PR-Agent pode capturar internamente falhas de inferência sem fazer o job do GitHub Actions terminar com erro. Por isso, um check verde **não comprova**, isoladamente, que uma revisão foi gerada e publicada.

Verificar sempre os logs, a resposta do modelo e a existência ou atualização do comentário do PR-Agent no Pull Request.

### Acompanhamento de cotas

A validação funcional nos quatro repositórios foi concluída, mas **a capacidade para muitos PRs abertos ou atualizados diariamente ainda não foi medida**. Durante o uso real, acompanhar no Google AI Studio, por projeto:

- quantidade de revisões disparadas e efetivamente publicadas;
- RPM, TPM e RPD disponíveis e utilizados;
- ocorrências de `429`, `503` e acionamentos de fallback;
- tamanho dos diffs e frequência de eventos `synchronize`.

`auto-improve: false` reduz chamadas automáticas, mas `/review` ainda consome tokens e pode realizar mais de uma chamada por execução. O mecanismo de `concurrency` cancela execuções antigas ainda em andamento, sem recuperar cota já consumida. Não há garantia documentada de suporte a 15 PRs simultâneos.

---

## Uso de dados pelo provedor

O modelo principal é `gemini/gemini-3.6-flash`, com fallback `gemini/gemini-3.5-flash-lite`, utilizando uma chave do respectivo projeto no Google AI Studio.

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
monitorar cotas e confiabilidade com PRs reais dos quatro produtos
testar pelo menos um comando via issue_comment
validar com o time o uso de dados pelo provedor
remover o CodeRabbit dos repositórios
confirmar que os callers estejam mergeados nas branches padrão
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
