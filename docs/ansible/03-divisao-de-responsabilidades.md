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
| Serviços e agentes instalados no host | Ansible | Gerencia unidades systemd, diretórios e demais serviços do Ubuntu; NGINX externo e Certbot não fazem parte da arquitetura inicial selecionada. |
| Cluster Kubernetes k3s single-node | Ansible | Instalação, configuração, versionamento e manutenção do k3s na VPS, conforme a issue #90. |
| Instalação e atualização do ArgoCD | Ansible | Bootstrap e upgrades do ArgoCD com versão fixada e validada, após a disponibilização do k3s; os manifestos da própria instalação ficam fora da reconciliação do ArgoCD. |
| AppProject e Application raiz | Ansible | Mantidos pelo playbook enquanto estiverem excluídos da reconciliação do ArgoCD. |
| AppProject de infraestrutura | Ansible | Aplicado no bootstrap junto com o AppProject `apae` e antes das Applications de infraestrutura; mantido pelo playbook, com `project-infra.yaml` também incluído no `exclude` da Application raiz. |
| CRDs do Gateway API | ArgoCD, em Application de infraestrutura | Instalação e atualização declarativa, com permissões para recursos de cluster e sincronização antes dos recursos dependentes. |
| NGINX Gateway Fabric e data plane | ArgoCD, em Application de infraestrutura | Instalação e atualização do controller e data plane, após disponibilização dos CRDs necessários. |
| GatewayClass, Gateway e HTTPRoute | ArgoCD | Recursos declarativos de entrada e roteamento; GatewayClass é de escopo de cluster e exige permissões específicas. |
| cert-manager e certificados TLS Kubernetes | ArgoCD, em Application de infraestrutura | Instalação e manutenção do cert-manager, seus CRDs e configurações; certificados e Secrets TLS reconciliados conforme a solução ACME adotada. |
| Exposição do Gateway nas portas 80/443 | Ansible e ArgoCD, por recursos distintos | Ansible prepara host, k3s e rede local; ArgoCD gerencia os recursos Kubernetes do Gateway. Não há um segundo proxy HTTP no host. |
| Namespaces, Deployments, Services e workloads Kubernetes | ArgoCD | Reconciliação dos recursos atribuídos às Applications gerenciadas pelo ArgoCD. |
| Agentes e serviços de observabilidade do host | Ansible | Instalação e configuração dos componentes executados diretamente na VPS. |
| Componentes de observabilidade Kubernetes | ArgoCD | Gerenciamento declarativo dos workloads e recursos de monitoramento executados dentro do cluster. |
| Validação e orquestração de Terraform e Ansible | GitHub Actions | Executa validações e aplicações controladas, sem assumir a propriedade do estado dos recursos. |

Quando um assunto existir em duas camadas, atribuir ownership por recurso. Exemplo: Terraform aplica regras de rede do provedor; Ansible aplica regras do firewall do host. Essas políticas precisam ser compatíveis, mas não devem disputar o mesmo objeto.

Na VPS atual (HostGator simples, sem painel), o firewall a gerenciar é o do Ubuntu e pertence ao Ansible. A ferramenta HG Firewall Administration documentada pela HostGator é acessada via WHM e, portanto, não se aplica a esta instância. Não há confirmação de firewall de rede externo nem de API para que Terraform o controle; verificar com o provedor antes de atribuir esse recurso ao Terraform.

### Requisitos de firewall para o k3s

A role de firewall do Ansible deverá considerar os requisitos de rede do
k3s single-node, conforme a issue #90.

A documentação do k3s alerta para conflitos do UFW com a rede Kubernetes e
recomenda desabilitá-lo como opção mais simples. Caso o UFW seja mantido habilitado,
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

Caso sejam utilizados Services NodePort, a implementação deverá:

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
Mudança versionada no APAE-INFRA
       |
       +-- Pull Request para dev: lint e validações sem acesso à produção
       |
       +-- Merge em main: apply Ansible controlado pelo
       |   GitHub Environment production e aprovação autorizada
       |        |
       |        +-- Terraform (se houver integração com o provedor)
       |        |     Recursos externos à VPS
       |        |
       |        `-- Ansible
       |              SO, usuários, SSH e firewall local
       |              Instalação e manutenção do k3s single-node
       |              Bootstrap do ArgoCD, AppProject e Application raiz
       |
       `-- ArgoCD (após bootstrap e conforme política de sync)
             CRDs do Gateway API e cert-manager
             NGINX Gateway Fabric e data plane
             GatewayClass, Gateway, HTTPRoute e certificados
             Applications filhas e workloads Kubernetes
```

GitHub Actions valida e orquestra as execuções aprovadas de Terraform e Ansible. O merge em `dev` **não aplica mudanças na VPS de produção**. O ArgoCD reconcilia recursos Kubernetes conforme as políticas de sincronização de cada Application; a instalação de componentes de infraestrutura exige Applications dedicadas, permissões compatíveis e ordenação de dependências.

O Ansible instala e configura o k3s single-node conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90). Também executa o bootstrap do ArgoCD, incluindo instalação, AppProject e Application raiz. Enquanto `project.yaml` e `app-of-apps.yaml` estiverem excluídos do caminho reconciliado, suas alterações deverão ser realizadas pelo playbook.

Na implementação, o Ansible também deverá criar e manter o AppProject dedicado aos CRDs, ao NGINX Gateway Fabric e ao cert-manager, antes de registrar as Applications de infraestrutura. Ao adicionar seu manifesto em `argocd/project-infra.yaml`, atualizar o `spec.source.directory.exclude` da Application raiz para `'{app-of-apps.yaml,project.yaml,project-infra.yaml}'`. Assim, a raiz continua reconciliando as Applications filhas, mas não passa a gerenciar o AppProject de infraestrutura pelo projeto `apae` das aplicações. Alterações e recuperação desse novo AppProject também deverão ser realizadas pelo playbook.

Após o bootstrap, o ArgoCD reconcilia as Applications filhas e os recursos atribuídos a elas, sem que duas ferramentas administrem o mesmo objeto. A recuperação do bootstrap deve contemplar reinstalação do k3s e do ArgoCD, reaplicação dos objetos de bootstrap, validação dos CRDs e restauração de dados persistentes a partir de backups independentes.

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

Além do bootstrap, o Ansible mantém a instalação e executa os upgrades do próprio ArgoCD, com versão fixada e validada. Os manifestos dessa instalação não deverão ser incluídos em nenhuma Application reconciliada pelo ArgoCD. Essa atribuição substitui o autogerenciamento da instalação previsto no estudo anterior e evita que o playbook e o ArgoCD disputem os mesmos recursos.

O AppProject de bootstrap e a Application raiz permanecem sob responsabilidade do Ansible
enquanto estiverem excluídos do caminho reconciliado pelo ArgoCD. Portanto,
o autogerenciamento integral previsto na decisão anterior não se aplica a
esses objetos na arquitetura aqui proposta.

Essa adequação é específica ao cenário estudado e **não significa abandonar
o Terraform**. A delimitação definitiva do seu escopo, bem como a atualização
dos documentos anteriores, deverá ser validada com o time na
[issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86).

## Gateway API, TLS e Kubernetes

A arquitetura selecionada no estudo da [issue #60](https://github.com/IFPBEsp/APAE-INFRA/issues/60) utiliza **Gateway API exposto diretamente com NGINX Gateway Fabric** sobre o **k3s single-node** previsto na [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90). Não haverá NGINX externo ao cluster nem Certbot como componentes obrigatórios da primeira implementação.

Fluxo lógico selecionado:

```text
Internet / DNS
      |
      | HTTP :80 / HTTPS :443
      v
IP público da VPS
      |
      v
NGINX Gateway Fabric (ArgoCD)
      | Terminação TLS e entrada HTTP/HTTPS
      v
Gateway / HTTPRoute (ArgoCD)
      |
      v
Services ClusterIP
      |
      v
Aplicações APAE
```

O diagrama é lógico: o mecanismo real que publica o data plane nas portas 80/443 — por exemplo, ServiceLB do k3s ou configuração de rede adequada — deverá ser selecionado e testado na implementação. Não pressupõe um NGINX ou um NodePort privado intermediário.

A divisão de responsabilidades será:

- **Ansible:** instalação e manutenção do k3s, configuração do host, SSH e firewall local, e bootstrap do ArgoCD; preparação das condições de rede e prevenção de conflitos de porta.
- **ArgoCD (infraestrutura):** instalação e atualização dos CRDs do Gateway API, do NGINX Gateway Fabric e do cert-manager, com Applications, permissões e ordem de sincronização adequadas.
- **ArgoCD (roteamento):** reconciliação de GatewayClass, Gateway, HTTPRoute e demais recursos declarativos, com Services das aplicações preferencialmente em `ClusterIP`.
- **NGINX Gateway Fabric:** implementação efetiva do proxy de entrada e terminação TLS dentro do Kubernetes.
- **cert-manager:** emissão e renovação automatizada dos certificados TLS, após definição de emissores e método de validação ACME; o uso de um certificado para hostname compartilhado é suficiente no roteamento inicial por path.

Os CRDs deverão estar disponíveis antes de controllers e recursos dependentes. O AppProject dedicado à infraestrutura deverá permitir os namespaces e recursos de escopo de cluster necessários sem ampliar indiscriminadamente as permissões do AppProject das aplicações.

A instalação do k3s deverá resolver conflitos com o Traefik integrado. O ServiceLB poderá ser mantido ou desabilitado de acordo com a estratégia de exposição selecionada: **não desabilitá-lo automaticamente sem justificar o mecanismo alternativo**. Validar as portas públicas 80/443, preservação do IP real, HTTPS, renovação TLS, acesso administrativo e recuperação após reinicializações.

A alternativa **NGINX externo + Gateway API** permanece documentada no estudo de NGINX apenas para reavaliação mediante requisito operacional concreto, não como padrão a provisionar pelo Ansible.

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
