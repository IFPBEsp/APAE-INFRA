# Workflow de aplicação protegida do Ansible (`ansible-apply.yml`)

> **Arquivo do workflow:** [`.github/workflows/ansible-apply.yml`](../../.github/workflows/ansible-apply.yml)
> **Allowlist de execução:** [`ansible/scripts/apply-plan.sh`](../../ansible/scripts/apply-plan.sh)
> **Testes da allowlist:** [`tests/test_ansible_apply_plan.py`](../../tests/test_ansible_apply_plan.py)
> **Issue de origem:** [APAE-INFRA #110](https://github.com/IFPBEsp/APAE-INFRA/issues/110)
> **Relacionadas:** [#88](https://github.com/IFPBEsp/APAE-INFRA/issues/88) (proteções do GitHub), [#90](https://github.com/IFPBEsp/APAE-INFRA/issues/90) (bootstrap e hardening), [#109](https://github.com/IFPBEsp/APAE-INFRA/issues/109) (validação em PR), [#117](https://github.com/IFPBEsp/APAE-INFRA/issues/117) e [#140](https://github.com/IFPBEsp/APAE-INFRA/issues/140) (alternância Compose/k3s)

## 1. Objetivo

Aplicar na VPS de produção somente playbooks Ansible **revisados, integrados à `main` e aprovados** no Environment `production`, com execução serializada e registro de commit, ambiente e verificações de saúde.

O workflow não faz o bootstrap inicial da VPS, não cria contas e não substitui o processo da #90. Ele pressupõe que a conta de automação, a chave pública e o hardening inicial já existam.

O desenho segue o [estudo de Ansible](../ansible/06-fluxo-github-actions-e-ansible.md) e a [política de secrets](../ansible/05-secrets-ssh-e-seguranca.md).

## 2. Fluxo

```text
PR → dev                 ansible-ci.yml (#109): lint e syntax-check, sem VPS
merge em dev             nenhuma aplicação
PR dev → main            revisão + validações obrigatórias
push em main (paths)  ─┐
workflow_dispatch      ─┤
                        ▼
job plan     (sem secrets)   ref == main? inputs na allowlist? → resumo do plano
                        ▼
job apply    environment: production → aguarda aprovação
             checkout do github.sha → revalida o plano
             ansible-core/collections fixados → known_hosts confiável
             check.yml (pré) → playbooks do perfil → verificações de saúde
             registro no resumo → remoção do material sensível
```

### Gatilhos

| Gatilho | Quando | O que executa |
| --- | --- | --- |
| `push` em `main` | Alteração em `ansible/**` (exceto `ansible/docs/**` e `*.md`) ou no próprio workflow | Perfil fixo `baseline` |
| `workflow_dispatch` | Disparo manual, **somente a partir da `main`** | Perfil escolhido em lista fechada |

`ansible/**` cobre playbooks, roles, inventários, variáveis, `requirements.txt`, `requirements.yml`, `ansible.cfg` e scripts. Merge em `dev` não aciona o workflow.

Disparos manuais a partir de outra branch são barrados três vezes: pelo `if: github.ref == 'refs/heads/main'` dos jobs, pela verificação do `apply-plan.sh` e pela regra de *deployment branches* do Environment. Esta última é a que importa contra um workflow alterado numa branch, pois o YAML dessa branch poderia remover as outras duas.

## 3. Perfis, tags e inventários autorizados

Os inputs do `workflow_dispatch` são do tipo `choice`, e o `apply-plan.sh` recusa qualquer valor fora da allowlist, mesmo que a API seja chamada diretamente. Não há input de ref Git, caminho, comando, inventário livre ou extra vars.

| Perfil | Playbooks (em ordem) | Verificações de saúde | Vault |
| --- | --- | --- | --- |
| `baseline` (push) | `prepare.yml`, `hardening.yml` | `check.yml` | não |
| `check` | `check.yml` | `check.yml` | não |
| `prepare` | `prepare.yml` | `check.yml` | não |
| `hardening` | `hardening.yml` | `check.yml` | não |
| `k3s-preflight` | `k3s-preflight.yml` | `check.yml` | não |
| `k3s` | `k3s-preflight.yml`, `k3s.yml` | `check.yml`, `k3s-verify.yml` | não |
| `k3s-verify` | `k3s-verify.yml` | `check.yml` | não |
| `argocd` | `argocd.yml` | `check.yml`, `k3s-verify.yml` | sim |
| `configure-runtime-tls` | `configure-runtime-tls.yml` | `check.yml` | não |

- **Tags:** apenas `todas` (sem `--tags`). Nenhuma role define tags hoje; para liberar uma, adicione-a em `tags_for_selection` e nas opções do input `tags`, no mesmo PR.
- **Inventários:** apenas `production` → Environment `production`, host `apae-prod`.
- **Fora da allowlist de propósito:** `activate-compose.yml` e `activate-cluster.yml` (a alternância é manual pelo administrador, conforme a #140) e `k3s-smoke-test.yml` (cria recursos temporários no cluster).
- O `push` usa só a base do host porque `k3s` e `argocd` dependem do modo de execução ativo; num host em modo Compose, iniciar o k3s automaticamente competiria pela memória das aplicações.

Para incluir um playbook, altere `playbooks_for_profile`, o input `playbook` e a tabela acima no mesmo PR, e adicione o caso em `tests/test_ansible_apply_plan.py`.

## 4. Controles de segurança implementados no YAML

| Controle | Implementação |
| --- | --- |
| Código da `main` | `if: github.ref == 'refs/heads/main'` nos dois jobs + `apply-plan.sh` |
| Commit autorizado | `actions/checkout` com `ref: ${{ github.sha }}`; o job confere `git rev-parse HEAD` |
| Plano aprovado = plano executado | O job `apply` recalcula o plano e compara com a saída do job `plan` |
| Aprovação | `environment: production` no job `apply`; secrets só existem nesse job |
| Permissões mínimas | `permissions: {}` no topo e `contents: read` por job; `persist-credentials: false` |
| Actions fixadas | SHA completo: `actions/checkout` v4.4.0, `actions/setup-python` v6.3.0 |
| Dependências fixadas | Somente `ansible-core==X.Y.Z` de `ansible/requirements.txt` e collections com versão exata de `requirements.yml`; sem cache de pip/Actions no job privilegiado |
| Identidade SSH | `StrictHostKeyChecking=yes`, `UserKnownHostsFile` exclusivo, `GlobalKnownHostsFile=/dev/null`; o job falha se o known_hosts não tiver a chave do host **na porta do inventário**. Sem `ssh-keyscan` |
| Chave de automação | Gravada com `umask 077` em `$RUNNER_TEMP`, validada sem passphrase, nunca impressa; `BatchMode=yes` |
| Vault | Senha gravada apenas quando o perfil carrega arquivo cifrado (`argocd`) |
| Limpeza | Passo `if: always()` faz `shred` da chave e da senha do Vault e remove o diretório temporário |
| Serialização | `concurrency: ansible-apply-production-apae-prod` com `cancel-in-progress: false` |
| Runner | `ubuntu-24.04` hospedado e efêmero; nenhum runner privilegiado na VPS |
| Logs | Sem `-v`/`--diff`; o IP fica em secret (mascarado) e o resumo mostra apenas o alias `apae-prod` |

Sobre a concorrência: uma execução em andamento, inclusive aguardando aprovação, nunca é cancelada pelo workflow. Se chegarem várias execuções nesse intervalo, o GitHub mantém apenas a mais recente na fila e cancela as pendentes mais antigas, que nunca chegaram a tocar a VPS. **Não cancele manualmente um apply em andamento**; se for indispensável, rode `check` em seguida e avalie o estado do host.

## 5. Configuração necessária no GitHub (#88)

Os itens abaixo não são criados pelo YAML. Configure-os e registre as evidências na #110 **antes** de cadastrar a chave de automação.

### Environment `production`

O Environment é gerenciado pelo Terraform da #88, no bloco `environment_protection` de [`terraform/environments/github/main.tf`](../../terraform/environments/github/main.tf). O módulo [`github-repo-config`](../../terraform/modules/github-repo-config/README.md) cria as regras abaixo, e alterações nelas passam por PR e pelo `terraform apply` no HCP Terraform:

| Configuração | Valor |
| --- | --- |
| Required reviewers | `henriquetomazzz`, `LuizArtur29` |
| Prevent self-review | Habilitado |
| Allow administrators to bypass | Desabilitado |
| Deployment branches and tags | **Selected branches**: somente `main` |

Depois do `terraform apply`, confira a configuração efetiva e anexe a saída como evidência:

```bash
gh api repos/IFPBEsp/APAE-INFRA/environments/production \
  --jq '{name, can_admins_bypass, deployment_branch_policy,
         rules: [.protection_rules[] | {type, prevent_self_review, reviewers: [.reviewers[]?.reviewer.login]}]}'
gh api repos/IFPBEsp/APAE-INFRA/environments/production/deployment-branch-policies \
  --jq '[.branch_policies[] | {name, type}]'
```

O resultado esperado é `can_admins_bypass: false`, `custom_branch_policies: true`, uma regra `required_reviewers` com `prevent_self_review: true` e uma única branch policy `main`.

### Secrets e variáveis do Environment `production`

Cadastre tudo como **Environment** secret/variable, nunca no nível do repositório. Eles ficam fora do Terraform para que os valores não sejam gravados no state.

```bash
gh secret set ANSIBLE_SSH_PRIVATE_KEY --env production --repo IFPBEsp/APAE-INFRA < id_ed25519_apae_automation
gh secret set ANSIBLE_TARGET_HOST --env production --repo IFPBEsp/APAE-INFRA
gh secret set ANSIBLE_VAULT_PASSWORD --env production --repo IFPBEsp/APAE-INFRA
gh variable set ANSIBLE_KNOWN_HOSTS --env production --repo IFPBEsp/APAE-INFRA < known_hosts.candidato
```

Sem `--body`, o `gh secret set` lê o valor de forma interativa, sem deixá-lo no histórico do shell.

| Nome | Tipo | Conteúdo |
| --- | --- | --- |
| `ANSIBLE_SSH_PRIVATE_KEY` | Secret | Chave privada **dedicada** da conta `ansible`, sem passphrase (ed25519) |
| `ANSIBLE_TARGET_HOST` | Secret | Endereço usado para alcançar a VPS (IP público ou privado da VPN) |
| `ANSIBLE_VAULT_PASSWORD` | Secret | Senha do Vault; obrigatório apenas para o perfil `argocd` |
| `ANSIBLE_KNOWN_HOSTS` | Variable | Linha(s) `known_hosts` da VPS, conferidas por canal independente (ver 6.2) |

O known_hosts não é segredo, mas sua integridade é crítica. Por isso fica como variável do Environment, editável só por administradores, e não no Git, onde um PR poderia trocá-lo junto com o restante.

### Proteção da `main`

O ruleset `Protect main` já exige PR com uma aprovação e bloqueia force push e exclusão da branch. Os checks obrigatórios hoje são `TFLint` e `Trivy config`.

Adicione o `Validate Ansible` (#109) aos checks obrigatórios do ruleset `Protect main` (**Settings → Rules → Rulesets**). O `ansible-ci.yml` não usa mais `paths` no gatilho: ele roda em todo PR e pula a validação quando não há alteração em Ansible, então o check não fica pendente nos PRs que não alteram `ansible/` ([detalhes](ansible-ci.md#2-quando-executa)).

Faça essa alteração só depois que o novo `ansible-ci.yml` estiver na `main`. Antes disso, o check não seria criado nos PRs sem alteração em Ansible e travaria o merge. Até lá, o revisor do PR para a `main` deve confirmar que o `Validate Ansible` passou quando houver alteração em `ansible/`.

## 6. Conectividade e identidade do host

### 6.1 Caminho de rede

1. **Preferido: rede privada.** Se a HostGator ou o projeto disponibilizarem VPN/bastion, use o endereço privado em `ANSIBLE_TARGET_HOST`. A integração da VPN no runner (por exemplo WireGuard com chave própria no Environment) deve entrar em PR específico, com a Action fixada por SHA.
2. **Alternativa: SSH público restrito.** Os runners hospedados não têm IP fixo, e a lista de faixas publicada em `https://api.github.com/meta` é ampla e muda. Se este for o caminho adotado, documente na #88:
   - SSH somente por chave na porta do inventário (`22022`), sem root e sem senha (#90);
   - conta `ansible` dedicada, distinta das contas pessoais;
   - rate limit/fail2ban e monitoramento dos logs de autenticação;
   - rotação e revogação da chave (seção 9);
   - caminho de recuperação via console do provedor.
3. **Não** instalar runner self-hosted privilegiado na própria VPS. Um runner self-hosted em outra máquina, dentro da rede privada, é aceitável se for dedicado a este repositório e efêmero; isso exige trocar `runs-on` por PR.

A API do k3s (`6443/tcp`) não precisa ficar exposta ao runner: os playbooks usam `k3s kubectl` dentro da VPS via SSH.

### 6.2 Obter o known_hosts confiável

Execute **na VPS**, por sessão já confiável (console do provedor ou SSH previamente verificado):

```bash
for f in /etc/ssh/ssh_host_*_key.pub; do ssh-keygen -lf "$f"; done
```

Na estação do operador:

```bash
ssh-keyscan -p 22022 -t ed25519 <IP_DA_VPS> > known_hosts.candidato
ssh-keygen -lf known_hosts.candidato
```

Só cadastre o conteúdo de `known_hosts.candidato` em `ANSIBLE_KNOWN_HOSTS` se a fingerprint for **idêntica** à obtida na VPS. Para porta diferente de 22, a linha precisa estar no formato `[IP]:22022 ssh-ed25519 AAAA...`. O workflow valida isso e publica a fingerprint no resumo de cada execução para conferência.

Se a chave do host mudar (reinstalação ou rotação), o job falha na conexão. Isso é esperado: confira a nova fingerprint pelo mesmo procedimento antes de atualizar a variável.

## 7. Operação

### Aplicação após merge na `main`

1. O merge de `dev` → `main` com alterações em `ansible/**` cria a execução.
2. O job `plan` publica no resumo: commit, perfil, playbooks, tags e verificações.
3. O revisor do Environment confere o resumo e o diff do commit e aprova (ou rejeita) em **Review deployments**.
4. O job `apply` executa `check.yml`, os playbooks do perfil e as verificações de saúde.
5. Confira o resumo final e o histórico em **Deployments → production**.

### Disparo manual

**Actions → Ansible Apply → Run workflow**, com **Use workflow from: `main`**, escolhendo perfil, tags e inventário. A aprovação do Environment é exigida da mesma forma. Use `check` para validar conectividade sem alterar o host.

### Resultado registrado

O resumo do job `apply` registra: commit aplicado, ref, evento e solicitante, Environment, inventário/host, perfil e playbooks, tags, fingerprint da host key, horários de início e fim, resultado da pré-verificação, da aplicação e das verificações de saúde, e o link da execução. O GitHub também registra o deployment no Environment, com o aprovador.

As verificações de saúde também rodam quando a aplicação falha, desde que a pré-verificação tenha passado, para registrar o estado resultante. O job continua marcado como falho.

## 8. Falhas e rollback

| Sintoma | Causa provável | Ação |
| --- | --- | --- |
| `plan` falha com "não autorizado" | Branch diferente da `main` ou valor fora da allowlist | Disparar a partir da `main` com valor listado |
| Job `apply` não inicia | Aguardando aprovação ou outra execução em andamento | Aprovar/rejeitar; aguardar a execução atual |
| Falha em "Preparar identidade SSH" | Secret/variável ausente, chave com passphrase ou known_hosts sem a porta correta | Corrigir o cadastro (seções 5 e 6.2) |
| `Host key verification failed` | Chave do host mudou ou known_hosts incorreto | **Não** desabilitar a verificação; conferir a fingerprint (6.2) |
| `UNREACHABLE` | Rede/firewall/porta | Ver 6.1; validar pelo console do provedor |
| Falha no meio de um playbook | Erro de task; mudança parcialmente aplicada | Ler o log, corrigir via PR e reaplicar; avaliar o estado com `check` |

Rollback de configuração do host: reverter o commit por PR até a `main` e reaplicar o perfil. Isso **não** desfaz upgrades de pacotes, do k3s ou mudanças destrutivas; siga [Rollback](../boas-praticas/10-rollback.md) e o plano de backup.

Se a automação estiver indisponível, use o acesso *break-glass* descrito no [estudo de Ansible](../ansible/05-secrets-ssh-e-seguranca.md#acesso-emergencial-recuperação-e-resposta): registre a intervenção, leve a mudança permanente para PR e reaplique pelo workflow.

## 9. Rotação de credenciais

- **Chave SSH de automação:** gerar nova chave ed25519, adicionar a pública em `authorized_keys` da conta `ansible` (via Ansible/#90), atualizar `ANSIBLE_SSH_PRIVATE_KEY`, rodar `check`, remover a pública antiga e rodar `check` de novo.
- **Senha do Vault:** `ansible-vault rekey` em PR, atualizar `ANSIBLE_VAULT_PASSWORD` imediatamente após o merge.
- **Suspeita de vazamento:** remover a chave pública da VPS, apagar o secret, revisar o histórico de deployments e os logs de autenticação da VPS.

## 10. Habilitação: primeira execução e testes das proteções

Não cadastre `ANSIBLE_SSH_PRIVATE_KEY` antes de concluir os itens 1 a 3. Anexe as evidências (prints ou links das execuções) na #110 e na #88.

| # | Teste | Resultado esperado |
| --- | --- | --- |
| 1 | Conferir as configurações do Environment `production` (seção 5) | Reviewers, prevent self-review e branch `main` configurados |
| 2 | `workflow_dispatch` a partir de `dev` ou de outra branch | Job `plan` ignorado/falho; o Environment recusaria o deployment |
| 3 | Merge em `dev` com alteração em `ansible/**` | Nenhuma execução do `Ansible Apply` |
| 4 | Chamar a API com valor fora da lista (`gh workflow run ansible-apply.yml --ref main -f playbook=activate-compose -f tags=todas -f inventory=production`) | `plan` falha com "perfil de playbook não autorizado" |
| 5 | `check` sem `ANSIBLE_KNOWN_HOSTS` ou com fingerprint errada | Falha antes de conectar ou com `Host key verification failed` |
| 6 | Primeira execução real: `check` na `main`, acompanhada | Aprovação solicitada; pré-verificação e saúde `success`; fingerprint igual à conferida |
| 7 | Dois disparos de `check` seguidos | O segundo aguarda o primeiro terminar |
| 8 | Rejeitar uma execução no Environment | Job `apply` não roda e nenhum secret é usado |
| 9 | Primeira aplicação com alteração (`baseline`), acompanhada, com sessão de recuperação aberta | `PLAY RECAP` sem falhas; SSH continua acessível após o hardening |
| 10 | Revisar logs das execuções | Nenhuma chave, senha ou IP exposto |

Somente depois desses testes considere o fluxo recorrente habilitado.

## 11. Validação local

```bash
# Allowlist (não conecta em hosts)
python3 -m unittest tests.test_ansible_apply_plan -v
EVENT_NAME=push GIT_REF=refs/heads/main ansible/scripts/apply-plan.sh

# Lint do workflow
actionlint .github/workflows/ansible-apply.yml
zizmor .github/workflows/ansible-apply.yml
```
