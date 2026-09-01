# Padronização de Abertura de Pull Requests

> Esta padronização é válida apenas para o repositório APAE-INFRA. A adoção do mesmo padrão nos repositórios de aplicação (APAE, APAE-atendimento, APAE-gestao-escolar, apae-site-comemorativo) não faz parte deste documento e fica a critério de cada squad responsável.

## Convenção de nomenclatura de branches

As branches devem seguir o padrão:

```text
{numero-da-issue}-{titulo-da-issue-em-kebab-case}
```

Este é o mesmo formato que o GitHub já gera automaticamente ao criar uma branch a partir de uma issue (botão **Create a branch**, no menu lateral da issue).

**Exemplo:** a issue `[DOCS] Padronizar mensagens de commit` gerou a branch `5-padroniza-mensagens-de-commit`.

## Vínculo entre PR e Issue

Todo PR deve estar vinculado a uma issue. O campo `Issue: {issue_link}` da seção **Tarefas Relacionadas** do template de PR deve sempre ser preenchido com o link da issue correspondente.

## Título do PR

O título do PR deve seguir o padrão:

```text
[TIPO] Descrição
```

* `[TIPO]` — tag em caixa alta correspondente ao tipo da issue vinculada (ex: `[DOCS]`, `[CHORE]`, `[FEAT]`, `[FIX]`...), no mesmo formato usado no título da issue;
* `Descrição` — exatamente a mesma descrição usada no título da issue vinculada ao PR.

**Exemplo:** issue `[DOCS] Padronizar mensagens de commit` → PR `[DOCS] Padronizar mensagens de commit`.

## Checklist mínimo antes de solicitar revisão

Antes de marcar o PR como pronto para revisão, verificar:

* Build/pipeline passando (incluindo lint de Markdown via CI);
* Testes executados (quando aplicável);
* Evidências anexadas na seção **Evidências** do template (prints, logs, capturas de tela, etc.);
* Campo `Issue:` do template preenchido.

## Política de revisão e aprovação

* Mínimo de **1 aprovação** de outro membro do time de infraestrutura antes do merge;
* Quem abre o PR não pode aprovar o próprio PR;
* O merge só pode ser feito depois que todos os checks obrigatórios (CI) passarem e a aprovação mínima for obtida.

## Referências

* Template de PR: [`.github/pull_request_template.md`](../.github/pull_request_template.md)
* [Padronização de Markdown](padronizacao-markdown.md)
* [Padronização de mensagens de commit](padronizacao-commits.md)
