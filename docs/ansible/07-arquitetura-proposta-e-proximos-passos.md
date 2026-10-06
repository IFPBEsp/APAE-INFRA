# 07 — Arquitetura proposta e próximos passos

[← Índice do estudo](README.md)

Este documento consolida as decisões do estudo e é a referência normativa para implementação. Os documentos 01–06 explicam requisitos, alternativas, ownership, bootstrap, segurança e fluxo operacional.

## Recomendação

Adotar **Ansible + GitHub Actions** para configurar a VPS existente e **Terraform** para recursos HostGator apenas se houver integração de provisionamento suportada pelo plano. Para uma VPS futura, cloud-init entra somente se user-data for suportado. Usar **ArgoCD** para reconciliar os recursos Kubernetes atribuídos às Applications filhas. Git é a fonte da configuração permanente; as definições bootstrap excluídas da raiz permanecem sob o playbook Ansible.

```text
Git / APAE-INFRA
  ├── Terraform → recursos HostGator com API suportada (a confirmar)
  ├── cloud-init → usuário/chave/acesso inicial em instância futura, se suportado
  ├── Ansible → SO, SSH, firewall local, NGINX, Certbot, serviços e Kubernetes
  └── manifests Kubernetes → ArgoCD → recursos e workloads do cluster

GitHub Actions → valida e orquestra Terraform e Ansible
```

## Estado atual e arquitetura proposta

Este estudo descreve uma arquitetura-alvo, não uma implantação concluída.

| Área | Estado observado no repositório | Proposta |
| --- | --- | --- |
| Ansible | Não há playbooks, roles, inventários ou workflow Ansible | Criar estrutura `ansible/`, CI estática e apply protegido |
| Terraform | Há documentação/README, mas não configurações de ambientes ou recursos | Avaliar integração de provisionamento com a VPS simples HostGator; não presumir API Terraform ou user-data cloud-init |
| Kubernetes | Há manifests em `kubernetes/apae-geral/base`; overlays anunciados no README não estão presentes na estrutura atual | Definir ambientes/topologia e manter manifests de cluster sob GitOps |
| ArgoCD | Há documentação de fluxo, mas não manifests de Applications no diretório `argocd/` | Bootstrap instala ArgoCD, aplica AppProject e Application raiz; ArgoCD reconcilia filhas, enquanto os objetos excluídos da raiz continuam sob Ansible |
| Observabilidade | Há diretórios e documentação, mas a instalação deve ser atribuída por camada | Ansible para agentes do host; ArgoCD para workloads Kubernetes |

Documentos, workflows ou diretórios vazios não devem ser tratados como automação implantada. Antes de implementação, reconciliar o README e os guias de ambiente com a estrutura que será efetivamente criada.

## Decisões arquiteturais

| Tema | Decisão |
| --- | --- |
| Configuration management do host | Ansible idempotente, com playbooks/roles versionados |
| Orquestração normal | GitHub Actions + Ansible |
| PR | YAML/lint/syntax-check estáticos; sem secrets de produção e sem conexão à VPS |
| Apply de produção | Disparo após merge; execução aguarda aprovação no Environment protegido |
| Apply manual | `workflow_dispatch` com inputs permitidos; mesma proteção de produção |
| `--check` remoto | Somente contra ambiente de teste isolado; omitir se esse ambiente não existir |
| Bootstrap da VPS | VPS atual: uma execução inicial controlada a partir de estação autorizada para criar acesso Ansible; nova VPS: Terraform + cloud-init mínimo somente se suporte HostGator for confirmado |
| Bootstrap do ArgoCD | Playbook Ansible separado instala ArgoCD, aplica AppProject e registra a raiz; como o guia exclui `project.yaml` e `app-of-apps.yaml` da raiz, mudanças nesses objetos também passam pelo playbook; Applications filhas ficam com ArgoCD |
| Borda HTTP/HTTPS | NGINX externo à VPS termina TLS e é dono das portas públicas 80/443; encaminha ao endpoint interno do cluster |
| Secrets | GitHub Environment Secrets para runtime; Ansible Vault só se conteúdo cifrado precisar ser versionado |
| Emergência | SSH break-glass controlado; registrar e converter mudança em PR para reconciliar via Ansible |
| Concorrência | Uma aplicação por host/ambiente de cada vez, sem cancelar apply já iniciado |

## Fronteiras de responsabilidade

- **Terraform:** VPS, rede, IP, volume, DNS e firewall do provider somente quando houver provider/API compatível. Para a VPS HostGator atual, essa compatibilidade não está confirmada; se o provisionamento depender do portal, registrar como exceção e manter Terraform fora desses recursos. Não configurar continuamente o sistema operacional.
- **cloud-init:** somente acesso inicial; não manter NGINX, firewall ou Kubernetes.
- **Ansible:** usuários, SSH, sistema operacional, pacotes, firewall local, NGINX, Certbot, systemd, diretórios, permissões, agentes e instalação Kubernetes conforme decisões futuras.
- **GitHub Actions:** validação, aprovação, entrega de credenciais necessárias e orquestração. Não contém comandos paralelos que definam a configuração do host.
- **ArgoCD:** Applications filhas e recursos atribuídos a elas depois do bootstrap. Não gerenciar o host nem a instalação base do cluster. O AppProject e a Application raiz ficam no playbook enquanto continuarem excluídos do path reconciliado.

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
  roles/nginx/
  roles/certbot/
  roles/kubernetes/
  roles/argocd_bootstrap/
  roles/observability/
  README.md

.github/workflows/
  ansible-ci.yml
  ansible-apply.yml
```

Inventários não contêm credenciais. Dependências e versões devem ser fixadas. Os nomes/ambientes definitivos dependem da topologia escolhida.

## Rede do runner e segurança

Preferir conectividade privada via VPN/bastion ou mecanismo gerenciado pelo provider. Não abrir SSH irrestrito à internet, aceitar host keys sem validação ou instalar o runner privilegiado na VPS que ele administra. HostGator é o provider atual, mas o plano/capacidade de rede desta VPS ainda precisa ser confirmado; se apenas runner hospedado e SSH público restrito forem viáveis, registrar os limites de IP de origem, exposição residual, monitoramento e recuperação antes de adotar.

Usar chave SSH dedicada e Environment Secret de produção, `known_hosts` obtido por canal confiável e `become` somente para tarefas administrativas. O usuário Ansible precisará de privilégio administrativo amplo para instalar pacotes, firewall e serviços; não declarar privilégio mínimo granular onde ele não existe. Vault cifra dados versionados, mas a chave de descriptografia nunca acompanha o conteúdo cifrado.

## Validação e aplicação

Em PR, executar lint de Ansible, syntax-check e validações estáticas sem credenciais de host. `--check` remoto só roda em ambiente de teste; ele não substitui aplicação real nem representa todos os módulos. Após merge, o job de apply usa Environment protegido, approval reviewer, dependências fixadas, inventário explícito, serialização por host e logs sem segredos.

Configuração NGINX candidata deve passar por `nginx -t` antes de ativação e reload. SSH/firewall precisam de sessão/caminho de recuperação. Uma falha Ansible pode deixar mudanças parciais: rollback de host via commit revertido + Ansible; rollback de infraestrutura via Terraform; rollback de workloads via ArgoCD.

## Riscos e limitações

- A VPS atual é HostGator simples, sem painel, com Ubuntu 22.04 LTS. A documentação consultada descreve acesso root SSH para VPS Linux; ainda é necessário confirmar porta e host key da instância, API Terraform, user-data cloud-init e conectividade privada. A ferramenta HG Firewall Administration exige WHM e não se aplica a este plano; não está confirmado firewall de rede externo. Topologia e distribuição Kubernetes seguem abertas. Sem esses detalhes não se deve fechar inventário, portas, instalação Kubernetes ou caminho de rede do runner.
- Ubuntu 22.04 LTS tem suporte padrão até maio de 2027; planejar upgrade LTS com antecedência ou confirmar cobertura estendida. Validar compatibilidade do Kubernetes e organizar janela/backup antes do upgrade.
- Endpoint interno entre NGINX e cluster depende da distribuição/topologia; Ingress Controller não pode competir pelas portas públicas do NGINX.
- Certificados dependem de DNS, validação ACME, conectividade pública e monitoramento da renovação.
- Alterações SSH/firewall podem causar lockout; exigem aplicação gradual e recuperação fora da sessão remota.
- Actions centraliza o processo, mas aumenta o impacto de comprometimento dos secrets ou runner; usar Environment, permissões mínimas, dependências fixadas e rotação.
- Ansible é executado sob demanda e não é um controller contínuo de reconciliação. Detectar drift depende de execuções regulares ou sob demanda.
- O bootstrap do ArgoCD é uma etapa privilegiada de transição; os objetos explicitamente excluídos da raiz não são reconciliados por ArgoCD. Manter ownership e execução desses objetos documentados para evitar drift e sobreposição.

## Definições para a fase de implementação

Os itens abaixo são detalhes operacionais a confirmar durante a implementação. Eles não bloqueiam a conclusão deste estudo arquitetural; cada decisão deverá ser registrada junto à tarefa que implementar o componente correspondente.

| Tema | O que precisa ser definido antes da operação de produção |
| --- | --- |
| Acesso SSH inicial | Porta real, fingerprint obtido por canal confiável, credencial root inicial e plano de recuperação |
| Conectividade de Actions | Se a HostGator permite acesso privado/VPN ou firewall de origem; caso não, definir runner com egress controlado e aceitar formalmente o risco de SSH público restrito |
| Validação remota | Criar um host não produtivo para `--check`/testes de roles ou aceitar apenas CI estática antes do apply aprovado |
| Atualizações do SO | Definir instalação automática/manual de security updates, janela de manutenção, política de reboot/kernel e responsabilidade por aplicar updates |
| Backup e restore | Definir dados/volumes/certificados/estado que precisam de backup, destino, retenção, criptografia e teste periódico de restauração; Ansible reconstrói configuração, mas não substitui backup de dados |
| DNS e certificados | Definir quem gerencia DNS, como validar ACME, quem monitora renovação e como recuperar material TLS |

## Próximos passos de implementação

1. Confirmar no portal/servidor a porta e fingerprint SSH; consultar HostGator sobre API de provisionamento, user-data/cloud-init, firewall de rede externo e acesso privado para o runner.
2. Definir topologia do cluster e distribuição Kubernetes.
3. Definir endpoint interno do NGINX, portas, dono do firewall, emissão/renovação TLS e acesso de recuperação.
4. Definir política de updates/reboots, backup/restore e se haverá host de teste.
5. Criar estrutura Ansible, fixar dependências e adicionar CI estática.
6. Planejar upgrade de Ubuntu 22.04 para uma LTS suportada ou confirmar cobertura Ubuntu Pro/ESM.
7. Implementar primeiro `base`, usuário administrativo, SSH e firewall em ambiente de teste, se disponível.
8. Implementar NGINX/Certbot e validação/reload seguro.
9. Implementar instalação Kubernetes e bootstrap ArgoCD depois das decisões de distribuição/topologia.
10. Adicionar apply pós-merge com Environment protegido, concorrência serial e logs sem secrets.
11. Atualizar README e guias Terraform/Kubernetes/ArgoCD para refletirem o estado efetivamente implantado.

## Referências relacionadas

- [Issue #59 — Arquitetura GitOps para Terraform e ArgoCD](https://github.com/IFPBEsp/APAE-INFRA/issues/59)
- [Issue #60 — Arquitetura do proxy reverso NGINX](https://github.com/IFPBEsp/APAE-INFRA/issues/60)
- [Terraform](../boas-praticas/03-terraform.md) · [GitHub Actions](../boas-praticas/07-github-actions.md) · [Secrets](../boas-praticas/02-segredos-e-credenciais.md)
- [Fluxo documentado do ArgoCD](../argocd/fluxo-argocd.md)
- HostGator: [acesso SSH à VPS](https://suporte.hostgator.com.br/hc/pt-br/articles/30812824748051-Como-acessar-um-servidor-via-SSH) e [firewall via WHM](https://www.hostgator.com.br/blog/como-abrir-e-fechar-portas-em-um-servidor-da-hostgator/).
