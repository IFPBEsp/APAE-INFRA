# Padronização de Markdown

Este documento define o padrão de formatação e lint de arquivos Markdown (`.md`) adotado no repositório **APAE-INFRA**, utilizando o `markdownlint-cli2`.

> Esta padronização é válida apenas para o repositório APAE-INFRA. A adoção do mesmo padrão nos repositórios de aplicação (APAE, APAE-atendimento, APAE-gestao-escolar, apae-site-comemorativo) não faz parte deste documento e fica a critério de cada squad responsável.

## Objetivo

Garantir consistência visual, hierarquia correta de cabeçalhos, formatação de listas, tabelas e blocos de código em todos os arquivos de documentação do repositório, prevenindo degradação da qualidade com múltiplos contribuidores.

## Ferramenta utilizada

A validação é feita através do [markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2), uma CLI rápida baseada na biblioteca `markdownlint`.

## Configuração de regras

As regras de lint estão versionadas no arquivo [`.markdownlint.yml`](../.markdownlint.yml) na raiz do repositório.

Principais diretrizes configuradas:

* **`default: true`**: todas as regras padrão do markdownlint estão ativas;
* **`MD013/line-length: false`**: desativação do limite rígido de 80 caracteres por linha para facilitar links longos, tabelas e parágrafos contínuos;
* **`MD024/no-duplicate-heading: { siblings_only: true }`**: permite títulos repetidos caso pertençam a seções ou níveis superiores distintos;
* **`MD025/single-title/single-h1: { front_matter_title: "" }`**: evita falsos positivos em templates de issues/PRs com front-matter YAML;
* **`MD033/no-inline-html: false`**: permite o uso pontual de tags HTML quando necessário (ex: `<kbd>`, `<details>`, `<img>`).

## Execução local

Você pode validar os arquivos localmente antes de abrir um Pull Request:

### 1. Verificar erros de lint

```bash
npx markdownlint-cli2 "**/*.md"
```

### 2. Corrigir erros automaticamente (onde suportado)

```bash
npx markdownlint-cli2 --fix "**/*.md"
```

## Integração Contínua (CI)

Existe um workflow do GitHub Actions configurado em [`.github/workflows/markdown-lint.yml`](../.github/workflows/markdown-lint.yml) que:

* É disparado automaticamente em qualquer Pull Request que altere arquivos `**/*.md` ou a configuração de lint;
* Executa a validação usando a action oficial `DavidAnson/markdownlint-cli2-action`;
* Falha o status do PR caso seja encontrado qualquer erro de formatação, impedindo o merge de documentação fora dos padrões.

## Referências

* [Repositório do markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2)
* [Regras do markdownlint](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md)
* [Padronização de abertura de Pull Requests](padronizacao-pull-requests.md)
