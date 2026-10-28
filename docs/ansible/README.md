# Estudo de Ansible para gerenciamento da VPS

Este diretório reúne o estudo arquitetural da adoção do **Ansible** no projeto APAE-INFRA.

O objetivo é definir como o Ansible participa do gerenciamento da VPS HostGator, quais responsabilidades pertencem ao Terraform, ao GitHub Actions e ao ArgoCD, e como evoluir para uma operação reproduzível, idempotente e segura.

**Status:** estudo arquitetural concluído, com arquitetura-alvo definida para **k3s single-node** e entrada HTTP/HTTPS por **NGINX Gateway Fabric com Gateway API exposto diretamente**. Os componentes ainda dependem de implementação, testes e validação operacional; este estudo não afirma que a infraestrutura já esteja implantada.

## Documentos

1. [Contexto e requisitos](./01-contexto-e-requisitos.md)
2. [Comparação das alternativas](./02-comparacao-das-alternativas.md)
3. [Divisão de responsabilidades](./03-divisao-de-responsabilidades.md)
4. [Bootstrap da VPS](./04-bootstrap-da-vps.md)
5. [Secrets, SSH e segurança](./05-secrets-ssh-e-seguranca.md)
6. [Fluxo GitHub Actions + Ansible](./06-fluxo-github-actions-e-ansible.md)
7. [Arquitetura proposta e próximos passos](./07-arquitetura-proposta-e-proximos-passos.md)

## Ordem recomendada de leitura

A leitura foi dividida em documentos curtos para separar contexto, alternativas, responsabilidades, bootstrap, segurança e operação:

```text
01 → 02 → 03 → 04 → 05 → 06 → 07
```

O documento **07** consolida a arquitetura proposta e as decisões que orientam a implementação.

A decisão está registrada no [ADR 004 — Adoção de Ansible com GitHub Actions](../adr/004-adocao-ansible-github-actions.md).

## Arquitetura consolidada

A infraestrutura prevista utiliza uma VPS HostGator com cluster **k3s single-node**. A entrada pública HTTP/HTTPS será realizada diretamente pelo **NGINX Gateway Fabric**, mediante recursos **Gateway API**, sem exigir um NGINX adicional instalado no host.

```text
Internet / DNS
      |
      | HTTPS :443 (e HTTP :80 para redirecionamento)
      v
VPS HostGator — k3s single-node
      |
      v
NGINX Gateway Fabric
      | TLS e processamento HTTP/HTTPS
      v
Gateway / HTTPRoute
      |
      v
Services ClusterIP
      |
      v
Aplicações APAE
```

A exposição das portas 80/443, o tratamento do Traefik e do ServiceLB, o gerenciamento de certificados com **cert-manager** e a ordenação da instalação dos CRDs/controllers serão definidos e validados na implementação, conforme o [estudo de NGINX](../nginx/README.md).

O NGINX externo e o Certbot no host foram estudados como alternativa, mas **não compõem o escopo obrigatório da implementação inicial**. Sua eventual adoção exigiria um requisito operacional concreto e uma revisão da decisão arquitetural.

## Escopo do Ansible

O estudo considera principalmente:

- configuração e manutenção do sistema operacional da VPS;
- usuários administrativos, SSH, privilégios, pacotes, diretórios e serviços do host;
- firewall local e validação da conectividade do k3s, sem presumir que o UFW sozinho bloqueia NodePorts;
- instalação, configuração, versionamento e manutenção do **k3s single-node**, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90);
- bootstrap inicial do **ArgoCD**, incluindo AppProject e Application raiz, enquanto esses objetos permanecerem fora do caminho reconciliado;
- agentes e serviços de observabilidade executados diretamente no host;
- automação e aprovação de mudanças com **GitHub Actions + Ansible**;
- procedimentos de recuperação, backups, validação e intervenções emergenciais controladas.

## Divisão de responsabilidades

| Ferramenta | Responsabilidade principal |
| --- | --- |
| **Terraform** | Recursos externos da infraestrutura, somente quando houver API/provider compatível com o plano HostGator; disponibilidade ainda a confirmar. |
| **cloud-init** | Acesso inicial em novas instâncias, apenas se o provedor oferecer suporte a user-data. |
| **Ansible** | Configuração do host, firewall local, instalação e manutenção do k3s e bootstrap do ArgoCD. |
| **GitHub Actions** | Validação, orquestração e aprovação de execuções Ansible; não gerencia diretamente o estado da VPS. |
| **ArgoCD** | Reconciliação das Applications filhas e dos componentes Kubernetes, incluindo Gateway API, NGINX Gateway Fabric, cert-manager e workloads, com permissões e ordem de implantação adequadas. |

O AppProject e a Application raiz permanecem sob responsabilidade do bootstrap Ansible enquanto estiverem excluídos da reconciliação do ArgoCD. A proposta atualiza a atribuição de bootstrap prevista no estudo anterior de Terraform; a consolidação entre os estudos será tratada na [issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86).

## Fluxo de aplicação em produção

As alterações passam por validações estáticas em Pull Requests para `dev`. Um merge em `dev` **não executa mudanças na VPS de produção**.

A aplicação em produção somente poderá utilizar código integrado à branch `main`, com restrição de branch no GitHub Environment `production`, aprovação de responsáveis autorizados e credenciais fornecidas exclusivamente ao job de apply. Execuções manuais por `workflow_dispatch` devem respeitar as mesmas restrições.

O mecanismo detalhado está no [documento 06](./06-fluxo-github-actions-e-ansible.md).

## Fora do escopo do Ansible

O Ansible **não** será responsável pela reconciliação contínua dos workloads Kubernetes nem pela configuração direta das rotas HTTPRoute. Esses recursos pertencem ao ArgoCD após o bootstrap.

Também não assumirá o gerenciamento contínuo de certificados TLS do Gateway: a estratégia prevista utiliza cert-manager dentro do Kubernetes, a ser validada na implementação.

O Terraform não deve ser considerado capaz de provisionar os recursos da HostGator sem confirmação de integração suportada. A criação manual de recursos não automatizáveis deverá ser registrada como exceção operacional.

## Referências relacionadas

- [Estudo de NGINX e Gateway API](../nginx/README.md)
- [Fluxo do ArgoCD](../argocd/fluxo-argocd.md)
- [Issue #59 — Estudo de Terraform e ArgoCD](https://github.com/IFPBEsp/APAE-INFRA/issues/59)
- [Issue #60 — Arquitetura NGINX e proxy reverso](https://github.com/IFPBEsp/APAE-INFRA/issues/60)
- [Issue #86 — Divisão de responsabilidades](https://github.com/IFPBEsp/APAE-INFRA/issues/86)
- [Issue #90 — k3s single-node](https://github.com/IFPBEsp/APAE-INFRA/issues/90)

## Resultado do estudo

> **Terraform gerencia recursos externos quando suportado; Ansible configura a VPS, instala o k3s e realiza o bootstrap do ArgoCD; GitHub Actions controla as execuções; ArgoCD reconcilia os componentes Kubernetes e o Gateway API.**
