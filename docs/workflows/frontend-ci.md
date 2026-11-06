# Workflow de CI para Frontends Node.js (Next.js)

Este é um workflow reutilizável (`workflow_call`) do GitHub Actions desenvolvido para padronizar a Integração Contínua (CI) dos frontends da organização. Ele cuida do processo de instalação de dependências de forma segura, aplica cache nativo e executa etapas configuráveis de lint, typecheck, testes e build.

## Como utilizar

Para adotar este workflow no seu repositório de aplicação (ex: `APAE`, `APAE-atendimento`), crie ou edite o arquivo `.github/workflows/ci.yml` do repositório destino e faça a chamada (`uses`) apontando para o repositório de infraestrutura.

### Exemplo básico de uso

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
Tabela de Inputs
Todos os inputs são passados através da chave with na chamada do job.
Input	Tipo	Obrigatório	Padrão	Descrição
working-directory	string	Sim	-	Diretório onde se encontra o package.json da aplicação frontend.
package-manager	string	Não	detect	Gerenciador a ser usado (pnpm ou npm). Se deixado como detect, tentará ler o lockfile.
node-version	string	Não	22	Versão do Node.js utilizada pelo runner.
run-lint	boolean	Não	true	Se true, executa o script lint definido no package.json.
typecheck-command	string	Não	tsc --noEmit	Comando executado para checagem de tipos. Se vazio, a etapa é pulada.
run-tests	boolean	Não	false	Se true, executa o script test definido no package.json.
build-env	string	Não	-	Variáveis de ambiente (não sensíveis) necessárias apenas em tempo de build, passadas uma por linha. Precisam iniciar com NEXT_PUBLIC_.
Observações Importantes
Segredos: Não passe tokens sensíveis ou senhas no input build-env. Ele deve ser usado estritamente para URLs públicas e flags (NEXT_PUBLIC_*).
Suporte a workspaces: O script detecta automaticamente se o projeto usa workspaces do pnpm baseando-se na presença do arquivo pnpm-workspace.yaml na raiz, instalando as dependências de forma global mas executando os scripts no working-directory.
Lockfiles duplicados: É altamente recomendado que o repositório possua apenas um lockfile (pnpm-lock.yaml ou package-lock.json). Lockfiles duplicados podem gerar ambiguidade na detecção automática.
