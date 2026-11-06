# Workflow de CI para Frontends Node.js (Next.js)

Este e um workflow reutilizavel (`workflow_call`) do GitHub Actions desenvolvido para padronizar a Integracao Continua (CI) dos frontends da organizacao. Ele cuida do processo de instalacao de dependencias de forma segura, aplica cache nativo e executa etapas configuraveis de lint, typecheck, testes e build.

## Como utilizar

Para adotar este workflow no seu repositorio de aplicacao (ex: `APAE`, `APAE-atendimento`), crie ou edite o arquivo `.github/workflows/ci.yml` do repositorio destino e faca a chamada (`uses`) apontando para o repositorio de infraestrutura.

### Exemplo basico de uso

```yaml
name: CI Frontend

on:
  pull_request:
    branches:
      - dev
      - main

jobs:
  frontend-ci:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/frontend-ci.yml@main
    with:
      working-directory: 'apps/meu-frontend'
      run-tests: true
      build-env: |
        NEXT_PUBLIC_API_URL=https://api.exemplo.com
        NEXT_PUBLIC_FLAG=true
```

Tabela de Inputs
Todos os inputs sao passados atraves da chave with na chamada do job.
Input  Tipo  Obrigatorio  Padrao  Descricao
working-directory  string  Sim  -  Diretorio onde se encontra o package.json da aplicacao frontend.
package-manager  string  Nao  detect  Gerenciador a ser usado (pnpm ou npm). Se deixado como detect, tentara ler o lockfile.
node-version  string  Nao  22  Versao do Node.js utilizada pelo runner.
run-lint  boolean  Nao  true  Se true, executa o script lint definido no package.json.
typecheck-command  string  Nao  tsc --noEmit  Comando executado para checagem de tipos. Se vazio, a etapa e pulada.
run-tests  boolean  Nao  false  Se true, executa o script test definido no package.json.
build-env  string  Nao  -  Variaveis de ambiente nao sensiveis necessarias apenas em tempo de build, passadas uma por linha. Precisam iniciar com NEXT_PUBLIC_.
Observacoes Importantes
Segredos: Nao passe tokens sensiveis ou senhas no input build-env. Ele deve ser usado estritamente para URLs publicas e flags (NEXT_PUBLIC_*).
Suporte a workspaces: O script detecta automaticamente se o projeto usa workspaces do pnpm baseando-se na presenca do arquivo pnpm-workspace.yaml na raiz, instalando as dependencias de forma global mas executando os scripts no working-directory.
Lockfiles duplicados: E altamente recomendado que o repositorio possua apenas um lockfile (pnpm-lock.yaml ou package-lock.json). Lockfiles duplicados podem gerar ambiguidade na deteccao automatica.
