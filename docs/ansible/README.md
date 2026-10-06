# Estudo de Ansible para gerenciamento da VPS

Este diretório reúne o estudo arquitetural da adoção do **Ansible** no projeto APAE-INFRA.

O objetivo é definir como o Ansible deve participar do gerenciamento da VPS, quais responsabilidades permanecem com Terraform, GitHub Actions e ArgoCD e como a automação poderá evoluir para uma operação reproduzível, idempotente e segura.

**Status:** estudo arquitetural concluído. As definições específicas do plano HostGator, da topologia Kubernetes, do acesso de rede e das políticas operacionais ficam para as tarefas de implementação; não são bloqueios para esta recomendação.

## Documentos

1. [Contexto e requisitos](./01-contexto-e-requisitos.md)
2. [Comparação das alternativas](./02-comparacao-das-alternativas.md)
3. [Divisão de responsabilidades](./03-divisao-de-responsabilidades.md)
4. [Bootstrap da VPS](./04-bootstrap-da-vps.md)
5. [Secrets, SSH e segurança](./05-secrets-ssh-e-seguranca.md)
6. [Fluxo GitHub Actions + Ansible](./06-fluxo-github-actions-e-ansible.md)
7. [Arquitetura proposta e próximos passos](./07-arquitetura-proposta-e-proximos-passos.md)

## Ordem recomendada de leitura

A leitura foi dividida em documentos curtos para separar contexto, decisões e implementação:

01 → 02 → 03 → 04 → 05 → 06 → 07

O documento 07 consolida a recomendação arquitetural resultante do estudo.

## Escopo

Este estudo considera principalmente:

- configuração e manutenção do sistema operacional da VPS;
- usuários, SSH e privilégios;
- pacotes e serviços;
- firewall local;
- NGINX e Certbot;
- instalação e configuração do Kubernetes;
- componentes de observabilidade instalados no host;
- execução controlada pelo GitHub Actions;
- execução manual para operações de emergência;
- segurança, idempotência e validação das mudanças.

## Fora do escopo

O Ansible não deve assumir responsabilidades já atribuídas ao ArgoCD, como a reconciliação dos recursos e workloads internos do Kubernetes.

Da mesma forma, a criação da infraestrutura externa da VPS permanece no domínio do Terraform.

## Resultado do estudo

O estudo define uma arquitetura para responder:

> **O que cria a infraestrutura, o que configura a máquina, o que reconcilia o Kubernetes e o que orquestra as mudanças?**
