# Conclusão e próximos passos

## 1. Decisão para a VPS HostGator — issue #86

**Status:** proposta para revisão e validação do time. Levantamento documental realizado em **17/10/2026**, sem acesso à VPS, ao contrato ou ao Portal do Cliente. Não comprova implantação nem homologação de capacidade. O responsável confirmou o plano escolhido por captura da oferta e informou Ubuntu 22.04 como sistema operacional. Inventário operacional e parâmetros de acesso ficam fora desta documentação pública. A estratégia de backup e recuperação da VPS e dos dados do cluster será definida na issue #107, com implementação e teste na #108; essas atividades não são pendências de conclusão da issue #86.

O estudo da [issue #59](https://github.com/IFPBEsp/APAE-INFRA/issues/59) definiu GitHub Actions como executor do Terraform e ArgoCD como reconciliador Kubernetes. A adoção de uma **VPS HostGator OCI NVMe 4 já contratada** exige delimitar quais recursos possuem integração utilizável pelo Terraform.

A proposta da [issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86) é:

> **Terraform gerencia recursos externos com API/provider validado, inicialmente as configurações do GitHub e a infraestrutura do backend de state. Ansible configura e mantém o host, instala o k3s e realiza o bootstrap do ArgoCD. ArgoCD reconcilia os recursos Kubernetes atribuídos às suas Applications. O provisionamento e as alterações do plano HostGator serão realizados pelo Portal do Cliente/suporte; a integração Terraform com a VPS não será adotada nesta etapa.**

Essa delimitação substitui a atribuição genérica de toda a fundação ao Terraform nos documentos do estudo #59. Mantém Git como fonte da verdade, revisão por PR, separação de credenciais e ausência de dependência circular no bootstrap. Terraform Operator e Crossplane continuam fora da etapa atual.

### Decisões arquiteturais consultadas

- [ADR 004 — Ansible e GitHub Actions](../adr/004-adocao-ansible-github-actions.md): Ubuntu 22.04 LTS sem painel, k3s single-node, host e bootstrap sob responsabilidade do Ansible.
- [ADR 003 — NGINX Gateway Fabric e Gateway API](../adr/003-nginx-gateway-fabric-e-gateway-api.md): Gateway Fabric exposto diretamente, TLS no Gateway e cert-manager como integração a validar.

Os ADRs foram incorporados à `dev` pelos PRs #80 e #62. São registros de arquitetura, não evidência de instalação; os status e as validações pendentes constam em cada ADR.

## 2. Especificações e acesso

O responsável confirmou em 17/10/2026 que o plano escolhido é o **VPS NVMe 4**, apresentando uma captura da oferta com **2 vCPU, 4 GB de RAM DDR5, 100 GB NVMe e 1 IP dedicado**, e informou **Ubuntu 22.04** como sistema operacional. A oferta também anuncia transferência ilimitada e servidores cloud no Brasil. Esses dados documentam o plano selecionado. Medições do host e detalhes de acesso pertencem à operação e à implementação, fora do escopo de conclusão desta documentação.

A [tabela pública dos planos brasileiros](https://suporte.hostgator.com.br/hc/pt-br/articles/30814898002707-Quais-s%C3%A3o-as-caracter%C3%ADsticas-dos-servidores-VPS) consultada coincide nos quantitativos de CPU, RAM e disco, mas descreve RAM DDR4. Para o plano escolhido, registra-se DDR5 conforme a captura fornecida, sem tratar essa divergência comercial como impedimento à definição do escopo Terraform.

| Item | Informação disponível | Verificação operacional fora da issue #86 |
| --- | --- | --- |
| Plano | HostGator VPS NVMe 4 confirmado pelo responsável; identificado como OCI na issue #86 | Identificador da assinatura e condições do contrato |
| CPU | 2 vCPU na oferta do plano escolhido | `lscpu` e `nproc` no host |
| Memória | 4 GB DDR5 na oferta do plano escolhido | Confirmar geração no contrato; `free -h` para capacidade utilizável |
| Disco | 100 GB NVMe na oferta do plano escolhido | `lsblk` e `df -h`; partições e espaço livre |
| Sistema operacional | Ubuntu 22.04, confirmado pelo responsável; LTS também informado no ADR 004 | `/etc/os-release`, arquitetura e kernel |
| Painel administrativo do SO | Sem cPanel/WHM, informado no ADR 004; oferta indica cPanel disponível | Disponibilidade comercial não confirma contratação ou instalação; conferir inventário |
| Endereço IP | Plano inclui 1 IP dedicado; endereço de acesso reservado ao inventário operacional privado | Conferir no Portal do Cliente e registrar eventual IPv6 no inventário privado; conectividade não testada neste levantamento |
| Acesso administrativo | SSH com acesso root disponível no produto | Porta efetiva, fingerprint por canal confiável, usuário e chave de automação |
| Recuperação | Não verificada na conta | Confirmar console/rescue e procedimento em caso de perda de SSH |

A [documentação da VPS simples](https://suporte.hostgator.com.br/hc/pt-br/articles/45911662214419-Como-funciona-a-VPS-simples) atribui segurança, atualizações e backups ao cliente e informa que a HostGator não realiza backups da VPS. O Portal do Cliente administra a contratação; o acesso ao sistema operacional ocorre por SSH.

Inventário medido no host, endereços e parâmetros de SSH devem ser mantidos na documentação operacional privada, conforme necessário à implementação. Não são entregáveis desta issue. Credenciais, chaves privadas e senhas ficam no mecanismo de secrets.

## 3. APIs, providers e limitações

**Resultado da pesquisa pública:** não foi localizada documentação de API pública de infraestrutura ou provider Terraform oficial da HostGator aplicável a este plano. Isso não prova inexistência de API privada ou integração contratual. A confirmação de API/provider de provisionamento da VPS não constitui pré-requisito nem pendência para encerrar esta decisão arquitetural. A pesquisa considerou a base de ajuda brasileira, as instruções de gerenciamento da VPS e o [Terraform Registry](https://registry.terraform.io/search/providers?q=hostgator).

| Recurso | Evidência e limite | Decisão inicial |
| --- | --- | --- |
| Criar, redimensionar ou reinstalar a VPS | Procedimentos públicos pelo Portal; API/provider utilizável não confirmado | Portal/suporte, com mudança registrada pelo operador |
| Rede, IP, volumes e firewall do provedor | Integração e permissões da conta não verificadas | Fora do Terraform nesta etapa; operações disponíveis pelo Portal/suporte serão registradas pelo operador |
| DNS | A HostGator documenta alterações por painel; API de zona DNS para esta conta não confirmada | Identificar DNS autoritativo antes de escolher provider; gestão manual registrada enquanto necessário |
| Snapshots | Estratégia ainda não decidida pelo projeto; disponibilidade, retenção, restauração e API não confirmadas | Estratégia na issue #107; implementação e teste de recuperação na #108; não assumir snapshots nem backup automático |
| `user-data`/cloud-init | Suporte não confirmado no plano | Não é pré-requisito; acesso inicial assistido e configuração com Ansible |
| OCI | A HostGator anuncia infraestrutura Oracle Cloud | A marca OCI não concede tenancy, OCIDs, IAM ou credenciais para o provider `oracle/oci` |

As instruções de [upgrade](https://suporte.hostgator.com.br/hc/pt-br/articles/45049801463315-Como-fazer-o-upgrade-da-VPS) descrevem a operação no Portal e não permitem downgrade entre esses planos. A [configuração de DNS](https://suporte.hostgator.com.br/hc/pt-br/articles/30810621770387-Como-configurar-o-DNS-de-um-dom%C3%ADnio) não comprova a existência de uma API. APIs de cPanel/WHM, quando disponíveis em outros produtos, não equivalem à API de provisionamento da VPS sem painel.

### Decisão registrada em 17/10/2026

Por decisão do responsável pelo projeto, **não será adotada integração Terraform com a VPS HostGator nesta etapa**. A VPS já existe e sua configuração será realizada pelo Ansible via SSH; criar ou alterar o plano por Terraform não é uma necessidade atual. Contratação, redimensionamento, reinstalação e demais operações disponíveis no provedor serão realizados pelo Portal do Cliente ou suporte, com registro da mudança.

A existência de API/provider permanece não confirmada, sem necessidade de investigação adicional para concluir a issue #86. A decisão poderá ser revista caso surja uma necessidade concreta de automatizar o ciclo de vida da VPS. Uma futura adoção exigirá comprovar integração, permissões e ciclo de vida dos recursos.

**DNS e backend de state são decisões independentes:** seus serviços e integrações serão avaliados conforme a solução escolhida. A estratégia de snapshots/backups e recuperação da VPS e dos dados do cluster fica na issue #107, com implementação e testes na #108; não exigem um provider Terraform da VPS nem bloqueiam a conclusão da issue #86. `user-data`/cloud-init não será pré-requisito do bootstrap atual.

Não serão utilizados `null_resource`, `terraform_data` com provisioners SSH ou automação do painel para simular um provider HostGator. A ausência de API de infraestrutura não impede configurar o Linux pelo Ansible.

## 4. Capacidade para k3s, ArgoCD e aplicações

O [mínimo documentado para um servidor k3s](https://docs.k3s.io/installation/requirements) é **2 cores e 2 GB de RAM**, sem incluir o consumo dos workloads. Portanto, o NVMe 4 anunciado atende ao mínimo do k3s, mas deixa pouca margem para control plane, ArgoCD, Gateway, aplicações e serviços auxiliares compartilharem 2 vCPU/4 GB.

### Carga declarada no repositório

A leitura dos seis Deployments em `kubernetes/*/base/` produz o seguinte recorte, sem overlays ou medição de execução:

| Cenário dos Deployments | Réplicas | CPU requests / limits | RAM requests / limits |
| --- | --- | --- | --- |
| Bases atuais: `apae`, `api`, `atendimento`, `atendimento-app` ativos | 4 | 400m / 2000m | 768Mi / 1536Mi |
| Uma réplica de cada Deployment, incluindo `management-app` e `site-comemorativo` | 6 | 600m / 3000m | 1024Mi / 2048Mi |

Fontes locais: [APAE Geral](../../kubernetes/apae-geral/base/), [APAE Atendimento](../../kubernetes/apae-atendimento/base/) e [site comemorativo](../../kubernetes/site-comemorativo/base/deployment.yaml). Os dois últimos Deployments adicionados no segundo cenário têm `replicas: 0` nas bases atuais. O recorte não representa todos os produtos futuros, em especial a gestão escolar sem Deployment nesse conjunto.

Requests são reservas para agendamento; limits são tetos por container, não consumo medido nem capacidade garantida. A soma de limits de CPU já alcança ou ultrapassa as 2 vCPU antes da plataforma. O orçamento precisa incluir SO, k3s, DNS do cluster, ArgoCD, Gateway Fabric, cert-manager, bancos, volumes, logs, métricas, backups e picos de rollout/reconciliação. Não se deve somar o mínimo do k3s como se fosse uma medição fixa nem assumir que os requests atuais bastam às aplicações.

**Conclusão de capacidade:** candidata a uma PoC enxuta de k3s single-node; capacidade de produção para todos os serviços **não homologada**. Não se recomenda hospedar simultaneamente `dev`, `hml` e `prod` nem adicionar uma stack pesada de observabilidade sem novo dimensionamento. Namespaces não criam recursos físicos adicionais.

A [documentação do ArgoCD](https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/) disponibiliza instalação sem HA para avaliação e não a recomenda para produção. Usá-la na PoC reduz componentes; sua adoção em produção exige aceitação explícita da limitação pelo time. Replicar componentes na mesma VPS não elimina a falha do host.

### Verificação necessária na issue #90

1. Confirmar hardware real, espaço livre e serviços já residentes; fixar versões e dimensionar todos os componentes da plataforma.
2. Instalar k3s e ArgoCD em PoC controlada; medir o consumo ocioso e durante sincronização, inicialização, rollout e backup. Métricas de `kubectl top nodes` e `kubectl top pods -A` dependem de metrics-server disponível.
3. Aplicar carga representativa aos serviços, incluindo bancos e uploads quando previstos; verificar latência, erros, throttling, OOMKills, reinícios, pods Pending, CPU/RAM e crescimento de disco.
4. Como critério inicial proposto, manter pelo menos 20% de margem de RAM utilizável e espaço livre em disco sob carga representativa, além de metas de latência/erros aprovadas pelo time; observar picos de CPU e contenção. A margem é uma proposta de engenharia, não garantia do provedor.
5. Registrar configuração, duração, carga, medições e resultado na issue #90. Se faltar margem ou houver degradação, reduzir o escopo ou redimensionar antes de produção.

O disco de 100 GB é compartilhado entre SO, imagens, datastore, volumes e logs; não equivale a 100 GB disponíveis para dados das aplicações. Um único nó não oferece alta disponibilidade. Backups devem sair da VPS e ter restauração testada; snapshot de máquina, caso exista, não substitui backup consistente de bancos e volumes.

## 5. Escopo do Terraform

| Candidato | Decisão | Condições e dependência |
| --- | --- | --- |
| Configurações dos repositórios GitHub | Primeiro escopo de implementação, issue #88 | Provider `integrations/github`; importar recursos existentes antes de aplicar, validar permissões e suporte às políticas no plano da organização |
| DNS | Condicional | Identificar domínio, nameservers autoritativos e API/provider. Um provedor externo pode gerenciar a zona mediante delegação aprovada, sem migrar a VPS |
| Backend remoto de state | Obrigatório antes do apply em CI, issue #87 | HCP Terraform Free, escolhido no [PR #101](https://github.com/IFPBEsp/APAE-INFRA/pull/101), ainda aberto; serviço externo à VPS, com integração e validações acompanhadas na issue #87 |
| Infraestrutura do backend | Terraform se houver provider adequado | Bootstrap separado e documentado; criar o backend antes de migrar o state das demais stacks |
| Helm e Kubernetes para bootstrap | Tecnicamente possíveis, não selecionados para esta VPS | Exigem cluster existente, API acessível e credenciais; duplicariam o bootstrap atribuído ao Ansible no ADR 004 |
| VPS, rede, discos, snapshots e firewall HostGator | Integração Terraform não adotada nesta etapa | Operações pelo Portal/suporte; reavaliar apenas diante de necessidade concreta de automação |
| Configuração do host e instalação do k3s | Ansible | Não substituir por provisioners Terraform |
| Recursos Kubernetes após bootstrap | ArgoCD | Terraform não mantém os mesmos objetos em state |

Providers [Helm](https://registry.terraform.io/providers/hashicorp/helm/latest/docs) e [Kubernetes](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs) não criam o servidor nem instalam o k3s no Linux. Sua disponibilidade não altera a decisão de manter as operações do provedor fora do Terraform.

A implementação do GitHub deve ter state separado dos ambientes de aplicações; configurações da organização são compartilhadas. O isolamento por stack/ambiente, o versionamento dos providers e as permissões mínimas serão definidos nas issues #87 e #88. Segredos e conteúdo sensível de state/plan não serão publicados no Git ou em comentários de PR.

O HCP Terraform Free é a solução escolhida na issue #87 e documentada no [PR #101](https://github.com/IFPBEsp/APAE-INFRA/pull/101), ainda pendente de integração à `dev`. A implementação e as evidências de locking e recuperação do state pertencem a esse PR; esta atualização não incorpora sua configuração nem comprova sua integração. Contabo Object Storage permanece apenas alternativa histórica do estudo #59. O backend deve ficar fora da VPS e do k3s; `concurrency` no Actions complementa o locking do backend.

O [documento 03](03-bootstrap-state-locking-e-drift.md) permanece sem alterações neste PR para evitar sobreposição com o #101. Até a integração daquele PR, suas referências a Contabo e à escolha de backend são históricas; para a divisão de responsabilidades na HostGator, prevalecem esta proposta e o ADR 004.

## 6. Responsabilidades e sequência de bootstrap

| Recurso/operação | Responsável pelo estado desejado | Limite |
| --- | --- | --- |
| Contratação, upgrade, reinstalação e recuperação HostGator | Operador via Portal/suporte | Fluxo adotado nesta etapa, com registro das mudanças; integração Terraform dispensada |
| GitHub, DNS e infraestrutura de state quando suportados | Terraform | Recursos externos; sem instalação do SO/k3s ou workloads |
| SO, usuários, SSH, pacotes, serviços e firewall local | Ansible | Mudanças por SSH com identidade validada e acesso de recuperação |
| Instalação, configuração e atualização do k3s | Ansible | Versão, datastore, rede, Traefik e ServiceLB explicitamente definidos |
| Instalação e manutenção inicial do ArgoCD | Ansible | Sem autogerenciamento presumido; transferência futura exige decisão e retirada da gestão anterior |
| AppProject de bootstrap e Application raiz | Ansible | Enquanto excluídos do caminho reconciliado, conforme ADR 004 |
| Applications filhas, workloads e infraestrutura Kubernetes | ArgoCD | CRDs, controllers, observabilidade e recursos com dependências e RBAC adequados |
| Gateway API e NGINX Gateway Fabric | ArgoCD | Exposição direta de 80/443 a validar no k3s; TLS no Gateway |
| cert-manager e configuração declarativa de certificados | ArgoCD | Controller emite/renova; integração ACME ainda precisa de validação |
| Validação, aprovação e execução de Terraform/Ansible | GitHub Actions | Orquestra; não assume propriedade dos recursos |

Cada objeto terá um único responsável. Ansible não aplica workloads ou HTTPRoutes pertencentes ao ArgoCD; Terraform não mantém releases Helm ou objetos já reconciliados por ele. O AppProject das aplicações não deve receber privilégios amplos apenas para instalar infraestrutura: a implementação precisará de escopo específico para CRDs e controllers.

```text
VPS existente (Portal/suporte HostGator)
  → acesso inicial validado por operador
  → Ansible: host, firewall local e k3s
  → Ansible: ArgoCD, AppProject e Application raiz
  → ArgoCD: Applications filhas e infraestrutura Kubernetes
  → ArgoCD: workloads e rotas das aplicações

Git → PR/review → GitHub Actions → Terraform → GitHub / recursos externos suportados
Git → PR/review → GitHub Actions → Ansible   → host / k3s / bootstrap
Git → ArgoCD                               → recursos Kubernetes atribuídos
```

A preparação do host não depende do backend Terraform nem do ArgoCD. O backend é pré-requisito do apply Terraform em CI. Produção com Ansible segue a decisão do ADR 004: código revisado na `main`, Environment `production` protegido, aprovação, SSH validado e execução serializada por host. Merge em `dev` não aplica mudanças à VPS de produção. São fluxos propostos, não workflows já implantados.

No desenho inicial, não há NGINX externo nem Certbot no host. A issue #90 deve validar conflitos com Traefik/ServiceLB, exposição do Gateway e firewall; a escolha de Gateway direto não implica desabilitar ServiceLB automaticamente. GitOps não substitui backups, e reconstruir o host não recupera seus dados.

## 7. Próximos passos e validação do time

| Ação | Encaminhamento | Evidência para conclusão |
| --- | --- | --- |
| Manter inventário e acesso operacional em local privado | Operação / implementação Ansible, fora da issue #86 | Dados necessários à execução segura, sem publicação neste estudo |
| Definir estratégia de backup e recuperação | Issue #107 | Dados protegidos, capacidades do provedor, responsáveis, retenção e RPO/RTO definidos |
| Implementar backups e testar recuperação | Issue #108, dependente da #107 | Backups externos automatizados, alertas e restauração em ambiente isolado validados |
| Identificar serviço de DNS e integração aplicável | Time de infraestrutura | Zona autoritativa e forma de gestão definidas, independentemente da VPS |
| Ratificar esta divisão de responsabilidades | Time de infraestrutura, issue #86 | Review registrado no PR e decisão explícita sobre pendências |
| Detalhar fluxo e arquitetura Terraform | Issue #11 | Guias alinhados ao escopo ratificado |
| Integrar o HCP Terraform e concluir validações do state remoto | Issue #87 / PR #101 | Concorrência, isolamento, acesso e recuperação validados |
| Implementar gestão GitHub | Issue #88 | Importação e plan revisados antes do apply |
| Implementar configuração do host | Issue #90, conforme ADR 004 | Roles, inventários e execução protegida validados |
| Provisionar k3s e homologar capacidade | Issue #90 | PoC, métricas, teste de carga e recuperação registrados |
| Implementar entrada HTTP/HTTPS | Issue #90, conforme ADR 003 | Gateway, DNS, TLS, rotas e reinício testados |

Para concluir a issue #86, resta registrar a revisão e validação do time sobre o escopo, as operações pelo Portal/suporte e as limitações de capacidade. O teste prático de capacidade fica na #90; a estratégia de backup e recuperação, na #107; sua implementação e teste, na #108. A issue #87 cobre apenas o state Terraform. Inventário e acesso operacional privados não são critérios pendentes desta documentação.

## 8. Referências

Fontes externas consultadas em 17/10/2026; links de produto podem mudar. Os ADRs consultados estão identificados na seção 1; encaminhamentos atualizados em 28/10/2026.

- [Issue #86 — capacidades da VPS e escopo Terraform](https://github.com/IFPBEsp/APAE-INFRA/issues/86)
- [Issue #59 — estudo GitOps](https://github.com/IFPBEsp/APAE-INFRA/issues/59)
- [Provider GitHub — integrations/github](https://registry.terraform.io/providers/integrations/github/latest/docs)
- [Decisão arquitetural consolidada](05-decisao-arquitetural.md)
- [Bootstrap, state, locking e drift](03-bootstrap-state-locking-e-drift.md)
- [ADR 002 — estratégia GitOps](../adr/002-estrategia-gitops-terraform.md)
- [Issue #107 — estratégia de backup e recuperação](https://github.com/IFPBEsp/APAE-INFRA/issues/107)
- [Issue #108 — implementação de backups e teste de recuperação](https://github.com/IFPBEsp/APAE-INFRA/issues/108)
- [ADR 003 — NGINX Gateway Fabric e Gateway API](../adr/003-nginx-gateway-fabric-e-gateway-api.md)
- [ADR 004 — Ansible e GitHub Actions](../adr/004-adocao-ansible-github-actions.md)
