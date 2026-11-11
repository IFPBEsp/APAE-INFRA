# Como adicionar scanning de segredos ao seu repositório

## O que é

O workflow de scanning de segredos usa o [Gitleaks](https://github.com/gitleaks/gitleaks)
para analisar o diff do PR, detectar automaticamente credenciais, tokens e chaves
expostas e falhar o check do job antes que o segredo entre no histórico do git.

Para que o bloqueio de merge seja efetivo, configure o job
`call-gitleaks / gitleaks` como **Required** (check obrigatório) nas regras de
proteção de branch do repositório (**Settings > Branches > Branch protection
rules**). Sem essa configuração, o check falha, mas o merge não é impedido.

## Como ativar no seu repositório

Crie o arquivo `.github/workflows/gitleaks.yml` no seu repositório:

```yaml
name: Secret Scanning

on:
  pull_request:
    branches:
      - dev
      - main

jobs:
  call-gitleaks:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/reusable-gitleaks.yml@dev
    secrets: inherit
```

A diretiva `secrets: inherit` repassa as secrets do repositório chamador
para o workflow reutilizável. Configure a secret `GITLEAKS_LICENSE` em
**Settings > Secrets and variables > Actions** da organização ou do
repositório (a licença é necessária apenas para uso em organizações).

## PRs de Forks

PRs originados de forks não possuem acesso às secrets do repositório
(`GITLEAKS_LICENSE`), fazendo o Gitleaks falhar na inicialização.

Por isso, as contribuições devem ser feitas via branches criadas dentro do
próprio repositório. Caso receba um PR de fork, oriente o autor a recriar a
branch internamente e abrir um novo PR a partir dela.

## Falsos positivos (`.gitleaksignore`)

Para tratar falsos positivos, utilize o arquivo `.gitleaksignore` na raiz do
projeto, listando o fingerprint específico gerado pelo Gitleaks para cada
finding:

```bash
echo <fingerprint> >> .gitleaksignore
```

> Atenção: arquivos de exemplo (`.env.example`) devem continuar sendo varridos
> pelo scanner. Não crie allowlists de path que ignorem o caminho inteiro, pois
> isso cria uma brecha para segredos reais colados dentro desses arquivos.

## O que fazer se um segredo real já foi commitado

1. **Rotacione a credencial imediatamente** — troque a senha, revogue o token,
   gere uma nova chave. Remover do código não basta, pois o histórico do git
   ainda guarda o valor antigo.
2. Notifique o responsável pelo serviço afetado.
3. Se necessário, reescreva o histórico com `git filter-repo` para remover
   o segredo dos commits anteriores.
