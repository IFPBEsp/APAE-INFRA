# 01 — Contexto e requisitos

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Objetivo

Definir o estado operacional esperado da VPS e os requisitos para gerenciá-lo declarativamente. Este estudo apresenta uma proposta arquitetural para a automação com Ansible e GitHub Actions; não descreve uma implantação Ansible já existente.

## Contexto

O ambiente atual utiliza uma **VPS simples da HostGator, sem painel, com Ubuntu 22.04 LTS**. A documentação da HostGator descreve acesso root via SSH para VPS Linux; a porta, a identidade SSH e os mecanismos de recuperação da instância deverão ser confirmados antes de qualquer automação.

O `APAE-INFRA` já contém documentação e manifests Kubernetes, além de orientações para Terraform e ArgoCD. A automação de infraestrutura ainda está em evolução: a presença de diretórios ou documentação não comprova que playbooks Ansible, módulos Terraform de ambiente, Applications ArgoCD ou componentes Kubernetes tenham sido implantados.

A arquitetura-alvo prevê **k3s single-node** na VPS, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90), com **Gateway API e NGINX Gateway Fabric exposto diretamente** como entrada HTTP/HTTPS dos produtos, conforme a decisão documentada no [estudo da issue #60](../nginx/README.md). Não está prevista uma segunda camada obrigatória de NGINX no host.

A seção [Estado atual e arquitetura proposta](07-arquitetura-proposta-e-proximos-passos.md#estado-atual-e-arquitetura-proposta) diferencia a estrutura versionada dos componentes cuja implementação ainda está pendente.

## Componentes da VPS sob gerenciamento

O Ansible deverá manter o estado da VPS e dos componentes de bootstrap atribuídos ao host:

- sistema operacional, atualizações de segurança, timezone, pacotes, diretórios, permissões e serviços `systemd` do host;
- usuários administrativos e de serviço, grupos, `sudo`, chaves públicas e configuração SSH;
- firewall local, coordenado com eventuais regras de rede oferecidas pelo provedor e com os requisitos de conectividade do k3s;
- pré-requisitos, instalação, configuração e manutenção do **k3s single-node**, com versão fixada, configuração de rede e definição sobre os componentes Traefik e ServiceLB;
- instalação inicial do ArgoCD e aplicação controlada do **AppProject** e da **Application raiz**, enquanto esses objetos permanecerem fora da reconciliação do ArgoCD;
- ferramentas auxiliares, verificações operacionais e agentes de observabilidade executados diretamente no host.

**NGINX externo e Certbot não fazem parte do escopo obrigatório do Ansible na arquitetura selecionada.** Esses componentes somente deverão ser incluídos em playbooks se uma futura decisão arquitetural justificar um proxy HTTP independente do cluster. A validação de configurações e o reload de serviços do host continuam sendo responsabilidade do Ansible quando tais serviços existirem.

O **ArgoCD** será responsável pelas Applications filhas e pelos recursos Kubernetes a elas atribuídos. A arquitetura selecionada prevê gerenciamento declarativo dos **CRDs do Gateway API**, do **NGINX Gateway Fabric**, dos recursos `GatewayClass`, `Gateway` e `HTTPRoute`, dos Services e dos workloads Kubernetes, respeitando as dependências de instalação.

O gerenciamento de certificados TLS é previsto com **cert-manager dentro do Kubernetes**, sujeito à definição de sua integração e configuração. A terminação TLS ocorrerá no data plane do NGINX Gateway Fabric. A exposição pública das portas `80/443` depende do mecanismo de rede selecionado e validado durante a implementação, não de um NGINX instalado no host.

A instalação de CRDs, controllers e outros recursos privilegiados exigirá um fluxo de bootstrap e permissões de ArgoCD apropriados, preferencialmente separados das permissões das aplicações de negócio. Não se deve presumir que o AppProject atual, destinado aos produtos APAE, já permita administrar recursos de infraestrutura de escopo global.

Cada recurso deverá possuir uma ferramenta proprietária, evitando sobreposição entre Terraform, Ansible e ArgoCD. O Terraform ficará restrito aos recursos do provedor para os quais exista integração efetivamente suportada; o Ansible manterá a configuração da VPS e o bootstrap; o ArgoCD reconciliará o estado declarativo do cluster.

## Requisitos de qualidade

- **Idempotência:** execuções repetidas convergem para o estado declarado, preferindo módulos declarativos a comandos shell.
- **Reprodutibilidade:** uma VPS reconstruída deverá alcançar o estado esperado a partir de procedimentos, versões e configurações documentados.
- **Segurança:** credenciais fora do Git em claro, SSH restrito, menor privilégio viável, logs sem segredos e prevenção de exposição indevida de portas e Services.
- **Auditabilidade:** PR, revisão, commit, aprovação e execução formam o registro das mudanças.
- **Validação:** lint e checagem de sintaxe antes do merge; verificações específicas dos serviços antes de reinícios ou alterações críticas.
- **Proteção da produção:** merges na `dev` apenas validam; a aplicação em produção utiliza código da `main`, filtros de caminhos, Environment protegido e aprovação obrigatória, inclusive em disparos manuais.
- **Recuperação:** mudanças em SSH, firewall, Kubernetes e serviços críticos exigem caminho de acesso emergencial, backups e procedimento de recuperação documentado.

## Ciclo de vida do sistema operacional e do k3s

O Ubuntu 22.04 LTS possui suporte padrão até maio de 2027. O planejamento operacional deverá prever migração suportada para uma LTS posterior antes desse marco ou confirmar cobertura de segurança estendida. A atualização de versão do sistema não deve ser tratada como um `apt upgrade` rotineiro: exige backup, verificação de compatibilidade do k3s, janela de manutenção e procedimento de recuperação.

A versão do k3s deverá ser fixada. Atualizações de k3s em um cluster single-node poderão interromper todos os produtos hospedados; por isso, exigem avaliação de compatibilidade, backup do datastore e dos dados persistentes, teste de restauração, janela de manutenção e validação posterior de rede, workloads e entrada HTTP/HTTPS.

## Fluxo esperado

```text
Terraform      → recursos externos com integração suportada, se houver
cloud-init     → acesso inicial em novas VPS, somente se suportado
Ansible        → host, SSH, firewall local, k3s e bootstrap do ArgoCD
ArgoCD         → infraestrutura Kubernetes, Gateway API e workloads
NGINX Gateway Fabric → entrada HTTP/HTTPS e terminação TLS no cluster
cert-manager   → emissão e renovação de certificados TLS no cluster
GitHub Actions → validação, aprovação e orquestração de Terraform/Ansible
```

A instalação inicial do ArgoCD, do AppProject e da Application raiz ficará sob execução controlada do Ansible enquanto esses objetos forem excluídos do caminho reconciliado. O ArgoCD passará a reconciliar as Applications filhas e seus recursos após o bootstrap, conforme o escopo de permissões definido.

## Decisões ainda necessárias para implementação

A VPS HostGator atual, o Ubuntu 22.04 LTS e a topologia prevista de **k3s single-node** são premissas deste estudo. A **arquitetura selecionada de entrada é Gateway API direto com NGINX Gateway Fabric**, sem NGINX externo obrigatório; o mecanismo concreto de exposição ainda precisa ser implementado e testado.

Permanecem pendentes as seguintes definições operacionais:

- disponibilidade de API de provisionamento e suporte a `user-data`/cloud-init na HostGator;
- existência de firewall de rede externo ao host e conectividade privada entre o runner e a VPS;
- porta e fingerprint SSH da instância, inventários, acesso administrativo e recuperação emergencial;
- versão fixa e parâmetros de instalação do k3s, CIDRs de pods/Services e política do UFW;
- decisão sobre desabilitar o Traefik e manter ou não o ServiceLB conforme a exposição pública escolhida;
- mecanismo seguro para disponibilizar o data plane do NGINX Gateway Fabric nas portas `80/443`;
- instalação ordenada dos CRDs do Gateway API, do controller e dos recursos dependentes, com AppProject e permissões de infraestrutura adequados;
- integração do cert-manager, emissão e renovação de certificados TLS e monitoramento de expiração;
- testes de conectividade, headers, IP real, exposição de Services e recuperação após reinício;
- política de atualizações, backup e restauração do sistema operacional, k3s e dados persistentes.

Na VPS atual, as regras locais do firewall pertencem ao Ansible. O **UFW, isoladamente, não deve ser considerado uma garantia de proteção de NodePorts**, e a configuração de firewall deverá respeitar os requisitos de rede do k3s.

A delimitação de responsabilidades entre Terraform, Ansible e ArgoCD deverá ser consolidada com o time, conforme a [issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86), preservando a decisão de entrada HTTP/HTTPS registrada na [issue #60](https://github.com/IFPBEsp/APAE-INFRA/issues/60).

Preferir VPN, bastion ou rede privada quando disponíveis. Não abrir SSH irrestrito à Internet nem executar o runner privilegiado de produção na própria VPS administrada.

## Referências

- [Estudo de arquitetura NGINX e Gateway API](../nginx/README.md)
- [Divisão de responsabilidades](03-divisao-de-responsabilidades.md)
- [Bootstrap da VPS](04-bootstrap-da-vps.md)
- [Fluxo GitHub Actions + Ansible](06-fluxo-github-actions-e-ansible.md)
- [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)
- [Issue #60 — Arquitetura de entrada HTTP/HTTPS](https://github.com/IFPBEsp/APAE-INFRA/issues/60)
- [Issue #86 — Divisão Terraform, Ansible e ArgoCD](https://github.com/IFPBEsp/APAE-INFRA/issues/86)
- [Issue #90 — Cluster k3s](https://github.com/IFPBEsp/APAE-INFRA/issues/90)
