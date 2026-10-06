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
- pré-requisitos e instalação da distribuição Kubernetes, depois de decididas distribuição e topologia;
- ferramentas auxiliares e agentes de observabilidade instalados no host.

O Ansible não deve gerenciar os workloads Kubernetes que pertencem ao ArgoCD. Uma ferramenta deve ser definida como proprietária de cada recurso; recursos de rede do provedor são Terraform, enquanto regras locais do host são Ansible.

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
Terraform → provisiona recursos do provedor somente onde existir integração suportada
cloud-init → prepara acesso inicial em novas instâncias somente se user-data estiver disponível
Ansible → configura o host e os serviços externos ao cluster
ArgoCD → reconcilia recursos dentro do Kubernetes
GitHub Actions → valida e orquestra Terraform e Ansible
```

## Decisões ainda necessárias para implementação

HostGator, plano VPS simples sem painel e Ubuntu 22.04 LTS são conhecidos para a VPS atual. Ainda precisam ser confirmados disponibilidade de API de provisionamento e user-data/cloud-init, existência de firewall de rede externo ao host, conectividade privada, topologia do cluster e distribuição Kubernetes. Para a instância atual, o firewall do Ubuntu é o escopo de Ansible. Esses pontos restantes condicionam Terraform, reconstrução, inventários, portas e conectividade do runner. Preferir VPN/bastion/rede privada quando disponível; não abrir SSH irrestrito nem instalar o runner de produção na própria VPS alvo.

Referências do provedor: [sistemas operacionais e acesso root da VPS](https://suporte.hostgator.com.br/hc/pt-br/articles/30816739471123-Como-come%C3%A7ar-a-usar-a-VPS-na-HostGator) e [acesso SSH em VPS Linux](https://suporte.hostgator.com.br/hc/pt-br/articles/30812824748051-Como-acessar-um-servidor-via-SSH).

Referência de suporte Ubuntu: [ciclo de vida do Ubuntu 22.04 LTS](https://ubuntu.com/about/release-cycle?product=ubuntu&release=ubuntu&version=22.04+LTS).

## Referências

- [Divisão de responsabilidades](03-divisao-de-responsabilidades.md)
- [Bootstrap da VPS](04-bootstrap-da-vps.md)
- [Fluxo GitHub Actions + Ansible](06-fluxo-github-actions-e-ansible.md)
- [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)
