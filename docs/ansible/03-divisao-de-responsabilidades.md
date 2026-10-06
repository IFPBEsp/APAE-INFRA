# 03 — Divisão de responsabilidades

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Princípio

Cada recurso deve ter uma ferramenta proprietária para seu estado declarado. Git é a fonte da configuração; GitHub Actions valida e orquestra, mas não se torna o dono do estado de Terraform ou Ansible.

## Matriz de ownership

| Domínio/recurso | Proprietário | Limite |
| --- | --- | --- |
| VPS, rede, IP, volume, DNS e firewall do provedor | Terraform, onde houver integração suportada | Para HostGator, confirmar API e recursos do plano; se não houver suporte, provisionamento fora do Terraform deve ser registrado como exceção |
| cloud-init | Terraform entrega user-data somente se suportado; cloud-init executa no primeiro boot | Bootstrap mínimo, sem configuração recorrente de serviços |
| SO, usuários, SSH, pacotes e firewall local | Ansible | Estado dentro do sistema operacional |
| NGINX externo, Certbot, systemd e diretórios do host | Ansible | Inclui configuração e validação local; NGINX possui as portas públicas 80/443 |
| Instalação e configuração da distribuição Kubernetes | Ansible | Depois de definida a distribuição/topologia; não inclui workloads GitOps |
| Instalação do ArgoCD, AppProject e Application raiz | Ansible/playbook de bootstrap | Guia atual exclui `project.yaml` e `app-of-apps.yaml` da raiz; mudanças nesses objetos também passam pelo playbook |
| Recursos Kubernetes e workloads | ArgoCD | Namespaces, Deployments, Services, Ingress e componentes declarados no Git |
| Validação e orquestração de Terraform/Ansible | GitHub Actions | Não contém configuração imperativa paralela aos módulos/playbooks |

Quando um assunto existir em duas camadas, atribuir ownership por recurso. Exemplo: Terraform aplica regras de rede do provedor; Ansible aplica regras do firewall do host. Essas políticas precisam ser compatíveis, mas não devem disputar o mesmo objeto.

Na VPS atual (HostGator simples, sem painel), o firewall a gerenciar é o do Ubuntu e pertence ao Ansible. A ferramenta HG Firewall Administration documentada pela HostGator é acessada via WHM e, portanto, não se aplica a esta instância. Não há confirmação de firewall de rede externo nem de API para que Terraform o controle; verificar com o provedor antes de atribuir esse recurso ao Terraform.

## Fluxo

```text
PR/merge no APAE-INFRA
        ├── Terraform → infraestrutura do provedor
        ├── Ansible → sistema operacional e serviços de host
        └── manifests → ArgoCD → recursos Kubernetes

GitHub Actions valida e orquestra Terraform e Ansible.
```

Ansible instala e prepara o cluster e mantém os três objetos do bootstrap do ArgoCD: instalação, AppProject e Application raiz. O guia atual exclui `project.yaml` e `app-of-apps.yaml` da raiz, portanto alterações nesses objetos seguem o playbook controlado. Depois que a raiz é registrada, Applications filhas e recursos Kubernetes atribuídos a elas são reconciliados pelo ArgoCD. Isso evita duas ferramentas atualizando os mesmos objetos.

## NGINX, TLS e Kubernetes

O NGINX do host será a borda pública e terminará TLS. Ele será o único componente da VPS a escutar publicamente nas portas 80/443 e encaminhará o tráfego a um endpoint interno do cluster. O ponto concreto de encaminhamento (por exemplo, endpoint privado ou NodePort) depende da topologia/distribuição Kubernetes e precisa ser definido antes da implementação.

O Ingress Controller, se adotado, não deve reivindicar as mesmas portas públicas do host. Certbot e a renovação de certificados pertencem ao Ansible, com validação de configuração e reload seguro do NGINX.

## Observabilidade

- Agentes e serviços instalados no host: Ansible.
- Workloads, exporters e recursos Kubernetes: ArgoCD.

Os documentos em `monitoring/` descrevem componentes, mas a propriedade de cada instalação deve seguir essa divisão.

## Referências internas

- [Bootstrap da VPS e do ArgoCD](04-bootstrap-da-vps.md)
- [Fluxo GitHub Actions + Ansible](06-fluxo-github-actions-e-ansible.md)
- [Fluxo atual/proposto do ArgoCD](../argocd/fluxo-argocd.md)
- [Boas práticas Terraform](../boas-praticas/03-terraform.md)
- [Boas práticas GitOps](../boas-praticas/06-argocd-e-gitops.md)
