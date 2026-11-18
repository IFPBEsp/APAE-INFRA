# Acesso administrativo ao cluster k3s — APAE Produção

## 1. Visão geral

Este documento descreve os procedimentos de acesso administrativo ao cluster
Kubernetes do APAE-INFRA, provisionado com k3s na VPS HostGator.

O objetivo é garantir que o acesso ao cluster seja seguro, restrito, auditável e
reproduzível por meio das configurações mantidas no repositório.

### Ambiente

| Item | Configuração |
| --- | --- |
| Ambiente | Produção |
| Provedor | HostGator |
| Arquitetura | k3s single-node |
| Sistema operacional | Ubuntu 22.04 LTS |
| Versão inicial do k3s | `v1.36.5+k3s1` |
| Provisionamento | Ansible |
| Inventário | `inventories/production/hosts.yml` |
| Usuário administrativo SSH | `ansible` |
| Porta SSH | `22022/TCP` |
| Porta da API Kubernetes | `6443/TCP` |
| Interface pública | `ens3` |
| Kubeconfig administrativo | `/etc/rancher/k3s/k3s.yaml` |
| Issue relacionada | #90 |

O cluster possui um único nó que executa o control plane e os workloads
Kubernetes.

Não há endpoint público administrativo intencionalmente disponibilizado para
acesso remoto direto à API Kubernetes.

### Reservas de recursos do nó

O template `roles/k3s/templates/config.yaml.j2` configura as seguintes reservas
do kubelet para a VPS com 2 vCPU e 4 GB de memória:

| Parâmetro | CPU | Memória | Finalidade |
| --- | --- | --- | --- |
| `system-reserved` | `250m` | `512Mi` | Sistema operacional e serviços como SSH |
| `kube-reserved` | `250m` | `512Mi` | Componentes Kubernetes e runtime de containers |

As reservas somam `500m` de CPU e `1Gi` de memória e reduzem os recursos
alocáveis aos pods. A memória alocável também considera o limiar de eviction do
kubelet. Esses valores são iniciais e devem ser revisados conforme o consumo
observado do nó.

O ArgoCD executa como workload e precisa de `requests` e `limits` próprios,
a serem definidos no bootstrap da
[issue #91](https://github.com/IFPBEsp/APAE-INFRA/issues/91).
As reservas do kubelet não reservam recursos para os pods do ArgoCD.

Após aplicar o playbook `playbooks/k3s.yml`, conferir na VPS:

```bash
sudo cat /etc/rancher/k3s/config.yaml
sudo k3s kubectl describe node
```

Verificar as reservas no arquivo gerado e comparar `Capacity` e `Allocatable`
do nó. A role reinicia o k3s quando a configuração é alterada.

### Separação dos ambientes por namespace

A decisão da [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90)
é separar logicamente os ambientes por namespaces no mesmo cluster single-node.
Os workloads de ambientes distintos devem usar namespaces distintos; todos
continuam compartilhando os recursos físicos do nó.

A criação dos namespaces, os nomes concretos por produto e ambiente e os
destinos das Applications do ArgoCD ficam na
[issue #92](https://github.com/IFPBEsp/APAE-INFRA/issues/92), junto aos overlays.
Essa issue contempla inicialmente `dev`; os overlays de `hml` e `prod` ficam
para etapas posteriores. Este provisionamento não cria esses namespaces.
Namespaces fornecem organização lógica; controles de acesso e de tráfego
dependem de RBAC e políticas de rede específicas.

---

## 2. Política de acesso

O acesso administrativo segue os seguintes princípios:

1. Utilizar autenticação SSH por chave pública.
2. Desabilitar autenticação SSH por senha.
3. Impedir login SSH direto como root.
4. Utilizar um usuário administrativo não root.
5. Executar operações privilegiadas por meio de `sudo`.
6. Manter a API Kubernetes protegida contra acesso público direto.
7. Preservar o kubeconfig administrativo exclusivamente em locais seguros.
8. Não armazenar credenciais, tokens ou kubeconfigs administrativos no Git.

O acesso SSH é o caminho administrativo previsto para operações no cluster.

O usuário `ansible` possui permissões de elevação de privilégios necessárias à
automação da infraestrutura.

Acesso ao usuário `ansible` e permissões de `sudo` devem ser restritos às
pessoas autorizadas a administrar a infraestrutura.

---

## 3. Bootstrap inicial de uma VPS nova

Esta etapa prepara uma VPS Ubuntu 22.04 LTS recém-criada para que o Ansible
possa provisionar o k3s. Na instalação inicial, o usuário `ansible` e a porta
SSH `22022` podem não existir. A preparação abaixo é **manual e controlada**;
não constitui, por si só, um playbook automatizado de criação da conta.

### 3.1. Acesso inicial e pré-requisitos

Entrar pelo console de recuperação/administração do provedor ou com o usuário
administrativo inicial fornecido pela VPS. A conexão SSH inicial pode usar a
porta `22`, mas deve-se verificar a configuração efetiva do provedor. Manter uma
sessão administrativa e acesso ao console abertos até o teste final na porta
definitiva.

Na estação de administração, preparar um par de chaves Ed25519, se ainda não
existir:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
```

Compartilhar com a VPS **somente a chave pública**, nunca a privada. Confirmar
também que o endereço da VPS está configurado localmente em
`inventories/production/host_vars/apae-prod.yml` (arquivo ignorado pelo Git).

### 3.2. Criar a conta de automação e cadastrar a chave

Na VPS, a partir da sessão administrativa inicial:

```bash
sudo adduser ansible
sudo install -d -m 700 -o ansible -g ansible /home/ansible/.ssh
sudo nano /home/ansible/.ssh/authorized_keys
```

Inserir no arquivo uma linha contendo a chave pública autorizada da estação de
administração. Em seguida:

```bash
sudo chown ansible:ansible /home/ansible/.ssh/authorized_keys
sudo chmod 600 /home/ansible/.ssh/authorized_keys
```

Não substituir chaves já existentes sem verificar se continuam necessárias. Se
`nano` não abrir por incompatibilidade de terminal, usar
`TERM=xterm-256color nano ...` apenas na sessão atual.

### 3.3. Configurar elevação de privilégios

A automação requer `sudo` não interativo. Criar a regra com validação de
sintaxe:

```bash
sudo visudo -f /etc/sudoers.d/90-apae-ansible
```

Adicionar ao arquivo:

```sudoers
ansible ALL=(ALL) NOPASSWD: ALL
```

Validar permissões e sintaxe:

```bash
sudo chmod 440 /etc/sudoers.d/90-apae-ansible
sudo visudo -cf /etc/sudoers.d/90-apae-ansible
```

Essa regra concede acesso administrativo amplo. Restringir a conta e suas chaves
às pessoas e automações autorizadas e planejar credenciais individuais para os
integrantes da equipe.

### 3.4. Verificar o acesso antes do hardening

Em uma **nova sessão** da estação administrativa (sem fechar a sessão inicial),
testar a porta inicial, aqui exemplificada como `22`:

```bash
ssh -i ~/.ssh/id_ed25519 -p 22 ansible@"IP_DA_VPS"
```

Na VPS, confirmar `whoami` (`ansible`) e `sudo -n id -u` (`0`). Se a porta ou o
usuário de bootstrap forem diferentes, adaptar os comandos ao ambiente do
provedor. Confirmar a identidade da chave de host SSH antes de aceitá-la.

### 3.5. Executar o hardening do SSH

A partir do diretório `ansible/` na estação administrativa, executar o playbook
usando temporariamente a porta inicial:

```bash
ansible-playbook -i inventories/production/hosts.yml \
  playbooks/hardening.yml -e ansible_port=22
```

Esse `-e` só é necessário durante o bootstrap, antes de a VPS aceitar conexões
na porta final definida pela variável `ssh_port`. A role configura autenticação
por chave pública, bloqueio de login direto como root e o parâmetro de porta
SSH.

**Antes de prosseguir:** confirmar que a porta final está liberada no firewall
do sistema e nas regras do provedor, quando existentes. Na VPS, verificar
`sudo sshd -t`, `sudo sshd -T | grep '^port '` e `sudo ss -ltnp | grep sshd`. Em
distribuições com socket activation do SSH, verificar também `ssh.socket` e seus
listeners. Não presumir que o arquivo de configuração isolado determine sozinho
a porta efetiva.

### 3.6. Confirmar a conexão definitiva

Abrir outra conexão, agora pela porta final (`22022` na configuração atual):

```bash
ssh -i ~/.ssh/id_ed25519 -p 22022 ansible@"IP_DA_VPS"
```

A partir de `ansible/`:

```bash
ansible-inventory -i inventories/production/hosts.yml --host apae-prod
ansible production -i inventories/production/hosts.yml -m ansible.builtin.ping
ansible production -i inventories/production/hosts.yml -b \
  -m ansible.builtin.command -a "id -u"
```

O inventário deve resolver `ansible_port` como `22022`, o `ping` deve retornar
`pong`, e o comando com `become` deve retornar `0`. **Não encerrar o acesso
inicial até esses testes passarem.**

### 3.7. Ordem do provisionamento

Com o acesso definitivo validado, a ordem operacional é:

1. Preparação da conta `ansible`, chave pública e `sudo` (bootstrap manual
   descrito acima).
2. Aplicação de `playbooks/hardening.yml` pela porta inicial, seguida da
   validação na porta definitiva.
3. Execução de `playbooks/prepare.yml` para validar o sistema operacional e a
   arquitetura, preparar o host e instalar os pacotes essenciais.
4. Execução de `playbooks/k3s-preflight.yml` para validar os recursos mínimos,
   cgroups e, na instalação inicial, a disponibilidade da porta da API.
5. Execução de `playbooks/k3s.yml`, cuja role `k3s` instala e inicia o
   `k3s-api-firewall.service` antes de iniciar o cluster.
6. Execução de `playbooks/k3s-verify.yml` e `playbooks/k3s-smoke-test.yml` para
   verificar o cluster.

A partir de `ansible/`, após validar o acesso SSH definitivo:

```bash
ansible-playbook playbooks/prepare.yml
ansible-playbook playbooks/k3s-preflight.yml
ansible-playbook playbooks/k3s.yml
ansible-playbook playbooks/k3s-verify.yml
ansible-playbook playbooks/k3s-smoke-test.yml
```

A role `k3s` instala explicitamente o pacote `iptables` antes de aplicar o
firewall, inclusive quando executada separadamente. Em `--check`, a ativação
do serviço de firewall e a verificação das regras são ignoradas, pois dependem
de alterações efetivamente aplicadas. A simulação não comprova a proteção do
host; essa validação ocorre na execução real e nos testes externos.

A documentação deste bootstrap resolve a lacuna de **ordem operacional**, mas um
provisionamento inteiramente automatizado a partir de uma VPS sem usuário
administrativo de automação exigirá um playbook específico de bootstrap ou
mecanismo equivalente. Não armazenar credenciais iniciais no repositório.

### 3.8. Recuperação e segurança

Preservar o console de recuperação do provedor como alternativa caso uma
alteração de SSH interrompa a conectividade. Não executar alterações de
autenticação, porta e firewall às cegas nem compartilhar chaves privadas ou
kubeconfigs administrativos.

---

## 4. Acesso à VPS via SSH

### 4.1. Pré-requisitos

A estação administrativa precisa possuir:

- Cliente OpenSSH.
- Chave privada Ed25519 autorizada na VPS.
- Acesso à porta TCP `22022`.
- Entrada correspondente à VPS no arquivo `known_hosts`.
- Permissão administrativa concedida pela equipe responsável.

O inventário Ansible utiliza a variável `ssh_port`, definida em
`inventories/production/group_vars/all.yml` (valor atual: `22022`):

```yaml
ansible_user: ansible
ansible_port: "{{ ssh_port }}"
ansible_ssh_private_key_file: ~/.ssh/id_ed25519
ansible_ssh_common_args: "-o IdentitiesOnly=yes"
```

A chave privada não deve ser compartilhada ou adicionada ao repositório.

### 4.2. Conexão direta

A partir de uma estação autorizada:

```bash
ssh -i ~/.ssh/id_ed25519 -p 22022 ansible@"IP_DA_VPS"
```

O endereço da VPS de produção deve ser configurado localmente em
inventories/production/host_vars/apae-prod.yml, arquivo ignorado pelo Git. O
placeholder IP_DA_VPS representa esse endereço.

Confirmar a identidade do servidor por meio da chave de host SSH antes de
aceitar uma nova chave ou uma alteração inesperada.

### 4.3. Conexão pelo Ansible

A partir do diretório `ansible/`:

```bash
ansible production -m ansible.builtin.ping
```

Resultado esperado:

```text
apae-prod | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

Verificar elevação de privilégios:

```bash
ansible production -b -m ansible.builtin.command -a "id -u"
```

Resultado esperado:

```text
0
```

Essas verificações confirmam a conectividade e a capacidade de executar tarefas
administrativas.

---

## 5. Configuração de segurança SSH

O hardening SSH é gerenciado pelo role Ansible:

```text
roles/hardening/
```

O template principal está localizado em:

```text
roles/hardening/templates/00-apae-hardening.conf.j2
```

As diretivas configuradas incluem:

```sshconfig
Port 22022
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
KbdInteractiveAuthentication no
PermitEmptyPasswords no
```

### 5.1. Verificar configuração efetiva

Na VPS:

```bash
sudo sshd -T | grep -E \
  -e '^(port|permitrootlogin|passwordauthentication) ' \
  -e '^(pubkeyauthentication|kbdinteractiveauthentication) '
```

Os valores esperados são:

```text
port 22022
permitrootlogin no
pubkeyauthentication yes
passwordauthentication no
kbdinteractiveauthentication no
```

Se aparecerem várias diretivas `port` ou a porta efetiva não for `22022`,
revisar a configuração do OpenSSH (incluindo arquivos em `sshd_config.d/`) antes
de encerrar a sessão administrativa inicial.

### 5.2. Validar sintaxe SSH

```bash
sudo sshd -t
```

Uma execução bem-sucedida não apresenta mensagens de erro.

Alterações de SSH devem preservar uma sessão administrativa funcional e ser
realizadas com um procedimento de recuperação disponível pelo console do
provedor.

Não aplicar alterações simultâneas em autenticação SSH e regras de firewall sem
validar a conectividade.

---

## 6. Acesso administrativo ao Kubernetes

O k3s instala uma versão integrada do `kubectl`, disponível por meio do próprio
binário.

### 6.1. Acesso local

Após conectar à VPS:

```bash
sudo k3s kubectl get nodes -o wide
```

Listar os pods de todos os namespaces:

```bash
sudo k3s kubectl get pods -A
```

Consultar os namespaces:

```bash
sudo k3s kubectl get namespaces
```

Verificar informações do cluster:

```bash
sudo k3s kubectl cluster-info
```

O uso de `sudo` permite utilizar o kubeconfig administrativo mantido pelo k3s
com permissões restritas.

### 6.2. Kubeconfig administrativo

O arquivo de configuração administrativo está localizado em:

```text
/etc/rancher/k3s/k3s.yaml
```

A configuração declarativa utiliza:

```yaml
write-kubeconfig-mode: "0600"
```

Isso restringe o acesso ao arquivo ao proprietário, normalmente `root`.

O kubeconfig contém credenciais administrativas sensíveis e concede privilégios
elevados ao cluster.

Não é permitido:

- Adicionar o kubeconfig ao repositório Git.
- Compartilhá-lo por canais não autorizados.
- Alterar suas permissões para `0644` ou `0666`.
- Copiá-lo para diretórios públicos.
- Utilizá-lo em pipelines que não necessitem de acesso administrativo.

O uso local de `sudo k3s kubectl` é o método administrativo padrão.

---

## 7. Acesso remoto ao cluster

### 7.1. Estratégia adotada

O acesso remoto administrativo ao Kubernetes ocorre indiretamente por SSH.

A API Kubernetes não precisa ser exposta publicamente para que a equipe realize
operações administrativas.

A abordagem padrão consiste em:

1. Autenticar na VPS por SSH.
2. Executar `sudo k3s kubectl`.
3. Encerrar a sessão após finalizar a operação.

### 7.2. Execução remota de comandos

Também é possível executar comandos administrativos diretamente via SSH:

```bash
ssh -i ~/.ssh/id_ed25519 -p 22022 \
  ansible@"IP_DA_VPS" \
  'sudo k3s kubectl get nodes'
```

Esse procedimento evita a transferência do kubeconfig para a estação local.

### 7.3. Acesso remoto por túnel SSH

Quando uma ferramenta local precisar acessar a API Kubernetes, poderá ser
utilizado um túnel SSH temporário.

Na estação administrativa:

```bash
ssh -N \
  -L 16443:127.0.0.1:6443 \
  -i ~/.ssh/id_ed25519 \
  -p 22022 \
  ansible@"IP_DA_VPS"
```

O túnel encaminha a porta local `16443` para a API Kubernetes no loopback da
VPS.

Por padrão, o túnel deve permanecer acessível somente pela própria estação
administrativa.

O acesso por `kubectl` local exige um kubeconfig autorizado, com credenciais
válidas e um endereço de servidor compatível com o túnel.

Também é necessário validar corretamente o certificado TLS do servidor,
incluindo o nome ou endereço utilizado.

Não utilizar `insecure-skip-tls-verify` como solução para problemas de
certificados.

O túnel não substitui autenticação, autorização ou validação TLS do Kubernetes.

A distribuição de kubeconfigs administrativos não faz parte do procedimento
padrão.

---

## 8. Proteção da API Kubernetes

### 8.1. Portas protegidas

O cluster utiliza as seguintes portas administrativas ou internas:

| Porta | Protocolo | Finalidade | Política na interface pública |
| --- | --- | --- | --- |
| 6443 | TCP | Kubernetes API | Bloquear |
| 10250 | TCP | Kubelet API | Bloquear |
| 8472 | UDP | Flannel VXLAN | Bloquear |

As regras são aplicadas na interface pública:

```text
ens3
```

O acesso administrativo à API deve ocorrer localmente ou por um canal seguro
previamente autorizado.

### 8.2. Gerenciamento do firewall

A proteção é instalada, habilitada e verificada pela role `k3s`, executada pelo
playbook `playbooks/k3s.yml`. A role aplica o serviço de firewall antes de
iniciar o k3s, sem exigir a execução prévia de um playbook separado.

O template utilizado é:

```text
roles/k3s/templates/k3s-api-firewall.service.j2
```

O serviço systemd é:

```text
k3s-api-firewall.service
```

O serviço `k3s` possui uma dependência systemd declarada para exigir a
inicialização do serviço de firewall. A role também verifica as regras IPv4 e
IPv6 aplicadas.

### 8.3. Verificar o serviço

```bash
sudo systemctl is-active k3s-api-firewall.service
```

Resultado esperado:

```text
active
```

### 8.4. Verificar as regras IPv4

```bash
sudo iptables -S INPUT
```

As regras esperadas incluem:

```text
-A INPUT -i ens3 -p tcp -m tcp --dport 6443 -j DROP
-A INPUT -i ens3 -p tcp -m tcp --dport 10250 -j DROP
-A INPUT -i ens3 -p udp -m udp --dport 8472 -j DROP
```

Consultar também:

```bash
sudo iptables -nvL INPUT --line-numbers
```

### 8.5. Verificar as regras IPv6

```bash
sudo ip6tables -S INPUT
```

A verificação deve confirmar as regras equivalentes para as portas protegidas.

A existência das regras não comprova, isoladamente, que nenhum caminho anterior
do firewall permita o tráfego.

A validação completa exige conferir a ordem das regras, as chains relevantes e a
conectividade a partir de uma origem externa autorizada.

Não remover nem reorganizar manualmente as regras Kubernetes sem avaliar o
impacto na rede do cluster.

---

### 8.6. Restrição de NodePorts e validação externa

O template `roles/k3s/templates/config.yaml.j2` restringe os endereços de
NodePort ao loopback IPv4:

```yaml
kube-proxy-arg:
  - "nodeport-addresses=127.0.0.1/32"
```

Essa restrição permanece até a implementação da entrada pelo NGINX Gateway
Fabric. O acesso funcional por loopback depende do modo do kube-proxy e deve
ser validado antes de usá-lo como caminho de entrada. As regras da chain
`INPUT` para portas administrativas não comprovam a proteção dos NodePorts.

Após aplicar `playbooks/k3s.yml`, executar de uma estação externa autorizada:

```bash
nmap -Pn -sT -p 6443,10250,30000-32767 IP_DA_VPS
sudo nmap -Pn -sU -p 8472,30000-32767 IP_DA_VPS
```

Se a VPS possuir IPv6 público, repetir os dois comandos com `-6` e o endereço
IPv6 público como destino. Nenhuma porta NodePort deve aparecer como `open`.
O resultado UDP `open|filtered` é inconclusivo e exige verificação adicional
das regras efetivas e do tráfego recebido.

Uma varredura sem Services NodePort ativos não comprova que um Service futuro
ficará protegido. Validar também com um Service NodePort de teste controlado,
confirmando que não responde no endereço público, e remover seus recursos ao
final. Repetir a validação após reinício do k3s ou alteração do modo do
kube-proxy.

---

## 9. Verificação do cluster via Ansible

O repositório possui um playbook específico para validar a saúde do Kubernetes:

```text
playbooks/k3s-verify.yml
```

A partir do diretório `ansible/`:

```bash
ansible-playbook playbooks/k3s-verify.yml
```

O playbook verifica:

1. A versão instalada do k3s.
2. A correspondência com a versão fixada.
3. A condição `Ready` dos nós.
4. A disponibilidade do CoreDNS.
5. A disponibilidade do Local Path Provisioner.
6. A disponibilidade do Metrics Server.
7. A criptografia de Secrets no datastore.

Uma execução bem-sucedida deve terminar sem falhas.

O playbook não precisa alterar o cluster para realizar essas verificações.

---

## 10. Smoke test de workloads

Para verificar se o Kubernetes consegue executar um workload, utilizar:

```bash
ansible-playbook playbooks/k3s-smoke-test.yml
```

O playbook executa um teste temporário utilizando Nginx.

### Processo

1. Copia o manifesto de teste para a VPS.
2. Cria o namespace `smoke-test`.
3. Cria o Deployment `nginx-test`.
4. Aguarda o Deployment ficar disponível.
5. Confirma que o pod está `Ready`.
6. Verifica que existe uma réplica disponível.
7. Remove o namespace e os recursos temporários.
8. Remove o manifesto temporário.

O teste comprova o agendamento e a disponibilidade básica de um workload
Kubernetes.

Ele não realiza, na implementação atual, uma requisição HTTP funcional ao Nginx.

A limpeza ocorre por meio de um bloco Ansible `always`, que tenta remover os
recursos mesmo quando há falha durante o teste.

Após a execução, não é necessário manter o namespace `smoke-test`.

---

## 11. Segurança e controle de credenciais

### 11.1. Chaves SSH

Cada administrador autorizado deve utilizar uma chave SSH individual, sempre que
possível.

As chaves privadas devem:

- Permanecer em armazenamento seguro.
- Possuir permissões restritas.
- Ser protegidas por passphrase, quando aplicável.
- Ser revogadas quando o acesso deixar de ser necessário.

Não compartilhar uma única chave privada entre todos os administradores.

### 11.2. Credenciais Kubernetes

O kubeconfig administrativo deve continuar protegido no servidor.

Para futuras integrações com GitOps ou CI/CD, preferir identidades específicas
com RBAC e permissões mínimas, em vez de distribuir o kubeconfig administrativo
do cluster.

Não armazenar tokens e credenciais Kubernetes em arquivos versionados.

### 11.3. Auditoria

O acesso SSH e as ações administrativas devem ser monitorados conforme a
política operacional da infraestrutura.

Os logs do SSH podem ser consultados com:

```bash
sudo journalctl -u ssh
```

Os logs do k3s podem ser consultados com:

```bash
sudo journalctl -u k3s
```

Esses logs auxiliam na investigação de falhas, mas não substituem uma política
de auditoria de ações da API Kubernetes.

---

## 12. Diagnóstico de problemas

### 12.1. Falha de conexão SSH

Verificar:

- Disponibilidade da VPS.
- Porta `22022`.
- Chave SSH correta.
- Usuário administrativo.
- Regras de firewall e bloqueios do provedor.

A partir de uma estação autorizada:

```bash
ssh -v -i ~/.ssh/id_ed25519 -p 22022 ansible@"IP_DA_VPS"
```

Se não houver acesso SSH, utilizar o console de recuperação disponibilizado pelo
provedor antes de modificar configurações de rede.

### 12.2. Serviço k3s indisponível

```bash
sudo systemctl status k3s
```

Consultar logs:

```bash
sudo journalctl -u k3s -n 100 --no-pager
```

Não executar uma reinstalação automática sem analisar a causa da falha.

### 12.3. Nó Kubernetes não está Ready

```bash
sudo k3s kubectl get nodes -o wide
```

Consultar eventos:

```bash
sudo k3s kubectl get events -A --sort-by=.lastTimestamp
```

Verificar recursos da VPS, rede CNI, armazenamento e logs do serviço.

### 12.4. Problemas de DNS interno

```bash
sudo k3s kubectl get pods -n kube-system
```

Verificar o CoreDNS:

```bash
sudo k3s kubectl rollout status deployment/coredns \
  -n kube-system --timeout=120s
```

Consultar logs quando necessário:

```bash
sudo k3s kubectl logs -n kube-system deployment/coredns
```

### 12.5. Falha de autenticação Kubernetes

Verificar se os comandos estão sendo executados com as credenciais corretas:

```bash
sudo k3s kubectl get nodes
```

Não modificar permissões do kubeconfig para contornar erros de autenticação ou
acesso.

---

## 13. Restrições e próximos passos

A configuração documentada corresponde ao acesso administrativo inicial do
cluster single-node.

Melhorias futuras poderão incluir:

- Controle individual de acesso ao Kubernetes com RBAC.
- Auditoria de operações da API Kubernetes.
- Monitoramento da disponibilidade das portas administrativas.
- Revisão periódica de permissões SSH.
- Automação de rotação e revogação de credenciais.
- Estratégia de acesso remoto baseada em VPN ou rede privada, caso necessária.
- Validação recorrente das regras de firewall após atualizações do k3s.

Essas melhorias devem ser tratadas separadamente, conforme a necessidade
operacional e o escopo das próximas issues.

---

## 14. Referências

- [Issue #90 — Provisionar cluster Kubernetes com k3s na VPS](https://github.com/IFPBEsp/APAE-INFRA/issues/90)
- [Documentação oficial do k3s](https://docs.k3s.io/)
- [Configuração do servidor k3s](https://docs.k3s.io/installation/configuration)
- [Requisitos de rede do k3s](https://docs.k3s.io/installation/requirements#networking)
- [Kubeconfig e acesso ao cluster](https://docs.k3s.io/cluster-access)
- [Backup e recuperação do cluster](./k3s-backup-restore.md)

---
