# Como contribuir

## Antes de começar

Toda mudança neste repositório parte de uma issue. Se o que você quer fazer ainda não tem uma issue, crie uma antes de abrir a branch.

## Branch

Crie a branch a partir da própria issue (botão "Create a branch"), seguindo o padrão:

```
{numero-da-issue}-{titulo-da-issue-em-kebab-case}
```

Exemplo: `9-criar-readme-explicando-proposito-e-estrutura-do-repositorio`

## Commits

Siga o padrão descrito em [docs/padronizacao-commits.md](docs/padronizacao-commits.md), baseado em Conventional Commits. Resumo rápido:

- Mensagens em português;
- Tipo + descrição no imperativo, minúsculo, sem ponto final: `docs: criar readme do repositorio`;
- Tipos permitidos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `build`.

## Pull Request

Siga o padrão descrito em [docs/padronizacao-pull-requests.md](docs/padronizacao-pull-requests.md). Resumo rápido:

- Título no formato `[ISSUE] Descrição`, com `Descrição` igual ao título da issue vinculada;
- Preencha o campo `Issue: {issue_link}` do template de PR;
- Antes de pedir revisão, confirme que o build está passando e que os testes foram executados (com evidência anexada, se fizer sentido).

## Revisão

O PR precisa de pelo menos uma aprovação antes do merge. Só quem revisou pode aprovar; quem abriu o PR não aprova o próprio trabalho.
