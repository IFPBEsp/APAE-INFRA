# 01 — Contexto e requisitos

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Objetivo

Definir o estado operacional esperado da VPS e os requisitos para gerenciá-lo declarativamente. Este estudo é uma proposta arquitetural; não descreve uma implantação Ansible já existente.

## Contexto

O ambiente atual está em uma VPS **simples da HostGator, sem painel, com Ubuntu 22.04 LTS**. A HostGator documenta acesso root via SSH para VPS Linux; confirmar a porta e a identidade SSH da instância antes de automatizar. O APAE-INFRA mantém documentação e manifests de Kubernetes, além de orientações para Terraform e ArgoCD. A estrutura de implementação ainda está incompleta: não há playbooks/workflows Ansible nem configurações Terraform de ambiente ou Applications do ArgoCD no repositório. A seção [Estado atual e arquitetura proposta](07-arquitetura-proposta-e-proximos-passos.md#estado-atual-e-arquitetura-proposta) detalha essa diferença.

## Componentes da VPS sob gerenciamento

O Ansible deverá manter o estado do host e dos serviços externos ao cluster:

- sistema operacional, atualizações de segurança, timezone, pacotes, diretórios e permissões;
- usuários administrativos e de serviço, grupos, `sudo`, chaves públicas e configuração SSH;
- firewall local, em coordenação com as regras de rede do provedor;
- NGINX externo, configuração de proxy e serviço `systemd`;
- Certbot, renovação de certificados e reload validado do NGINX;
- pré-requisitos, instalação, configuração e manutenção do cluster Kubernetes k3s single-node, conforme a issue #90, incluindo versionamento, configuração de rede e definição sobre o Traefik integrado;
- ferramentas auxiliares e agentes de observabilidade instalados no host.

O Ansible é responsável pela configuração da VPS, pela instalação e manutenção do k3s single-node e pelo bootstrap inicial do ArgoCD, incluindo o AppProject e a Application raiz enquanto esses objetos permanecerem fora do caminho reconciliado.

O ArgoCD é responsável pelas Applications filhas e pelos recursos Kubernetes atribuídos a elas. A arquitetura proposta também atribui ao ArgoCD a instalação declarativa dos CRDs do Gateway API, do NGINX Gateway Fabric e dos recursos GatewayClass, Gateway e HTTPRoute, respeitando a ordem de instalação das dependências.

O NGINX externo e o Certbot permanecem sob responsabilidade do Ansible. O NGINX do host será responsável pelas portas públicas 80/443 e encaminhará o tráfego para o endpoint interno do Gateway.

Cada recurso deve possuir uma ferramenta proprietária, evitando sobreposição entre Terraform, Ansible e ArgoCD. O Terraform gerencia recursos do provedor somente quando existir integração suportada, enquanto o Ansible mantém as configurações locais do host.

## Requisitos de qualidade

- **Idempotência:** execuções repetidas convergem para o mesmo estado, preferindo módulos declarativos a comandos shell.
- **Reprodutibilidade:** uma máquina nova alcança o estado declarado sem conhecimento operacional não documentado.
- **Segurança:** credenciais fora do Git em claro, acesso SSH restrito, privilégios mínimos e logs sem segredos.
- **Auditabilidade:** PR, revisão, commit, aprovação e execução formam o registro de cada mudança.
- **Validação:** lint e sintaxe antes do merge; validação específica de serviços antes de reload/restart.
- **Recuperação:** mudanças em SSH, firewall e serviços críticos preservam um caminho de console/recuperação e procedimento de rollback.

## Ciclo de vida do sistema operacional

Ubuntu 22.04 LTS está no ciclo de suporte padrão até maio de 2027. O plano de configuração deve incluir uma atualização suportada para uma LTS posterior antes desse marco ou confirmar cobertura de segurança estendida. A atualização de versão não deve ser tratada como `apt upgrade` rotineiro: exige plano, backup, validação de compatibilidade Kubernetes e janela de manutenção.

## Fluxo esperado

```text
Terraform → recursos externos com integração suportada
cloud-init → acesso inicial em novas VPS, se suportado
Ansible → host, NGINX externo, Certbot, k3s e bootstrap ArgoCD
ArgoCD → Gateway API, NGINX Gateway Fabric e workloads Kubernetes
GitHub Actions → validação, aprovação e orquestração
```

## Decisões ainda necessárias para implementação

A VPS atual utiliza a HostGator, em plano simples sem painel, com Ubuntu 22.04 LTS. A arquitetura prevista para o cluster é k3s single-node, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90).

Ainda precisam ser confirmados os seguintes aspectos operacionais:

- disponibilidade de API de provisionamento e suporte a user-data/cloud-init;
- existência de firewall de rede externo ao host;
- conectividade privada entre o GitHub Actions e a VPS;
- versão fixa do k3s e seus parâmetros de instalação;
- política de manutenção ou desabilitação do Traefik integrado ao k3s;
- endpoint interno entre o NGINX externo e o Gateway no cluster;
- instalação e ordenação dos CRDs do Gateway API e do NGINX Gateway Fabric;
- configuração de inventários, portas e acesso administrativo;
- mecanismos de backup, recuperação e atualização do sistema operacional.

Para a VPS atual, o firewall local do Ubuntu pertence ao Ansible.

A arquitetura de entrada proposta considera NGINX externo e Gateway API dentro do cluster, conforme o estudo da [issue #60](https://github.com/IFPBEsp/APAE-INFRA/issues/60).

A divisão definitiva entre Terraform, Ansible e ArgoCD deverá ser consolidada com o time, conforme a [issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86).

Preferir VPN, bastion ou rede privada quando disponíveis. Não abrir SSH irrestrito à Internet nem executar o runner privilegiado de produção na própria VPS administrada.

## Referências

- [Divisão de responsabilidades](03-divisao-de-responsabilidades.md)
- [Bootstrap da VPS](04-bootstrap-da-vps.md)
- [Fluxo GitHub Actions + Ansible](06-fluxo-github-actions-e-ansible.md)
- [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)
