# Workflow de validação Ansible (`ansible-ci.yml`)

> **Arquivo do workflow:** [`.github/workflows/ansible-ci.yml`](../../.github/workflows/ansible-ci.yml)  
> **Script de validação:** [`ansible/scripts/validate.sh`](../../ansible/scripts/validate.sh)  
> **Issue de origem:** [APAE-INFRA #109](https://github.com/IFPBEsp/APAE-INFRA/issues/109)  
> **Relacionadas:** [#90](https://github.com/IFPBEsp/APAE-INFRA/issues/90) (estrutura Ansible) e [#110](https://github.com/IFPBEsp/APAE-INFRA/issues/110) (aplicação protegida)

## 1. Objetivo

Validar automaticamente playbooks, roles, inventários e dependências Ansible em Pull Requests para `dev` e `main` (promoção), **sem acesso à VPS**. O workflow não recebe secrets de produção, não usa SSH e não executa `--check` remoto.

## 2. Quando executa

Em `pull_request` com destino `dev` ou `main`, quando houver alteração em:

- `ansible/**` (playbooks, roles, inventários, variáveis, dependências e configurações de lint);
- `.github/workflows/ansible-ci.yml`.

Permissões declaradas: somente `contents: read`. Actions externas são referenciadas por SHA completo.

## 3. Verificações

| Etapa | Comando (via `validate.sh`) | O que garante |
| --- | --- | --- |
| Chaves privadas | `validate.sh secrets` | Nenhuma chave privada versionada em `ansible/`; todo arquivo `*vault*.yml` está cifrado com `ansible-vault` |
| Collections | `validate.sh collections` | Todas as collections de `requirements.yml` com versão exata `X.Y.Z`; instalação das versões fixadas |
| YAML | `validate.sh yaml` | `yamllint --strict` com [`ansible/.yamllint`](../../ansible/.yamllint) (ignora `.collections/`, `.cache/` e arquivos `*vault*.yml`) |
| Lint | `validate.sh lint` | `ansible-lint` perfil `production` com [`ansible/.ansible-lint`](../../ansible/.ansible-lint), quando houver conteúdo Ansible em `playbooks/`, `roles/`, `inventories/` ou `collections/` |
| Sintaxe | `validate.sh syntax` | `ansible-inventory --list` para cada `ansible/inventories/<ambiente>/hosts.yml`, independentemente de playbooks; com playbooks, também executa `ansible-playbook --syntax-check` contra cada inventário; inventário ilegível faz a etapa falhar |

Sem playbooks em `ansible/playbooks/` (estrutura da #90), o lint ainda valida roles, inventários e collections próprios existentes, e a etapa de sintaxe valida os inventários encontrados; apenas o `ansible-playbook --syntax-check` é ignorado. O lint só é ignorado quando não há conteúdo Ansible aplicável. Havendo playbooks sem inventário, a etapa de sintaxe falha.

### Arquivos cifrados (`ansible-vault`)

O CI não recebe a senha do vault e não decifra nada. Para o `ansible-lint` e o `ansible-playbook --syntax-check`, o `validate.sh` trabalha em uma cópia temporária de `ansible/` em que cada arquivo cifrado (primeira linha `$ANSIBLE_VAULT;`) é substituído por um stub vazio (`{}`); a cópia é apagada ao final e o arquivo versionado não é alterado. Como o `yamllint` ignora arquivos `*vault*.yml`, a etapa `secrets` falha se algum deles estiver em texto puro.

## 4. Versões fixadas

- Ferramentas (`ansible-core`, `ansible-lint`, `yamllint`): [`ansible/requirements.txt`](../../ansible/requirements.txt), todas com `==`.
- Collections: [`ansible/requirements.yml`](../../ansible/requirements.yml), todas com versão exata; entradas sem versão ou com intervalo fazem o CI falhar.
- Python: `3.12` no runner.

Atualize versões em PR dedicado.

## 5. Validação local

Pré-requisito: Python 3.12 ou superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ansible/requirements.txt

# Todas as verificações, na mesma ordem do CI
ansible/scripts/validate.sh

# Ou uma por vez
ansible/scripts/validate.sh secrets
ansible/scripts/validate.sh collections
ansible/scripts/validate.sh yaml
ansible/scripts/validate.sh lint
ansible/scripts/validate.sh syntax
```

Comandos equivalentes, executados dentro de `ansible/` (o `validate.sh` continua sendo a fonte de verdade e aplica essas variáveis automaticamente):

```bash
export ANSIBLE_COLLECTIONS_PATH="$PWD/.collections"
export ANSIBLE_HOST_KEY_CHECKING="False"
export ANSIBLE_RETRY_FILES_ENABLED="False"
export ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED="True"
export ANSIBLE_NOCOLOR="1"

yamllint --strict -c .yamllint .
ansible-lint --config-file .ansible-lint
ansible-inventory -i inventories/<ambiente>/hosts.yml --list > /dev/null
ansible-playbook -i inventories/<ambiente>/hosts.yml --syntax-check playbooks/<playbook>.yml
```

## 6. Validação remota

`--check` contra a VPS de produção **não** é executado no CI. Uma eventual validação remota só poderá usar ambiente isolado, com credenciais próprias, em workflow separado (ver [#110](https://github.com/IFPBEsp/APAE-INFRA/issues/110)).

## 7. Falha controlada

Para comprovar os checks, abra um PR de teste (não mesclar) com uma das alterações abaixo e confirme que o job `Validate Ansible` falha na etapa indicada:

| Alteração | Etapa que deve falhar |
| --- | --- |
| Espaços no fim de linha ou YAML inválido em um playbook | YAML lint |
| Task sem `name` ou módulo sem FQCN (`apt:` em vez de `ansible.builtin.apt:`) | Ansible lint |
| Palavra-chave inexistente em um play (`bogus_keyword: 1`) | Ansible lint (o `ansible-lint` já executa o syntax-check e falha antes da etapa de sintaxe) |
| Inventário com estrutura inválida (`hosts:` como lista em vez de mapa), mesmo sem playbooks | Inventory and playbook syntax check |
| Collection com `version: ">=1.0.0"` em `requirements.yml` | Validate and install pinned collections |
| Cabeçalho `-----BEGIN OPENSSH PRIVATE KEY-----` em qualquer arquivo de `ansible/` | Check for committed private keys |
