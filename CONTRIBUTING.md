# Como contribuir

> Válido para o repositório **APAE-INFRA**. A adoção deste padrão nos repositórios de aplicação (APAE, APAE-atendimento, APAE-gestao-escolar, apae-site-comemorativo) fica a critério de cada squad.

**Sumário:** [Antes de começar](#antes-de-começar) · [Branch](#branch) · [Commits](#commits) · [Pull Request](#pull-request) · [Revisão](#revisão) · [Referências](#referências)

## Antes de começar

Toda mudança neste repositório parte de uma issue. Se o que você quer fazer ainda não tem uma issue, crie uma antes de abrir a branch.

## Branch

Crie a branch a partir da própria issue (botão "Create a branch"), seguindo o padrão:

```
{numero-da-issue}-{titulo-da-issue-em-kebab-case}
```

Este é o mesmo formato que o GitHub já gera automaticamente ao criar uma branch a partir de uma issue.

**Exemplo:** a issue `[DOCS] Padronizar mensagens de commit` gerou a branch `5-padroniza-mensagens-de-commit`.

## Commits

Seguimos o modelo [Conventional Commits](https://www.conventionalcommits.org/pt-br/), com mensagens escritas em **português**.

#### Formato

```
tipo: descrição
```

#### Tipos permitidos

| Tipo | Quando usar | Exemplo |
|---|---|---|
| `feat` | Nova funcionalidade | `feat: adiciona pipeline de deploy do argocd` |
| `fix` | Correção de bug | `fix: corrige path do values.yaml do grafana` |
| `docs` | Mudanças de documentação | `docs: adiciona padronizacao de mensagens de commit` |
| `refactor` | Mudança de código que não corrige bug nem adiciona funcionalidade | `refactor: reorganiza modulos do terraform` |
| `test` | Adição ou ajuste de testes | `test: adiciona teste de validacao do manifesto k8s` |
| `chore` | Tarefas de manutenção que não alteram código de produção | `chore: atualiza versao do provider aws no terraform` |
| `ci` | Mudanças em pipelines/integração contínua | `ci: adiciona workflow de lint dos arquivos yaml` |
| `build` | Mudanças que afetam o processo de build ou dependências | `build: atualiza imagem base do dockerfile` |

#### Regras da descrição

- Modo imperativo (ex: `adiciona`, não `adicionado` ou `adicionando`);
- Tudo em minúsculo;
- Sem ponto final;
- Sem caracteres especiais, além dos dois-pontos após o tipo;
- Sem acentuação (ex: `documentacao`, não `documentação`).

## Pull Request

#### Vínculo com a issue

Todo PR deve estar vinculado a uma issue: preencha o campo `Issue: {issue_link}` da seção **Tarefas Relacionadas** do template.

#### Título

Formato `[TIPO] Descrição`:

- `[TIPO]` — tag em caixa alta correspondente ao tipo da issue vinculada (ex: `[DOCS]`, `[CHORE]`, `[FEAT]`, `[FIX]`...), no mesmo formato usado no título da issue;
- `Descrição` — exatamente a mesma descrição usada no título da issue vinculada.

**Exemplo:** issue `[DOCS] Padronizar mensagens de commit` → PR `[DOCS] Padronizar mensagens de commit`.

#### Checklist antes de pedir revisão

- [ ] Build/pipeline passando (quando aplicável);
- [ ] Testes executados (quando aplicável);
- [ ] Evidências anexadas na seção **Evidências** do template (prints, logs, capturas de tela, etc.);
- [ ] Campo `Issue:` do template preenchido.

## Revisão

- Mínimo de **1 aprovação** de outro membro do time de infraestrutura antes do merge;
- Quem abre o PR não pode aprovar o próprio PR;
- O merge só pode ser feito depois que todos os checks obrigatórios (CI) passarem e a aprovação mínima for obtida.

## Referências

- Template de PR: [`.github/pull_request_template.md`](.github/pull_request_template.md)
- [Conventional Commits](https://www.conventionalcommits.org/pt-br/)