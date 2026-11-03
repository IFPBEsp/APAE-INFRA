# ADR — Adoção de Ansible com GitHub Actions para gerenciamento da VPS

## Status

Aceito como decisão arquitetural do estudo de Ansible; implementação e validação operacional pendentes.

A consolidação da divisão de responsabilidades com o estudo anterior de Terraform permanece vinculada à [issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86). Este registro não comprova implantação na VPS nem conclusão dessa consolidação.

## Contexto

O APAE-INFRA precisa gerenciar de forma reproduzível, idempotente e auditável uma VPS HostGator existente, sem painel, com Ubuntu 22.04 LTS. A plataforma prevista é um cluster **k3s single-node**, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90).

O estudo em [`docs/ansible/`](../ansible/README.md) compara scripts via SSH, execução direta de Ansible e execução de Ansible pelo GitHub Actions. A presença de documentação e manifests no repositório não comprova que playbooks, workflows ou componentes estejam implantados.

A arquitetura de entrada selecionada pelo estudo da issue #60 prevê **Gateway API com NGINX Gateway Fabric exposto diretamente no Kubernetes**, com terminação TLS no Gateway Fabric. NGINX externo e Certbot no host não compõem o escopo obrigatório inicial. A emissão e renovação de certificados com cert-manager é proposta e depende de validação da integração.

Não há confirmação de API/provider Terraform compatível com o plano HostGator nem de suporte a `user-data`/cloud-init. Por isso, essas integrações não podem ser pré-requisitos para configurar a VPS atual.

## Decisão

Adotar **GitHub Actions + Ansible como fluxo normal de configuração e manutenção da VPS**. Playbooks e roles versionados descrevem o estado do host; GitHub Actions valida, controla a aprovação e orquestra a execução.

Cada recurso terá uma única ferramenta responsável por seu estado declarado:

| Ferramenta | Responsabilidade e limite |
| --- | --- |
| **Ansible** | Sistema operacional, usuários, SSH, pacotes, permissões, firewall local, serviços e agentes do host; instalação, configuração e manutenção do k3s; instalação e atualização do ArgoCD com versão fixada e validada. |
| **GitHub Actions** | Validação e orquestração das execuções aprovadas, sem assumir a propriedade dos recursos. |
| **ArgoCD** | Applications filhas e recursos Kubernetes atribuídos a elas: workloads, observabilidade do cluster, CRDs, NGINX Gateway Fabric, GatewayClass, Gateway, HTTPRoute e cert-manager quando implementado. |
| **Terraform** | Recursos externos ao host, como VPS, rede, volumes, DNS e firewall do provedor, somente quando houver integração suportada. Provisionamento não automatizável será uma exceção documentada. |
| **cloud-init** | Preparação mínima do acesso inicial de novas VPS, somente se houver suporte do provedor; não realiza configuração recorrente. |

O **AppProject de bootstrap e a Application raiz permanecem sob responsabilidade do Ansible enquanto `project.yaml` e `app-of-apps.yaml` estiverem excluídos do caminho reconciliado pelo ArgoCD**. Ansible não aplicará diretamente workloads ou rotas que pertençam ao ArgoCD após o bootstrap.

As Applications de infraestrutura terão permissões específicas e ordenação que disponibilize os CRDs antes dos controllers e recursos dependentes. A política de sincronização das Applications filhas deverá ser respeitada, sem pressupor sincronização automática.

### Fluxo de produção

1. Pull Requests para `dev` executam validação YAML, `ansible-lint` e `ansible-playbook --syntax-check`, sem conexão com a VPS nem secrets de produção.
2. Merge em `dev` não aplica mudanças na VPS. As alterações seguem por Pull Request revisado de `dev` para `main`.
3. Push em `main` pode iniciar o workflow de aplicação quando houver alterações nos caminhos monitorados de Ansible, dependências e workflow.
4. O job utiliza o GitHub Environment `production`, com aprovação obrigatória de responsável autorizado e restrição de deployment à branch `main`.
5. O apply verifica `github.ref == 'refs/heads/main'`, utiliza o commit da execução autorizada, dependências fixadas, validação SSH e secrets restritos ao job aprovado.
6. Execuções são serializadas por host/ambiente, sem cancelar automaticamente um apply em andamento. Ao terminar, são registradas as verificações de saúde, o commit e o resultado.

Disparos manuais por `workflow_dispatch` seguem as mesmas proteções e permitem apenas playbooks, inventários e tags autorizados. Não aceitam comandos ou referências Git arbitrários. Aprovação do Environment e revisão do código são requisitos distintos.

O `--check` remoto será permitido apenas em ambiente de teste isolado, com credenciais próprias. Na ausência desse ambiente, a CI permanece estática até a aplicação protegida.

### Bootstrap e segurança

O bootstrap da VPS existente será executado por operador autorizado, a partir de estação controlada, utilizando o acesso inicial do provedor e validando a identidade SSH. A senha root inicial não será fornecida ao GitHub Actions. O acesso definitivo será testado antes de restringir o acesso anterior, preservando um caminho de recuperação.

A automação utilizará usuário e chave SSH dedicados, `become` quando necessário e `known_hosts` validado por canal confiável. Secrets de execução ficarão no Environment `production`; Ansible Vault será reservado a conteúdo que precise ser versionado cifrado, com senha fora do Git. Logs e artefatos não conterão segredos.

Preferir VPN, bastion ou rede privada quando disponíveis. Se for necessário SSH público, restringir origens e documentar as limitações. Não abrir SSH irrestrito nem instalar runner privilegiado de produção na própria VPS administrada.

A configuração do firewall deverá preservar a rede de pods e Services do k3s, restringir a API Kubernetes às origens administrativas autorizadas e validar externamente as portas expostas. UFW isoladamente não será tratado como garantia de bloqueio de NodePorts.

## Motivação

- Módulos declarativos e roles permitem convergência idempotente e reutilização da configuração.
- Separar playbooks da orquestração evita distribuir o estado desejado em comandos dos workflows.
- PR, revisão, commit, aprovação e execução permitem rastrear as mudanças de produção.
- A divisão por recurso evita que Terraform, Ansible e ArgoCD disputem o mesmo objeto.
- O bootstrap com Ansible atende à VPS existente sem depender de integrações do provedor ainda não confirmadas.

## Alternativas consideradas

| Alternativa | Avaliação |
| --- | --- |
| **GitHub Actions + SSH/scripts** | Não selecionada como gerenciamento permanente: idempotência, falhas parciais e recuperação precisariam ser implementadas em cada script. Operações pontuais continuam possíveis mediante controle e registro. |
| **Ansible executado diretamente** | Mantido para bootstrap, desenvolvimento, diagnóstico e contingência controlada. Não é o fluxo recorrente principal, pois depende da padronização da estação, das credenciais e do registro pelo operador. |
| **GitHub Actions + Ansible** | Selecionada por combinar configuração declarativa com validação, aprovação e execução padronizadas. Exige manutenção do pipeline e proteção do runner e das credenciais. |

## Relação com a decisão anterior

O estudo de Terraform da [issue #59](https://github.com/IFPBEsp/APAE-INFRA/issues/59) atribuía conceitualmente ao Terraform o bootstrap do host, do Kubernetes e do ArgoCD, prevendo autogerenciamento posterior.

Para a VPS HostGator atual, a decisão registrada neste ADR atribui esse bootstrap e as atualizações da instalação do ArgoCD ao Ansible. Terraform permanece aplicável aos recursos externos com integração confirmada. Os manifestos da própria instalação do ArgoCD ficam fora de todas as Applications reconciliadas por ele; não haverá autogerenciamento dessa instalação. O AppProject e a Application raiz também permanecem sob o Ansible enquanto estiverem excluídos da reconciliação.

A ratificação dessa delimitação com o time e a atualização dos documentos anteriores serão tratadas na issue #86, conforme o estudo. A arquitetura de entrada da issue #60 é preservada.

## Consequências

### Positivas

- Configuração do host versionada e reproduzível, com menor dependência de intervenções manuais.
- Execuções recorrentes padronizadas e auditáveis, com controle explícito de acesso à produção.
- Responsabilidades delimitadas entre host, provisionamento externo e reconciliação Kubernetes.
- Bootstrap e recuperação documentáveis sem exigir uma API HostGator ainda não confirmada.

### Negativas e limitações

- Há custo inicial para criar playbooks, roles, inventários, CI e proteções de produção, além da manutenção de versões e credenciais.
- Ansible converge quando executado; não mantém reconciliação contínua do host. Drift exige detecção e nova execução.
- Ansible não é transacional: falhas podem deixar alterações parciais. Reverter um commit ou repetir o playbook não oferece rollback universal.
- A VPS single-node não fornece alta disponibilidade. Manutenções do host ou do k3s podem interromper todos os produtos e exigem janela, compatibilidade de versões e recuperação planejada.
- Runner e credenciais administrativos comprometidos podem afetar toda a VPS. Alterações em SSH e firewall também podem causar perda de acesso.
- Playbooks e manifests não substituem backups do datastore do k3s, volumes, bancos de dados e material sensível. A restauração deverá ser testada.
- A execução depende da disponibilidade do GitHub Actions e da conectividade SSH. A contingência por operador autorizado deverá ser registrada e as mudanças permanentes incorporadas ao Git.

## Implementação pendente

Antes da entrada em produção, será necessário:

1. Confirmar porta e fingerprint SSH, recuperação, conectividade do runner e capacidades de API, `user-data` e firewall externo do provedor.
2. Consolidar o escopo Terraform/Ansible/ArgoCD na issue #86 e implementar roles, inventários sem credenciais, dependências fixadas, CI e apply protegido.
3. Definir versão, datastore, rede e política de atualização do k3s, com tratamento explícito de Traefik e ServiceLB. A escolha de exposição do Gateway não implica desabilitar ServiceLB automaticamente.
4. Implementar o bootstrap do ArgoCD e o escopo GitOps de infraestrutura, com permissões e ordenação de CRDs, controllers e recursos dependentes.
5. Selecionar e testar a exposição direta de 80/443, DNS, TLS, integração ACME/cert-manager, IP real, rotas e recuperação após reinício.
6. Definir observabilidade, atualização do sistema operacional, backups externos, retenção, criptografia, restauração testada e runbooks de contingência.

## Referências

- [Índice do estudo de Ansible](../ansible/README.md)
- [01 — Contexto e requisitos](../ansible/01-contexto-e-requisitos.md)
- [02 — Comparação das alternativas](../ansible/02-comparacao-das-alternativas.md)
- [03 — Divisão de responsabilidades](../ansible/03-divisao-de-responsabilidades.md)
- [04 — Bootstrap da VPS](../ansible/04-bootstrap-da-vps.md)
- [05 — Secrets, SSH e segurança](../ansible/05-secrets-ssh-e-seguranca.md)
- [06 — Fluxo GitHub Actions + Ansible](../ansible/06-fluxo-github-actions-e-ansible.md)
- [07 — Arquitetura proposta e próximos passos](../ansible/07-arquitetura-proposta-e-proximos-passos.md)
