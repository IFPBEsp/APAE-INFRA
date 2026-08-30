# Padronização de Mensagens de Commit

Este documento define o padrão de mensagens de commit adotado no repositório **APAE-INFRA**, baseado no modelo [Conventional Commits](https://www.conventionalcommits.org/pt-br/).

> Esta padronização é válida apenas para o repositório APAE-INFRA. A adoção do mesmo padrão nos repositórios de aplicação (APAE, APAE-atendimento, APAE-gestao-escolar, apae-site-comemorativo) não faz parte deste documento e fica a critério de cada squad responsável.

## Formato da mensagem

```
tipo: descrição
```

* **tipo:** uma das categorias definidas na seção [Tipos de commit permitidos](#tipos-de-commit-permitidos);
* **descrição:** resumo da mudança, seguindo as regras da seção [Formato da descrição](#formato-da-descrição).

## Idioma

As mensagens de commit devem ser escritas em **português**.

## Tipos de commit permitidos

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

## Formato da descrição

* Modo imperativo (ex: `adiciona`, não `adicionado` ou `adicionando`);
* Tudo em minúsculo;
* Sem ponto final;
* Sem caracteres especiais, além dos dois-pontos após o tipo;
* Sem acentuação (ex: `documentacao`, não `documentação`).

## Referência

* [Conventional Commits](https://www.conventionalcommits.org/pt-br/)
