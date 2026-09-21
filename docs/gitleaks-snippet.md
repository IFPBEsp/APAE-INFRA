# Como adicionar scanning de segredos ao seu repositório

## O que é

O workflow de scanning de segredos usa o [Gitleaks](https://github.com/gitleaks/gitleaks)
para detectar automaticamente credenciais, tokens e chaves expostas em PRs,
falhando o CI antes que o segredo entre no histórico do git.

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
```

## Exceções

Se precisar ignorar algum arquivo ou padrão específico, crie um `.gitleaksignore`
na raiz do repositório com os paths a ignorar.

## O que fazer se um segredo real já foi commitado

1. **Rotacione a credencial imediatamente** — troque a senha, revogue o token,
   gere uma nova chave. Remover do código não basta, pois o histórico do git
   ainda guarda o valor antigo.
2. Notifique o responsável pelo serviço afetado.
3. Se necessário, reescreva o histórico com `git filter-repo` para remover
   o segredo dos commits anteriores.