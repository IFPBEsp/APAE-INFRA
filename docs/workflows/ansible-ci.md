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
| Chaves privadas | `validate.sh secrets` | Nenhuma chave privada versionada em `ansible/` |
| Collections | `validate.sh collections` | Todas as collections de `requirements.yml` com versão exata `X.Y.Z`; instalação das versões fixadas |
| YAML | `validate.sh yaml` | `yamllint --strict` com [`ansible/.yamllint`](../../ansible/.yamllint) |
| Lint | `validate.sh lint` | `ansible-lint` perfil `production` com [`ansible/.ansible-lint`](../../ansible/.ansible-lint) |
| Sintaxe | `validate.sh syntax` | `ansible-inventory --list` e `ansible-playbook --syntax-check` para cada playbook em `ansible/playbooks/` contra cada `ansible/inventories/<ambiente>/hosts.yml` |

Enquanto não houver playbooks em `ansible/playbooks/` (estrutura da #90), as etapas de lint e sintaxe informam a ausência e passam. Havendo playbooks sem inventário, a etapa de sintaxe falha.

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

Comandos equivalentes, executados dentro de `ansible/`:

```bash
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
| Palavra-chave inexistente em um play (`bogus_keyword: 1`) | Inventory and playbook syntax check |
| Collection com `version: ">=1.0.0"` em `requirements.yml` | Validate and install pinned collections |
| Cabeçalho `-----BEGIN OPENSSH PRIVATE KEY-----` em qualquer arquivo de `ansible/` | Check for committed private keys |
