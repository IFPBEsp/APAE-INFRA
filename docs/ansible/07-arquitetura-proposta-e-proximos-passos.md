# 07 — Arquitetura proposta e próximos passos

[← Índice do estudo](README.md)

Este documento consolida as decisões do estudo e serve como referência arquitetural para a implementação. Os documentos 01–06 detalham requisitos, alternativas, responsabilidades, bootstrap, segurança e fluxo operacional. **A arquitetura descrita é proposta, não uma implantação concluída.**

## Recomendação

Adotar **GitHub Actions + Ansible** para a configuração e manutenção da VPS HostGator existente. O **Terraform** permanece aplicável a recursos do provedor somente se for confirmada uma integração compatível; **cloud-init** poderá executar apenas o bootstrap inicial de novas instâncias caso exista suporte a `user-data`.

A plataforma Kubernetes prevista é **k3s single-node**, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90). O Ansible instala e mantém o k3s e realiza o bootstrap do ArgoCD. Depois desse bootstrap, o **ArgoCD** reconcilia os recursos Kubernetes sob sua responsabilidade.

Para a entrada pública HTTP/HTTPS, a arquitetura selecionada no estudo da [issue #60](https://github.com/IFPBEsp/APAE-INFRA/issues/60) é **Gateway API com NGINX Gateway Fabric exposto diretamente**, sem NGINX externo adicional na VPS. A terminação TLS ocorre no Gateway Fabric, e o **cert-manager** é a solução proposta para emissão e renovação de certificados dentro do cluster, sujeita à validação da integração durante a implementação.

```text
Git / APAE-INFRA
  ├── Terraform → recursos do provedor com API compatível (a confirmar)
  ├── cloud-init → acesso inicial de novas VPS, se suportado
  ├── Ansible → SO, usuários, SSH, firewall local, k3s e bootstrap ArgoCD
  └── manifests Kubernetes → ArgoCD
        ├── CRDs do Gateway API e NGINX Gateway Fabric
        ├── NGINX Gateway Fabric / data plane público
        ├── cert-manager, certificados e Secrets TLS
        ├── GatewayClass, Gateway e HTTPRoute
        └── Services, aplicações e observabilidade Kubernetes

GitHub Actions → valida, aprova e orquestra o Ansible
```

### Relação com a decisão arquitetural anterior

A [issue #59](https://github.com/IFPBEsp/APAE-INFRA/issues/59), documentada em [`docs/terraform/05-decisao-arquitetural.md`](../terraform/05-decisao-arquitetural.md), atribuiu conceitualmente ao Terraform o bootstrap do host, do Kubernetes e a instalação inicial do ArgoCD, prevendo autogerenciamento posterior.

Para a VPS HostGator atual, este estudo **propõe substituir essa atribuição de bootstrap pelo Ansible**, sem descartar Terraform para recursos externos quando houver suporte real de API ou provider. A definição não pressupõe que essa integração exista.

Enquanto `project.yaml` e `app-of-apps.yaml` estiverem excluídos do caminho reconciliado pela Application raiz, o **AppProject de bootstrap e a Application raiz** permanecem sob gerenciamento do playbook Ansible. As Applications filhas e os recursos atribuídos a elas ficam sob o ArgoCD. Portanto, o autogerenciamento integral previsto no estudo anterior não se aplica a esses objetos de bootstrap na divisão proposta.

A ratificação dessa divisão e a atualização dos documentos anteriores deverão ser tratadas na [issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86). Nenhuma ferramenta deve modificar o mesmo recurso por caminhos concorrentes.

## Estado atual e arquitetura proposta

Este estudo descreve uma arquitetura-alvo. A existência de diretórios e documentação não comprova a instalação dos componentes na VPS.

| Área | Estado documentado no repositório | Proposta |
| --- | --- | --- |
| Ansible | Não há playbooks, roles, inventários ou workflow Ansible implementados no escopo estudado | Criar `ansible/`, CI estática e apply protegido |
| Terraform | Existem `terraform/environments/` e `terraform/modules/`, ainda sem configuração funcional comprovada de provisionamento HostGator | Usar apenas para recursos com integração real, conforme #86 |
| Kubernetes | Há manifests em `kubernetes/apae-geral/base`, `kubernetes/apae-atendimento/base` e `kubernetes/site-comemorativo/base`; não há implantação comprovada no cluster | Implantar k3s single-node conforme #90 e organizar o GitOps |
| ArgoCD | O fluxo está documentado, mas o bootstrap e as Applications ainda precisam ser implementados e validados | Ansible instala o ArgoCD e mantém os objetos de bootstrap excluídos; ArgoCD reconcilia Applications filhas |
| Entrada HTTP/HTTPS | NGINX Gateway Fabric e Gateway API não estão comprovadamente implantados | NGINX Gateway Fabric exposto diretamente em 80/443; roteamento via Gateway e HTTPRoute, reconciliados pelo ArgoCD |
| TLS | Política proposta no estudo de NGINX, sem implantação comprovada | TLS no Gateway Fabric; emissão e renovação com cert-manager conforme integração validada |
| Observabilidade | Há diretórios e documentação; implantação não comprovada | Ansible para agentes do host; ArgoCD para recursos de observabilidade Kubernetes |

## Decisões arquiteturais

| Tema | Decisão |
| --- | --- |
| Configuration management do host | Ansible idempotente, com roles e playbooks versionados |
| Orquestração | GitHub Actions + Ansible |
| Pull Requests | Validação estática de YAML, lint e sintaxe, sem conexão nem segredos de produção |
| Apply de produção | Somente código integrado à `main`, mediante `push` nos caminhos monitorados e aprovação do Environment `production`; merges em `dev` não executam apply |
| Apply manual | `workflow_dispatch` somente na `main`, com inputs autorizados, verificação de `github.ref` e Environment restrito à `main` |
| `--check` remoto | Apenas em ambiente de teste isolado; omitir caso não exista |
| Bootstrap de VPS existente | Acesso inicial controlado a partir de estação autorizada; não enviar senha root para Actions |
| Bootstrap de VPS futura | Terraform e cloud-init mínimo somente quando o provedor confirmar o suporte |
| Distribuição Kubernetes | k3s single-node na VPS HostGator, com versão fixada, rede validada e política explícita para Traefik e ServiceLB |
| Bootstrap do ArgoCD | Ansible instala o ArgoCD e aplica AppProject e Application raiz enquanto excluídos da reconciliação |
| Entrada HTTP/HTTPS | NGINX Gateway Fabric exposto diretamente nas portas públicas 80/443, sem proxy HTTP externo obrigatório |
| Roteamento | Gateway API por meio de GatewayClass, Gateway e HTTPRoute; Services internos preferencialmente `ClusterIP` |
| CRDs e controllers | ArgoCD gerencia os CRDs do Gateway API, NGINX Gateway Fabric e demais recursos de infraestrutura, mediante permissões e ordem de sincronização apropriadas |
| Certificados TLS | cert-manager proposto, reconciliado pelo ArgoCD, com TLS terminado no Gateway Fabric |
| Secrets | GitHub Environment Secrets para o apply; Ansible Vault somente para conteúdo cifrado versionado; Secrets Kubernetes sob política específica |
| Recuperação | Acesso break-glass, backup, restauração testada e reconstrução documentada do k3s/ArgoCD |
| Concorrência | Um apply por host/ambiente por vez, sem cancelar execução em andamento |

## Fronteiras de responsabilidade

- **Terraform:** recursos externos — VPS, rede, IP, volumes, DNS e firewall do provedor — apenas se houver integração suportada. A disponibilidade para o plano HostGator atual precisa ser confirmada. Não administra a configuração recorrente do Ubuntu.
- **cloud-init:** prepara exclusivamente o acesso inicial em uma VPS nova quando houver suporte a `user-data`; não substitui o Ansible.
- **Ansible:** administra Ubuntu, usuários, SSH, pacotes, permissões, firewall local, serviços e agentes do host; instala, configura e mantém o **k3s single-node**; realiza o bootstrap do ArgoCD e aplica os objetos de bootstrap explicitamente excluídos da reconciliação.
- **GitHub Actions:** executa verificações e orquestra o apply com aprovação e credenciais protegidas; não se torna proprietário dos recursos do host ou Kubernetes.
- **ArgoCD:** reconcilia Applications filhas, recursos de infraestrutura Kubernetes, CRDs do Gateway API, NGINX Gateway Fabric, cert-manager, recursos Gateway API, aplicações e observabilidade do cluster. Não instala o k3s nem configura o sistema operacional da VPS.

### Bootstrap de infraestrutura do Gateway

A criação dos CRDs e de recursos de escopo de cluster exige **permissões adequadas**. O AppProject usado para workloads das aplicações não deve receber permissões amplas apenas para permitir a instalação do Gateway Fabric. Na implementação, criar ou adaptar uma Application/um AppProject de infraestrutura, com destinos e recursos de cluster estritamente necessários.

A ordem deverá garantir que os CRDs estejam disponíveis **antes** do controller ou dos objetos que deles dependam, conforme os requisitos de cada componente e os mecanismos de ordenação do ArgoCD. O cert-manager e seus próprios CRDs também exigem essa validação. As Applications filhas de produtos continuam sujeitas à política de sincronização definida para cada ambiente.

### Entrada pública sem proxy HTTP externo

```text
Internet / DNS
       |
       v
IP público da VPS — portas 80/443
       |
       v
NGINX Gateway Fabric (TLS / data plane)
       |
       v
Gateway API / HTTPRoute
       |
       v
Services ClusterIP
       |
       v
Pods das aplicações APAE
```

A forma concreta de publicar o data plane em 80/443 deve ser validada no k3s single-node, incluindo possíveis conflitos com o **Traefik** e o **ServiceLB**, segurança de rede e comportamento após reinício. A exposição direta **não exige** um NodePort de comunicação com NGINX no host.

A alternativa **NGINX externo + Gateway API** permanece registrada no estudo de NGINX como opção não selecionada. Sua adoção futura exigirá requisito operacional concreto e nova revisão da divisão de responsabilidades.

## Organização proposta

```text
ansible/
  ansible.cfg
  requirements.yml
  inventories/<ambiente>/hosts.yml
  inventories/<ambiente>/group_vars/
  playbooks/site.yml
  playbooks/bootstrap.yml
  roles/base/
  roles/users/
  roles/ssh/
  roles/firewall/
  roles/kubernetes/
  roles/argocd_bootstrap/
  roles/observability/
  README.md

.github/workflows/
  ansible-ci.yml
  ansible-apply.yml
```

As roles `nginx/` e `certbot/` **não integram a estrutura padrão proposta**. O controller NGINX Gateway Fabric e o cert-manager são componentes do cluster, gerenciados pelo fluxo GitOps. Inventários não conterão credenciais, e as dependências terão versões fixadas.

## Rede do runner e segurança

Preferir VPN, bastion ou outro caminho privado quando existir suporte. Não abrir SSH irrestrito à Internet nem executar runner privilegiado de produção na própria VPS administrada. Caso o acesso público restrito seja a única opção, documentar origens permitidas, limitações dos IPs de runners hospedados, monitoramento e recuperação.

Utilizar chave SSH dedicada em Environment Secret, validação confiável de `known_hosts`, usuário de automação com `become` somente quando necessário e procedimentos de rotação. O usuário que administra o host é privilegiado; não presumir isolamento forte por simples uso do Ansible Vault.

A política de firewall do Ubuntu deve ser compatível com as redes do k3s. A documentação do k3s recomenda desabilitar o UFW ou configurá-lo explicitamente para permitir a comunicação dos pods e Services. Não presumir que o UFW, isoladamente, bloqueie NodePorts. Restringir a API Kubernetes (`6443/tcp`) às origens administrativas necessárias e testar o acesso após alterações.

## Validação e aplicação

Em Pull Requests, executar `ansible-lint`, validação YAML e `ansible-playbook --syntax-check`, sem credenciais de produção. O `--check` remoto somente poderá ser executado em ambiente isolado de teste.

Após merge na `main`, um workflow acionado pelos caminhos monitorados ou por `workflow_dispatch` autorizado executa o apply com GitHub Environment `production` protegido, verificação de branch, revisão, dependências fixadas, validação de host SSH e serialização por host. O **Environment não substitui a revisão de código**, e o disparo manual não pode executar refs ou comandos arbitrários.

Alterações de SSH e firewall exigem validação antes de perder a conexão administrativa. Atualizações do Ubuntu e do k3s exigem procedimento próprio, janela de manutenção e backup. Reverter um commit não garante desfazer automaticamente uma atualização destrutiva, de schema ou do datastore.

## Riscos e limitações

- **VPS single-node:** a queda do host ou a manutenção do k3s pode indisponibilizar todos os serviços; a arquitetura não fornece alta disponibilidade.
- **Sistema operacional:** Ubuntu 22.04 LTS tem suporte padrão até maio de 2027; planejar upgrade para versão suportada ou confirmar cobertura estendida, com testes e backup.
- **Exposição pública:** a estratégia para disponibilizar Gateway Fabric nas portas 80/443 e o tratamento de Traefik/ServiceLB ainda devem ser validados. Serviços internos não devem ser publicados acidentalmente.
- **Instalação GitOps:** CRDs, controller, AppProject e Applications de infraestrutura exigem permissões e ordem de reconciliação adequadas.
- **TLS:** certificados dependem de DNS, validação ACME, renovação monitorada e estratégia de recuperação de Secrets ou reemissão.
- **Segurança do k3s:** regras de UFW, NAT, redes de pods e Services e acesso à API precisam ser testados; UFW não deve ser tratado como única defesa para NodePort.
- **SSH e automação:** mudanças indevidas podem causar lockout; segredos ou runner comprometidos dão acesso privilegiado ao host.
- **Convergência:** Ansible é executado quando acionado, não um controller de reconciliação contínua. Drift requer detecção e novo apply.
- **Bootstrap do ArgoCD:** AppProject e Application raiz excluídos da raiz não são reconciliados por ela; manter procedimento de atualização e recuperação pelo Ansible.
- **Backups:** playbooks reconstroem configurações, mas não restauram automaticamente volumes, bancos de dados ou o datastore Kubernetes.

## Definições para a fase de implementação

Esses detalhes não impedem a conclusão do estudo, mas devem ser resolvidos antes da entrada em produção.

| Tema | Definição necessária |
| --- | --- |
| SSH inicial | Porta, fingerprint obtido por canal confiável, credencial inicial e recuperação |
| Conectividade do runner | VPN/bastion ou acesso restrito validado, com aceitação documentada de riscos |
| Validação remota | Host de teste isolado ou CI apenas estática até o apply protegido |
| k3s | Versão fixa, configuração de rede, datastore, Traefik, ServiceLB e política de upgrade |
| Gateway público | Método de exposição de 80/443, firewall, IP real e ausência de rotas internas inadvertidamente públicas |
| ArgoCD e infraestrutura | Ordem de instalação dos CRDs/controllers; Applications e AppProjects com permissões corretas |
| DNS e certificados | Domínio, ACME, cert-manager, integração com Gateway Fabric, alertas e reemissão |
| Observabilidade | Logs, métricas, alertas e health checks do host, k3s e Gateway |
| Backups | Destino externo, retenção, criptografia, cópia do datastore e restauração testada |
| Manutenção do SO | Atualizações, reboots, plano de upgrade LTS e janelas de intervenção |

## Próximos passos de implementação

1. Confirmar no servidor/HostGator a porta e fingerprint SSH, acesso de recuperação, API de provisionamento, `user-data`, firewall de rede e opções de conectividade privada.
2. Planejar versão, rede, datastore, backup e instalação do **k3s single-node** conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90), incluindo a política de Traefik e ServiceLB.
3. Consolidar a divisão Terraform/Ansible/ArgoCD e a relação com a decisão anterior na [issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86).
4. Implementar a estrutura `ansible/`, com inventários não sensíveis, dependências fixadas, roles de host, CI estática e plano de bootstrap seguro.
5. Configurar acesso administrativo com chave SSH dedicada e aplicar hardening e firewall compatíveis com k3s, preservando um acesso de recuperação.
6. Instalar e validar o k3s; registrar versões, parâmetros e verificações de conectividade.
7. Instalar ArgoCD pelo Ansible; aplicar AppProject e Application raiz e testar a recuperação desses objetos sem ownership concorrente.
8. Criar o escopo GitOps de infraestrutura, com permissões necessárias para CRDs, controller NGINX Gateway Fabric, cert-manager e recursos Gateway API, respeitando a ordem de instalação.
9. Configurar a **exposição direta** do Gateway Fabric nas portas 80/443 e validar TLS, redirects, roteamento por HTTPRoute e proteção de serviços internos, conforme a [issue #60](https://github.com/IFPBEsp/APAE-INFRA/issues/60).
10. Validar as particularidades das aplicações, especialmente os Route Handlers do APAE Geral e a adaptação do frontend APAE Atendimento para `/atendimento`.
11. Implantar observabilidade, health checks, monitoramento de certificados, backups e testes de restauração; definir janelas de atualização do Ubuntu e do k3s.
12. Habilitar o workflow de apply após merge na `main`, com Environment protegido, inputs controlados, serialização e trilha de auditoria.
13. Atualizar os guias Terraform, Kubernetes, ArgoCD e README para representar os recursos efetivamente implementados.

## Referências relacionadas

- [Issue #59 — Arquitetura GitOps para Terraform e ArgoCD](https://github.com/IFPBEsp/APAE-INFRA/issues/59)
- [Issue #60 — Arquitetura do proxy reverso NGINX](https://github.com/IFPBEsp/APAE-INFRA/issues/60)
- [Issue #86 — Divisão do escopo Terraform, Ansible e ArgoCD na HostGator](https://github.com/IFPBEsp/APAE-INFRA/issues/86)
- [Issue #90 — Provisionar cluster Kubernetes com k3s](https://github.com/IFPBEsp/APAE-INFRA/issues/90)
- [Estudo de NGINX e Gateway API](../nginx/README.md)
- [Terraform](../boas-praticas/03-terraform.md) · [GitHub Actions](../boas-praticas/07-github-actions.md) · [Secrets](../boas-praticas/02-segredos-e-credenciais.md)
- [Fluxo documentado do ArgoCD](../argocd/fluxo-argocd.md)
- HostGator: [acesso SSH à VPS](https://suporte.hostgator.com.br/hc/pt-br/articles/30812824748051-Como-acessar-um-servidor-via-SSH) e [firewall via WHM](https://www.hostgator.com.br/blog/como-abrir-e-fechar-portas-em-um-servidor-da-hostgator/).
