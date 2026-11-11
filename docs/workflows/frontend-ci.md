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

### Tabela de Inputs

Todos os inputs sao passados atraves da chave `with` na chamada do job.

| Input | Tipo | Obrigatorio | Padrao | Descricao |
| --- | --- | --- | --- | --- |
| `working-directory` | `string` | Sim | - | Diretorio onde se encontra o package.json da aplicacao frontend. |
| `package-manager` | `string` | Nao | `detect` | Gerenciador a ser usado (`pnpm` ou `npm`). Se `detect`, tenta ler o lockfile do `working-directory` e, na ausencia dele, o da raiz do repositorio. |
| `node-version` | `string` | Nao | `22` | Versao do Node.js utilizada pelo runner. |
| `run-lint` | `boolean` | Nao | `true` | Se true, executa o script lint definido no package.json. |
| `typecheck-command` | `string` | Nao | `tsc --noEmit` | Comando executado para checagem de tipos. Se vazio, a etapa e pulada. |
| `run-tests` | `boolean` | Nao | `false` | Se true, executa o script test definido no package.json. |
| `run-build` | `boolean` | Nao | `true` | Se true, executa a etapa de build do frontend. |
| `build-env` | `string` | Nao | - | Variaveis de ambiente nao sensiveis necessarias apenas em tempo de build, passadas uma por linha. Precisam iniciar com `NEXT_PUBLIC_`. |

## Observacoes Importantes

- Segredos: Nao passe tokens sensiveis ou senhas no input `build-env`. Ele deve ser usado estritamente para URLs publicas e flags (`NEXT_PUBLIC_*`).
- Diretorio de instalacao: antes de instalar, o script define o `install-dir`. Se o `working-directory` possuir lockfile (`pnpm-lock.yaml` ou `package-lock.json`), ele e usado. Caso contrario, a raiz (`.`) e verificada em busca de `pnpm-workspace.yaml`, `pnpm-lock.yaml` ou `package-lock.json`; havendo lockfile na raiz, `install-dir` vira `.` e o lockfile da raiz e usado para o hash do cache e para a instalacao, enquanto os scripts continuam sendo executados no `working-directory`.
- Versao do pnpm: o `package.json` do `install-dir` e verificado em busca do campo `packageManager` (ex: `pnpm@10.x`). Se ele estiver definido, nenhum parametro `version` e passado para o `pnpm/action-setup` (evitando o erro "Multiple versions of pnpm specified"); caso contrario, a versao padrao `10` e usada. O `package_json_file` sempre aponta para o `package.json` do `install-dir`.
- Next.js: antes da etapa de typecheck, quando o projeto declara `next` no package.json, o workflow executa `next typegen` para gerar o `next-env.d.ts`. Falhas desse comando viram apenas um aviso e nao interrompem a CI.
- Suporte a workspaces: as dependencias sao instaladas de forma global no `install-dir` (raiz do workspace), mas os scripts sao executados no `working-directory`.
- Lockfiles duplicados: E altamente recomendado que o repositorio possua apenas um lockfile (`pnpm-lock.yaml` ou `package-lock.json`). Lockfiles duplicados podem gerar ambiguidade na deteccao automatica.
