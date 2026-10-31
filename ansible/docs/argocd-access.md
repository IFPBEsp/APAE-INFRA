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

https://localhost:18080

O certificado TLS poderá apresentar um aviso
por não corresponder ao endereço localhost.

## Segurança

- Não abrir portas públicas para o ArgoCD.
- Não registrar senhas em logs ou scripts.
- Não copiar o kubeconfig administrativo para o runner.
- Encerrar o túnel e o port-forward após a administração.
```
