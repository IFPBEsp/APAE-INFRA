# Workflows do GitHub Actions

Este diretório contém os pipelines de Integração Contínua (CI) e Entrega Contínua (CD) do repositório **APAE-INFRA**.

## Pipelines disponíveis

| Workflow | Arquivo | Gatilho | Descrição |
| --- | --- | --- | --- |
| **Markdown Lint** | [`markdown-lint.yml`](markdown-lint.yml) | PRs alterando `**/*.md`, pushes em `main`/`dev` | Validação de formatação e boas práticas em arquivos Markdown via `markdownlint-cli2` |

## Referências

* [Padronização de Markdown](../../docs/padronizacao-markdown.md)
* [Padronização de Pull Requests](../../docs/padronizacao-pull-requests.md)
