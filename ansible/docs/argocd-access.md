# Acesso administrativo ao ArgoCD

O ArgoCD é instalado como ClusterIP, sem exposição
pública da interface administrativa.

## Pré-requisitos

- Acesso SSH autorizado à VPS.
- Permissão administrativa para utilizar o k3s.
- Senha administrativa configurada pelo Ansible.

## Estabelecer o túnel SSH

Na máquina local:

```bash
ssh -N -L 18080:127.0.0.1:18080 \
  -p 22022 ansible@IP_DA_VPS
```

Em outra sessão SSH na VPS:

```bash
sudo k3s kubectl -n argocd \
  port-forward --address 127.0.0.1 \
  svc/argocd-server 18080:443
```

## Acessar a interface

Na máquina local, abrir:

<https://localhost:18080>

O certificado TLS poderá apresentar um aviso
por não corresponder ao endereço localhost.

## Conta de leitura e RBAC

A conta local `apae-leitura` permite login e está associada ao papel
`role:apae-readonly`, com leitura de Applications, projetos, repositórios e logs.
Ela não recebe permissões de sincronização, criação, alteração ou exclusão.
A política padrão é vazia; o acesso depende da associação explícita ao papel.

Antes de executar o bootstrap, editar o Vault com:

```bash
ansible-vault edit ansible/vars/argocd-vault.yml
```

Além de `argocd_admin_password_hash`, definir `argocd_readonly_password_hash`
com um hash bcrypt próprio, gerado a partir de uma senha distinta. Não adicionar
senhas ou hashes em texto claro ao repositório. O Ansible valida os hashes antes
da instalação e atualiza o Secret via stdin, com `no_log: true`, somente quando
o hash muda. A data de alteração da senha também é atualizada nesse caso.

Após aplicar, entrar como `apae-leitura`, conferir a visualização das Applications
e confirmar que operações de sincronização e alteração são negadas. Reexecutar
o playbook para verificar que as senhas não são atualizadas sem necessidade.

## Segurança

- Não abrir portas públicas para o ArgoCD.
- Não registrar senhas em logs ou scripts.
- Não copiar o kubeconfig administrativo para o runner.
- Encerrar o túnel e o port-forward após a administração.
