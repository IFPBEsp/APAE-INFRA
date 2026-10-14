# 04 — Bootstrap da VPS

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Objetivo

Preparar a VPS HostGator atual, sem painel, com Ubuntu 22.04 LTS, para que o Ansible gerencie a configuração do host, instale e mantenha o cluster **k3s single-node** e execute o bootstrap inicial do ArgoCD. Este documento descreve uma arquitetura e um processo propostos, não uma implantação já realizada.

Para novas instâncias, considerar **Terraform + cloud-init mínimo + Ansible** somente se o plano e o provedor confirmarem suporte a provisionamento por API e a user-data. Na VPS existente, não presumir que Terraform ou cloud-init possam reprovisionar a instância ou injetar user-data retroativamente.

A entrada HTTP/HTTPS selecionada no estudo da [issue #60](https://github.com/IFPBEsp/APAE-INFRA/issues/60) é feita diretamente pelo **NGINX Gateway Fabric** no Kubernetes, sem NGINX externo ou Certbot obrigatórios no host. O modo de exposição nas portas 80/443 e a integração com cert-manager serão definidos na implementação.

## Fluxo inicial

1. **Instância existente:** um operador autorizado acessa a VPS pelo SSH inicial fornecido pela HostGator, a partir de estação controlada, valida a identidade do host e executa o bootstrap versionado. Não disponibilizar a senha root inicial ao GitHub Actions.
2. **Acesso administrativo:** Ansible cria usuário dedicado com chave pública e privilégios administrativos necessários, valida uma nova sessão SSH e somente depois restringe o acesso root, preservando um caminho de recuperação previamente confirmado.
3. **Configuração do host:** Ansible configura sistema operacional, usuários, SSH, pacotes, serviços, firewall local e os pré-requisitos de rede do k3s.
4. **Instalação do Kubernetes:** Ansible instala o **k3s single-node** com versão fixada e parâmetros versionados, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90). A configuração deve tratar explicitamente Traefik, ServiceLB, redes de pods/Services e acesso à API Kubernetes.
5. **Bootstrap do ArgoCD:** um playbook separado instala o ArgoCD, aplica o `AppProject` de bootstrap e registra a `Application` raiz.
6. **Reconciliação GitOps:** ArgoCD passa a gerenciar as Applications filhas e os recursos Kubernetes atribuídos a elas. Applications de infraestrutura, com permissões próprias, deverão reconciliar os CRDs do Gateway API, o NGINX Gateway Fabric, o cert-manager e os demais recursos necessários, respeitando a ordem de dependências.
7. **Validação:** confirmar acesso administrativo, saúde do k3s e do ArgoCD, sincronização das Applications e, após a configuração da entrada pública, funcionamento de TLS, portas 80/443 e rotas das aplicações.

Para uma instância futura, Terraform provisionará somente os recursos suportados pelo provedor, e cloud-init criará o acesso inicial se a HostGator disponibilizar esses mecanismos. Depois, o Ansible seguirá as etapas pertinentes.

### Responsabilidades do cloud-init

O cloud-init, quando suportado, executará apenas o necessário para habilitar o gerenciamento inicial:

- criar usuário administrativo de bootstrap, sem autenticação por senha;
- instalar a chave pública autorizada;
- garantir Python, caso ausente na imagem;
- conceder `sudo` suficiente para a configuração posterior pelo Ansible;
- manter SSH acessível enquanto o hardening definitivo é aplicado e validado.

Não utilizar cloud-init para configuração recorrente do host nem para instalar ou manter k3s, ArgoCD, Gateway Fabric, cert-manager ou agentes de observabilidade.

User-data não deverá conter chave privada, senha ou token permanente. Considerar que seu conteúdo pode ser retido pelo provedor ou registrado no estado da infraestrutura; fornecer apenas dados não sensíveis.

### Configuração pelo Ansible

O Ansible manterá o estado declarado do **host**: sistema operacional, usuários, SSH, pacotes, diretórios, permissões, firewall local, serviços e agentes instalados diretamente na VPS. Também gerenciará a instalação, a configuração e a manutenção do k3s e o bootstrap do ArgoCD.

**NGINX externo e Certbot não integram o escopo padrão.** Caso seja aprovada futuramente uma topologia com proxy independente do cluster, sua responsabilidade deverá ser documentada antes de criar roles adicionais.

Alterações em SSH e firewall deverão preservar uma sessão de recuperação, validar novo acesso antes de encerrar a sessão atual e observar os requisitos de comunicação do k3s. Se o UFW for mantido, validar as redes de pods e Services (por padrão, `10.42.0.0/16` e `10.43.0.0/16`) e restringir a API Kubernetes na porta `6443/tcp` às origens autorizadas. O UFW isoladamente não é garantia de bloqueio de NodePorts.

Atualizações do k3s e do sistema operacional exigirão versões controladas, verificação de compatibilidade, backups, plano de recuperação e janela de manutenção, considerando que o cluster é single-node.

### Bootstrap do ArgoCD

Após confirmar a saúde do k3s, um playbook Ansible separado deverá:

1. Instalar uma versão fixada e validada do ArgoCD.
2. Aguardar a disponibilidade dos componentes e CRDs próprios do ArgoCD.
3. Aplicar o `AppProject` necessário ao bootstrap e registrar a `Application` raiz do repositório.
4. Validar acesso ao repositório GitOps, destino Kubernetes e estado da Application raiz.
5. Confirmar a descoberta e a reconciliação das Applications filhas.

Conforme o fluxo atualmente documentado em [Fluxo do ArgoCD](../argocd/fluxo-argocd.md), `project.yaml` e `app-of-apps.yaml` são excluídos do caminho reconciliado pela raiz. Enquanto essa exclusão permanecer, ambos pertencem ao **Ansible**: suas alterações exigirão a execução controlada do playbook. Não fazer Ansible e ArgoCD administrarem simultaneamente os mesmos objetos.

A instalação de CRDs e controllers de infraestrutura deverá utilizar Applications e permissões apropriadas, sem conceder indiscriminadamente privilégios de cluster ao AppProject das aplicações APAE. A ordem de instalação deve assegurar que os CRDs existam antes dos recursos que dependem deles; versões, sincronização e mecanismo exato de bootstrap serão definidos e testados na implementação.

**A instalação inicial do ArgoCD não comprova que o cluster já esteja funcionando em produção.** As rotas públicas e os certificados somente serão considerados prontos depois das validações de exposição, TLS e conectividade.

## Identidade e conectividade SSH

O bootstrap instala apenas chaves públicas no host. A chave privada da automação ficará em um GitHub Environment Secret de produção, disponibilizado exclusivamente ao job de apply autorizado, ou em estação administrativa aprovada para contingência. O acesso root fornecido pela HostGator é reservado ao bootstrap inicial e à recuperação, não ao uso recorrente do Ansible.

Antes de iniciar a automação, confirmar a porta SSH e a identidade da instância por canal confiável. O runner deverá validar a chave do host com `known_hosts` verificado independentemente ou mecanismo equivalente. Não usar `StrictHostKeyChecking=no` nem confiar automaticamente em `ssh-keyscan` realizado no primeiro contato.

Preferir conectividade privada por VPN, bastion ou mecanismo do provedor quando disponível. Não expor SSH irrestrito à Internet nem executar runner privilegiado de produção na mesma VPS administrada.

A VPS atual não possui painel WHM; portanto, não presumir disponibilidade do HG Firewall Administration. O Ansible gerenciará o firewall local do Ubuntu. A existência de firewall externo à VPS deverá ser confirmada com a HostGator. Caso o SSH público restrito seja a única opção viável, documentar as origens permitidas, os limites de segurança e o caminho de recuperação.

## Reinstalação, backup e evidências

Uma reconstrução deverá seguir um runbook versionado e utilizar um **commit conhecido e aprovado**. Terraform e cloud-init só poderão participar do provisionamento quando houver suporte confirmado da HostGator; caso contrário, a criação da instância será uma etapa manual documentada no provedor.

A sequência de recuperação proposta é:

1. Confirmar acesso à instância e recuperar credenciais administrativas por mecanismo autorizado.
2. Restaurar o sistema operacional e executar a configuração básica pelo Ansible.
3. Instalar o k3s na versão compatível definida e restabelecer o estado necessário do cluster.
4. Restaurar o datastore do k3s, volumes e dados persistentes **quando necessário**, conforme o plano de backup apropriado; não presumir que os manifests GitOps substituem esses backups.
5. Reinstalar o ArgoCD pelo playbook de bootstrap e reaplicar o AppProject e a Application raiz.
6. Verificar a reconciliação das Applications de infraestrutura e das aplicações, inclusive CRDs do Gateway API, NGINX Gateway Fabric e cert-manager, na ordem de dependências.
7. Validar os certificados e Secrets necessários, a exposição HTTP/HTTPS, as rotas públicas e a conectividade interna.
8. Registrar versão, commit, execução, resultados dos testes e eventuais intervenções manuais.

O plano de backup deverá definir origem, destino, retenção, criptografia, restauração e responsáveis pelos dados do k3s e das aplicações. Também deverão ser avaliados backups dos Secrets e dos dados necessários ao funcionamento do ArgoCD e dos certificados. Uma restauração completa precisa ser **testada** antes de declarar a infraestrutura reconstruível.

A configuração essencial não poderá depender de mudanças manuais não documentadas. Falhas parciais do Ansible exigirão diagnóstico e procedimento de recuperação específico; repetir o playbook ou reverter um commit não constitui, por si só, rollback universal.

## Fluxo de execução automatizada

Pull Requests direcionados à `dev` executarão validações estáticas sem secrets de produção nem conexão com a VPS. O merge em `dev` não deverá disparar alterações em produção.

O apply de produção utilizará apenas código integrado à `main`, com filtro de caminhos pertinentes aos playbooks e configurações de Ansible, proteção do GitHub Environment `production`, aprovação obrigatória, validação de `github.ref == 'refs/heads/main'` e execução serializada por host ou ambiente.

Execuções manuais por `workflow_dispatch` também deverão respeitar a restrição à `main`, inclusive nas regras de deployment branches do Environment. Ver detalhes em [Fluxo GitHub Actions + Ansible](06-fluxo-github-actions-e-ansible.md).

## Referências

- [Divisão de responsabilidades](03-divisao-de-responsabilidades.md)
- [Secrets, SSH e segurança](05-secrets-ssh-e-seguranca.md)
- [Fluxo GitHub Actions + Ansible](06-fluxo-github-actions-e-ansible.md)
- [Fluxo do ArgoCD](../argocd/fluxo-argocd.md)
- [Estudo de NGINX e Gateway API](../nginx/README.md)
- [Issue #60 — Arquitetura de entrada HTTP/HTTPS](https://github.com/IFPBEsp/APAE-INFRA/issues/60)
- [Issue #86 — Divisão Terraform, Ansible e ArgoCD](https://github.com/IFPBEsp/APAE-INFRA/issues/86)
- [Issue #90 — Cluster k3s single-node](https://github.com/IFPBEsp/APAE-INFRA/issues/90)
- [Documentação cloud-init](https://cloudinit.readthedocs.io/)
- [Requisitos oficiais de rede do k3s](https://docs.k3s.io/installation/requirements)
- [Requisitos dos nós gerenciados pelo Ansible](https://docs.ansible.com/ansible/latest/getting_started/introduction.html#managed-nodes)
- [HostGator: acesso SSH à VPS](https://suporte.hostgator.com.br/hc/pt-br/articles/30812824748051-Como-acessar-um-servidor-via-SSH)
