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

## Validação automática (commitlint)
 
A adesão a este padrão passou a ser **verificada automaticamente** em cada Pull Request, usando o [commitlint](https://commitlint.js.org/) com o preset `@commitlint/config-conventional`.
 
### Regras configuradas
 
As regras estão definidas em [`commitlint.config.js`](../commitlint.config.js), na raiz do repositório. Além do preset padrão, foram adicionadas/ajustadas as seguintes regras para refletir os tipos definidos neste documento:
 
| Regra | Configuração | Efeito |
|---|---|---|
| `type-enum` | `feat, fix, docs, refactor, test, chore, ci, build` | Só aceita os tipos listados na seção [Tipos de commit permitidos](#tipos-de-commit-permitidos) |
| `type-case` | `lower-case` | O tipo deve estar em minúsculo (ex: `feat`, não `Feat`) |
| `subject-case` | `lower-case` | A descrição deve estar em minúsculo |
| `subject-full-stop` | proibido ponto final | A descrição não pode terminar com `.` |
| `subject-exclamation-mark` | proibido `!` | A descrição não pode terminar com `!` |
 
> Observação: o preset `@commitlint/config-conventional` valida a estrutura `tipo: descrição`, mas não impõe idioma nem acentuação. A regra de "sem acentuação" e "modo imperativo" ainda dependem de revisão humana/atenção de quem commita — o commitlint não cobre esses dois pontos.
 
### Onde a validação roda
 
A validação **não** roda localmente por padrão (nenhum hook obrigatório é instalado). Ela roda em um workflow dedicado do GitHub Actions (`.github/workflows/commitlint.yml`), disparado nos eventos `opened`, `synchronize` e `reopened` de Pull Requests.
 
O workflow usa a action [`wagoid/commitlint-github-action`](https://github.com/wagoid/commitlint-github-action), que valida **todo o range de commits do PR** (do commit-base até o topo da branch), não apenas o último commit. Isso garante que, mesmo em um PR com vários commits, nenhum deles escape da validação.
 
Esse desenho foi escolhido para que quem só mexe com Terraform, YAML ou Dockerfile não precise instalar Node.js nem configurar nada localmente — o check roda inteiramente no CI.
 
### Hook local (opcional, via Husky)
 
Não é obrigatório instalar nada localmente para contribuir. Quem tiver Node.js instalado e quiser feedback imediato (antes mesmo de abrir o PR) pode, opcionalmente, configurar um hook local com [Husky](https://typicode.github.io/husky/) + commitlint. Essa configuração é individual e não faz parte da árvore de dependências obrigatória do projeto.
 
### O que acontece quando um commit falha na validação
 
* O check `commitlint` no Pull Request falha (fica vermelho), com o log apontando qual commit e qual regra foi violada;
* Enquanto o check estiver marcado como **obrigatório** nas regras de proteção da branch principal, o PR não pode ser mesclado até a mensagem ser corrigida;
* Para corrigir:
  * **Se for o último commit:**
```bash
    git commit --amend -m "tipo: descrição corrigida"
    git push --force-with-lease
```
  * **Se for um commit mais antigo no histórico do PR:**
```bash
    git rebase -i <commit-anterior-ao-que-precisa-mudar>
    # marque o commit com problema como "reword" (ou "r")
    # salve, edite a mensagem, salve novamente
    git push --force-with-lease
```
* Após o push forçado, o workflow do GitHub Actions roda novamente e o check é atualizado automaticamente.

## Referência
 
* https://www.conventionalcommits.org/pt-br/
* https://commitlint.js.org/
