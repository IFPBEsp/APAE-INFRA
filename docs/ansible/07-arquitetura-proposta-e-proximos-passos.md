# 07 — Arquitetura proposta e próximos passos

[← Índice do estudo](README.md)

Este documento consolida as decisões do estudo e é a referência normativa para implementação. Os documentos 01–06 explicam requisitos, alternativas, ownership, bootstrap, segurança e fluxo operacional.

## Recomendação

Adotar **Ansible + GitHub Actions** para configurar a VPS existente e **Terraform** para recursos HostGator apenas se houver integração de provisionamento suportada pelo plano. Para uma VPS futura, cloud-init entra somente se user-data for suportado. A topologia planejada é **k3s single-node**, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90). Usar **ArgoCD** para reconciliar os recursos Kubernetes atribuídos às Applications filhas. Para a entrada HTTP/HTTPS, a proposta considera **NGINX no host e Gateway API no cluster**, com **NGINX Gateway Fabric** como controller a validar com o time no escopo da [issue #60](https://github.com/IFPBEsp/APAE-INFRA/issues/60). Git é a fonte da configuração permanente; as definições de bootstrap excluídas da raiz permanecem sob o playbook Ansible.

```text
Git / APAE-INFRA
  ├── Terraform → recursos HostGator com API suportada (a confirmar)
  ├── cloud-init → usuário/chave/acesso inicial em instância futura, se suportado
  ├── Ansible → SO, SSH, firewall local, NGINX, Certbot e k3s single-node
  └── manifests Kubernetes → ArgoCD → Gateway API, Gateway Fabric e workloads

GitHub Actions → valida e orquestra Terraform e Ansible
```

### Relação com a decisão arquitetural anterior

A proposta deste estudo atualiza, para a VPS HostGator, a divisão de responsabilidades definida no estudo de GitOps com Terraform da [issue #59](https://github.com/IFPBEsp/APAE-INFRA/issues/59).

Na decisão anterior, o Terraform era responsável conceitualmente pelo bootstrap do host, do Kubernetes e do ArgoCD. Neste estudo, essas atividades passam a ser atribuídas ao Ansible, em razão das limitações de integração com o provedor atual.

Também fica estabelecido que o AppProject e a Application raiz permanecem sob o playbook Ansible enquanto não forem reconciliados pelo ArgoCD. A reconciliação automática pelo ArgoCD começa nos recursos sob responsabilidade das Applications filhas.

Essa proposta substitui a atribuição anterior para o cenário da VPS atual, sem descartar o uso futuro do Terraform em recursos com API ou provider compatível.

A consolidação dessa mudança nos documentos de Terraform e sua validação arquitetural com o time fazem parte da [issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86).

## Estado atual e arquitetura proposta

Este estudo descreve uma arquitetura-alvo, não uma implantação concluída.

| Área | Estado observado no repositório | Proposta |
| --- | --- | --- |
| Ansible | Não há playbooks, roles, inventários ou workflow Ansible | Criar estrutura `ansible/`, CI estática e apply protegido |
| Terraform | A estrutura `terraform/` já possui os diretórios `environments/` e `modules/`, atualmente com arquivos README, mas sem módulos ou configurações de ambientes implementados | Definir o escopo efetivamente gerenciável por Terraform na HostGator, conforme a issue #86, e implementar recursos apenas quando houver integração suportada |
| Kubernetes | Já existem manifests organizados em `kubernetes/apae-geral/base`, `kubernetes/apae-atendimento/base` e `kubernetes/site-comemorativo/base`; a implantação no cluster ainda não foi comprovada | Adotar k3s single-node conforme a issue #90, definir a separação dos ambientes e integrar os recursos Kubernetes ao fluxo GitOps com ArgoCD |
| ArgoCD | Há documentação de fluxo, mas não manifests de Applications no diretório `argocd/` | Ansible instala ArgoCD, AppProject e Application raiz; ArgoCD reconcilia Applications filhas, Gateway API e workloads, enquanto objetos excluídos da raiz continuam sob Ansible |
| Entrada HTTP/HTTPS | A implementação de Gateway API e NGINX Gateway Fabric não foi confirmada neste estudo | Proposta: Ansible mantém NGINX externo e Certbot; ArgoCD instala CRDs do Gateway API, NGINX Gateway Fabric e recursos de roteamento, após decisão da #60 |
| Observabilidade | Há diretórios e documentação, mas a instalação deve ser atribuída por camada | Ansible para agentes do host; ArgoCD para workloads Kubernetes |

Documentos, workflows ou diretórios vazios não devem ser tratados como automação implantada. Antes de implementação, reconciliar o README e os guias de ambiente com a estrutura que será efetivamente criada.

## Decisões arquiteturais

| Tema | Decisão |
| --- | --- |
| Configuration management do host | Ansible idempotente, com playbooks/roles versionados |
| Orquestração normal | GitHub Actions + Ansible |
| PR | YAML/lint/syntax-check estáticos; sem secrets de produção e sem conexão à VPS |
| Apply de produção | Disparo somente após merge na `main`, mediante alterações nos caminhos monitorados pelo workflow Ansible, com aprovação obrigatória no GitHub Environment `production`; merges em `dev` não aplicam mudanças na VPS. |
| Apply manual | `workflow_dispatch` restrito à branch `main`, com inputs previamente autorizados e aprovação obrigatória no GitHub Environment `production`, configurado para permitir deployments somente da `main`. |
| `--check` remoto | Somente contra ambiente de teste isolado; omitir se esse ambiente não existir |
| Bootstrap da VPS | VPS atual: uma execução inicial controlada a partir de estação autorizada para criar acesso Ansible; nova VPS: Terraform + cloud-init mínimo somente se suporte HostGator for confirmado |
| Bootstrap do ArgoCD | Ansible instala o ArgoCD, aplica o AppProject e registra a Application raiz. Enquanto `project.yaml` e `app-of-apps.yaml` permanecerem fora do caminho reconciliado, suas alterações serão aplicadas pelo playbook. O ArgoCD reconcilia as Applications filhas e os recursos atribuídos a elas. |
| Borda HTTP/HTTPS | NGINX instalado na VPS, externo ao cluster Kubernetes, responsável pela terminação TLS e pelas portas públicas 80/443; encaminha o tráfego ao endpoint interno do NGINX Gateway Fabric no k3s |
| Distribuição Kubernetes | k3s single-node na VPS HostGator, conforme #90; definir versão fixada, acesso seguro e política sobre o Traefik embutido |
| Gateway API e controller | Proposta: ArgoCD instala os CRDs do Gateway API e o NGINX Gateway Fabric em ordem controlada; posteriormente reconcilia GatewayClass, Gateway e HTTPRoute. |
| Secrets | GitHub Environment Secrets para runtime; Ansible Vault só se conteúdo cifrado precisar ser versionado |
| Emergência | SSH break-glass controlado; registrar e converter mudança em PR para reconciliar via Ansible |
| Concorrência | Uma aplicação por host/ambiente de cada vez, sem cancelar apply já iniciado |

## Fronteiras de responsabilidade

- **Terraform:** VPS, rede, IP, volume, DNS e firewall do provider somente quando houver provider/API compatível. Para a VPS HostGator atual, essa compatibilidade não está confirmada; se o provisionamento depender do portal, registrar como exceção e manter Terraform fora desses recursos. Não configurar continuamente o sistema operacional.
- **cloud-init:** somente acesso inicial; não manter NGINX, firewall ou Kubernetes.
- **Ansible:** usuários, SSH, sistema operacional, pacotes, firewall local, NGINX externo, Certbot, systemd, diretórios, permissões, agentes e instalação/manutenção do k3s single-node conforme #90. Também instala o ArgoCD e mantém AppProject e Application raiz enquanto estiverem excluídos da reconciliação.
- **GitHub Actions:** validação, aprovação, entrega de credenciais necessárias e orquestração. Não contém comandos paralelos que definam a configuração do host.
- **ArgoCD:** Applications filhas e recursos atribuídos a elas depois do bootstrap. Na proposta para Gateway API, instala e atualiza declarativamente os CRDs, o controller NGINX Gateway Fabric e recursos GatewayClass, Gateway e HTTPRoute, com ordem de sincronização controlada. Não gerencia o host nem a instalação base do k3s. O AppProject e a Application raiz ficam no playbook enquanto continuarem excluídos do caminho reconciliado. Essa atribuição de Gateway API depende da validação arquitetural da #60.

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

Inventários não contêm credenciais. Dependências e versões devem ser fixadas. A topologia-base é k3s single-node, conforme #90; nomes dos ambientes, isolamento por namespaces e detalhes de conectividade ainda exigem definição.

## Rede do runner e segurança

Preferir conectividade privada via VPN/bastion ou mecanismo gerenciado pelo provider. Não abrir SSH irrestrito à internet, aceitar host keys sem validação ou instalar o runner privilegiado na VPS que ele administra. HostGator é o provider atual, mas o plano/capacidade de rede desta VPS ainda precisa ser confirmado; se apenas runner hospedado e SSH público restrito forem viáveis, registrar os limites de IP de origem, exposição residual, monitoramento e recuperação antes de adotar.

Usar chave SSH dedicada e Environment Secret de produção, `known_hosts` obtido por canal confiável e `become` somente para tarefas administrativas. O usuário Ansible precisará de privilégio administrativo amplo para instalar pacotes, firewall e serviços; não declarar privilégio mínimo granular onde ele não existe. Vault cifra dados versionados, mas a chave de descriptografia nunca acompanha o conteúdo cifrado.

## Validação e aplicação

Em PR, executar lint de Ansible, syntax-check e validações estáticas sem credenciais de host. `--check` remoto só roda em ambiente de teste; ele não substitui aplicação real nem representa todos os módulos. Após merge, o job de apply usa Environment protegido, approval reviewer, dependências fixadas, inventário explícito, serialização por host e logs sem segredos.

Configuração NGINX candidata deve passar por `nginx -t` antes de ativação e reload. SSH/firewall precisam de sessão/caminho de recuperação. Uma falha Ansible pode deixar mudanças parciais: rollback de host via commit revertido + Ansible; rollback de infraestrutura via Terraform; rollback de workloads via ArgoCD.

## Riscos e limitações

- A VPS atual é HostGator simples, sem painel, com Ubuntu 22.04 LTS. A documentação consultada descreve acesso root SSH para VPS Linux; ainda é necessário confirmar porta e host key da instância, API Terraform, user-data cloud-init e conectividade privada. A ferramenta HG Firewall Administration exige WHM e não se aplica a este plano; não está confirmado firewall de rede externo. A topologia prevista é k3s single-node conforme #90; permanecem abertos a versão fixada, as configurações de rede, a decisão sobre Traefik, o inventário, as portas internas e o caminho de rede do runner.
- Ubuntu 22.04 LTS tem suporte padrão até maio de 2027; planejar upgrade LTS com antecedência ou confirmar cobertura estendida. Validar compatibilidade do Kubernetes e organizar janela/backup antes do upgrade.
- O endpoint interno entre NGINX externo e NGINX Gateway Fabric no k3s single-node ainda deve ser definido. A proposta com Gateway API exige CRDs antes do controller e recursos dependentes, além da decisão sobre o Traefik embutido; nenhum componente interno deve disputar as portas públicas 80/443 do NGINX do host.
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
2. Detalhar a implantação do k3s single-node na VPS, conforme a issue #90, incluindo versão fixada, configuração de rede, desabilitação ou manutenção do Traefik e estratégia de acesso.
3. Validar a arquitetura de entrada baseada em Gateway API, conforme o estudo da issue #60, definindo a instalação declarativa dos CRDs e do NGINX Gateway Fabric pelo ArgoCD, com ordenação adequada das dependências.
4. Definir endpoint interno do NGINX, portas, dono do firewall, emissão/renovação TLS e acesso de recuperação.
5. Definir política de updates/reboots, backup/restore e se haverá host de teste.
6. Criar estrutura Ansible, fixar dependências e adicionar CI estática.
7. Planejar upgrade de Ubuntu 22.04 para uma LTS suportada ou confirmar cobertura Ubuntu Pro/ESM.
8. Implementar primeiro `base`, usuário administrativo, SSH e firewall em ambiente de teste, se disponível.
9. Implementar NGINX/Certbot e validação/reload seguro.
10. Instalar e validar o k3s single-node conforme #90 e executar o bootstrap do ArgoCD com Ansible; após definição da #60, reconciliar CRDs do Gateway API, NGINX Gateway Fabric e recursos Gateway/HTTPRoute via ArgoCD, na ordem adequada.
11. Adicionar apply pós-merge com Environment protegido, concorrência serial e logs sem secrets.
12. Atualizar README e guias Terraform/Kubernetes/ArgoCD para refletirem o estado efetivamente implantado.

## Referências relacionadas

- [Issue #59 — Arquitetura GitOps para Terraform e ArgoCD](https://github.com/IFPBEsp/APAE-INFRA/issues/59)
- [Issue #60 — Arquitetura do proxy reverso NGINX](https://github.com/IFPBEsp/APAE-INFRA/issues/60)
- [Issue #86 — Divisão do escopo Terraform, Ansible e ArgoCD na HostGator](https://github.com/IFPBEsp/APAE-INFRA/issues/86)
- [Issue #90 — Provisionar cluster Kubernetes com k3s](https://github.com/IFPBEsp/APAE-INFRA/issues/90)
- [Terraform](../boas-praticas/03-terraform.md) · [GitHub Actions](../boas-praticas/07-github-actions.md) · [Secrets](../boas-praticas/02-segredos-e-credenciais.md)
- [Fluxo documentado do ArgoCD](../argocd/fluxo-argocd.md)
- HostGator: [acesso SSH à VPS](https://suporte.hostgator.com.br/hc/pt-br/articles/30812824748051-Como-acessar-um-servidor-via-SSH) e [firewall via WHM](https://www.hostgator.com.br/blog/como-abrir-e-fechar-portas-em-um-servidor-da-hostgator/).
