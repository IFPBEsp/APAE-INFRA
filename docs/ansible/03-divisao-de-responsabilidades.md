# 03 — Divisão de responsabilidades

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Princípio

Cada recurso deve ter uma ferramenta proprietária para seu estado declarado. Git é a fonte da configuração; GitHub Actions valida e orquestra, mas não se torna o dono do estado de Terraform ou Ansible.

## Matriz de ownership

| Domínio/recurso | Proprietário | Limite |
| --- | --- | --- |
| VPS, rede, IP, volumes, DNS e firewall do provedor | Terraform, quando houver integração suportada | Na HostGator, confirmar disponibilidade de API ou provider. Sem suporte, registrar o provisionamento externo como exceção. |
| cloud-init | Terraform e cloud-init, se suportados | Terraform fornece user-data; cloud-init executa apenas o bootstrap inicial de uma nova VPS. |
| SO, usuários, SSH, pacotes e firewall local | Ansible | Configuração e manutenção do sistema operacional da VPS. |
| NGINX externo, Certbot, systemd e diretórios do host | Ansible | Gerencia o proxy reverso externo, a terminação TLS e as portas públicas 80/443. |
| Cluster Kubernetes k3s single-node | Ansible | Instalação, configuração, versionamento e manutenção do k3s na VPS, conforme a issue #90. |
| Instalação inicial do ArgoCD | Ansible | Bootstrap do ArgoCD após a disponibilização do cluster k3s. |
| AppProject e Application raiz | Ansible | Mantidos pelo playbook enquanto estiverem excluídos da reconciliação do ArgoCD. |
| CRDs do Gateway API | ArgoCD | Instalação e atualização declarativa, garantindo sua disponibilização antes dos recursos dependentes. |
| NGINX Gateway Fabric | ArgoCD | Instalação, configuração e manutenção do controller no cluster após a disponibilização dos CRDs necessários. |
| GatewayClass, Gateway e HTTPRoute | ArgoCD | Recursos declarativos de entrada e roteamento, versionados no Git e reconciliados no cluster. |
| Namespaces, Deployments, Services e workloads Kubernetes | ArgoCD | Reconciliação dos recursos atribuídos às Applications gerenciadas pelo ArgoCD. |
| Agentes e serviços de observabilidade do host | Ansible | Instalação e configuração dos componentes executados diretamente na VPS. |
| Componentes de observabilidade Kubernetes | ArgoCD | Gerenciamento declarativo dos workloads e recursos de monitoramento executados dentro do cluster. |
| Validação e orquestração de Terraform e Ansible | GitHub Actions | Executa validações e aplicações controladas, sem assumir a propriedade do estado dos recursos. |

Quando um assunto existir em duas camadas, atribuir ownership por recurso. Exemplo: Terraform aplica regras de rede do provedor; Ansible aplica regras do firewall do host. Essas políticas precisam ser compatíveis, mas não devem disputar o mesmo objeto.

Na VPS atual (HostGator simples, sem painel), o firewall a gerenciar é o do Ubuntu e pertence ao Ansible. A ferramenta HG Firewall Administration documentada pela HostGator é acessada via WHM e, portanto, não se aplica a esta instância. Não há confirmação de firewall de rede externo nem de API para que Terraform o controle; verificar com o provedor antes de atribuir esse recurso ao Terraform.

### Requisitos de firewall para o k3s

A role de firewall do Ansible deverá considerar os requisitos de rede do
k3s single-node, conforme a issue #90.

A documentação oficial do k3s recomenda desabilitar o UFW para evitar
conflitos com a rede Kubernetes. Caso o UFW seja mantido habilitado,
a configuração deverá contemplar, no mínimo:

- Comunicação dos pods na rede `10.42.0.0/16`, por padrão.
- Comunicação dos Services na rede `10.43.0.0/16`, por padrão.
- Acesso à API Kubernetes na porta `6443/tcp`, restrito às origens
  administrativas autorizadas.

Essas redes são os valores padrão do k3s e deverão ser ajustadas
caso sejam utilizados CIDRs personalizados.

O Ansible deverá validar a conectividade entre pods, Services e
componentes do cluster após aplicar ou alterar regras de firewall.
As alterações precisam preservar o acesso administrativo e um caminho
de recuperação em caso de falha.

O UFW não deve ser considerado proteção suficiente para restringir
a exposição de Services do tipo NodePort. Dependendo do modo de
funcionamento do kube-proxy, regras de iptables/nftables podem
interagir com o processamento das regras do firewall local.

A implementação deverá:

- Restringir a exposição dos NodePorts às interfaces e origens
  estritamente necessárias.
- Avaliar a configuração de `nodePortAddresses` e as regras efetivas
  de iptables/nftables.
- Não expor indiscriminadamente a faixa padrão de NodePorts
  `30000-32767`.
- Validar externamente quais portas estão realmente acessíveis.
- Registrar os controles adicionais de rede utilizados para impedir
  acesso não autorizado.

Referência:
[Requisitos oficiais de rede e firewall do k3s](https://docs.k3s.io/installation/requirements).

## Fluxo

```text
PR/merge no APAE-INFRA
        |
        |-- Terraform
        |     Recursos do provedor, se houver integração suportada
        |
        |-- Ansible
        |     Sistema operacional, SSH e firewall local
        |     NGINX externo e Certbot
        |     Instalação e configuração do k3s single-node
        |     Bootstrap do ArgoCD, AppProject e Application raiz
        |
        `-- ArgoCD
              CRDs do Gateway API
              NGINX Gateway Fabric
              GatewayClass, Gateway e HTTPRoute
              Applications filhas e workloads Kubernetes

GitHub Actions valida e orquestra Terraform e Ansible.
```

O Ansible instala e configura o k3s single-node, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90).

O bootstrap do ArgoCD também pertence ao Ansible, incluindo sua instalação, o AppProject e a Application raiz. Enquanto `project.yaml` e`app-of-apps.yaml` estiverem excluídos do caminho reconciliado, suas alterações deverão ser realizadas pelo playbook.

Após o bootstrap, o ArgoCD reconcilia as Applications filhas e os recursos Kubernetes atribuídos a elas, evitando que duas ferramentas administrem o mesmo objeto.

## Compatibilidade com a decisão anterior de Terraform

O estudo de GitOps da [issue #59](https://github.com/IFPBEsp/APAE-INFRA/issues/59), documentado em
[`docs/terraform/05-decisao-arquitetural.md`](../terraform/05-decisao-arquitetural.md),
atribuiu conceitualmente ao Terraform o bootstrap do host, do Kubernetes e a
instalação inicial do ArgoCD, prevendo seu autogerenciamento posterior.

Para a VPS HostGator atualmente utilizada, este estudo **refina e substitui
essa atribuição de bootstrap**, considerando que ainda não foi confirmada
uma API ou integração Terraform compatível com os recursos do provedor.

A divisão proposta para esse ambiente é:

- **Terraform:** recursos externos ao host somente quando existir integração
  suportada. Não é responsável pela configuração contínua do sistema operacional.
- **Ansible:** preparação do host, instalação do Kubernetes e bootstrap do
  ArgoCD, incluindo AppProject e Application raiz.
- **ArgoCD:** reconciliação das Applications filhas e dos recursos Kubernetes
  atribuídos a elas após o bootstrap.

O AppProject e a Application raiz permanecem sob responsabilidade do Ansible
enquanto estiverem excluídos do caminho reconciliado pelo ArgoCD. Portanto,
o autogerenciamento integral previsto na decisão anterior não se aplica a
esses objetos na arquitetura aqui proposta.

Essa adequação é específica ao cenário estudado e **não significa abandonar
o Terraform**. A delimitação definitiva do seu escopo, bem como a atualização
dos documentos anteriores, deverá ser validada com o time na
[issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86).

## NGINX, TLS e Kubernetes

A arquitetura proposta utiliza um cluster Kubernetes k3s single-node na VPS HostGator, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90).

O NGINX externo, instalado e gerenciado pelo Ansible, será a borda pública da infraestrutura e o responsável pela terminação TLS. Ele será o único componente da VPS a utilizar publicamente as portas 80/443.

O tráfego será encaminhado do NGINX externo para um endpoint interno do NGINX Gateway Fabric, responsável por implementar o Gateway API dentro do cluster.

Fluxo proposto:

```text
Internet
   |
   v
NGINX externo (Ansible)
   | TLS / portas 80 e 443
   v
NGINX Gateway Fabric (ArgoCD)
   |
   v
Gateway / HTTPRoute (ArgoCD)
   |
   v
Services Kubernetes
   |
   v
Aplicações APAE
```

A divisão de responsabilidades será:

- **Ansible:** instalação e manutenção do NGINX externo, Certbot, certificados e configuração do proxy no host.
- **ArgoCD:** instalação declarativa dos CRDs do Gateway API, do NGINX Gateway Fabric e gerenciamento dos recursos GatewayClass, Gateway e HTTPRoute.
- **Ansible:** instalação e configuração do k3s single-node, incluindo a decisão operacional de desabilitar ou manter o Traefik integrado.

A instalação dos CRDs deverá ocorrer antes da reconciliação dos recursos Kubernetes que dependem deles.

O endpoint interno entre o NGINX externo e o Gateway Fabric, assim como a estratégia de exposição do controller e a configuração do Traefik, deverão ser definidos na implementação.

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
- [Issue #59 — Arquitetura GitOps com Terraform](https://github.com/IFPBEsp/APAE-INFRA/issues/59)
- [Issue #60 — Arquitetura do proxy reverso](https://github.com/IFPBEsp/APAE-INFRA/issues/60)
- [Issue #86 — Divisão de responsabilidades Terraform, Ansible e ArgoCD](https://github.com/IFPBEsp/APAE-INFRA/issues/86)
- [Issue #90 — Provisionamento do k3s](https://github.com/IFPBEsp/APAE-INFRA/issues/90)
