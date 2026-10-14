# 05 — Secrets, SSH e segurança

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Princípios

- Nenhuma chave privada, senha, token ou certificado privado em texto claro no Git.
- Secrets de execução ficam em GitHub Environment Secrets e são disponibilizados somente aos jobs autorizados que realmente precisam deles.
- Ansible Vault é reservado a dados sensíveis que precisem ser versionados cifrados; a senha do Vault permanece fora do repositório.
- Workflows declaram permissões mínimas, fixam versões de Actions e dependências privilegiadas e não imprimem dados sensíveis.
- O acesso manual por SSH é excepcional; mudanças permanentes no host retornam ao Git e são reconciliadas pelo Ansible.
- Cada credencial deve ter proprietário, finalidade, escopo, política de rotação e procedimento de revogação definidos.
- O Ansible gerencia a VPS, o k3s single-node e o bootstrap do ArgoCD; não assume a gestão recorrente de certificados ou recursos de roteamento dentro do Kubernetes.

## Chaves SSH e identidade do host

Usar uma chave de automação dedicada, sem reutilizá-la para acesso pessoal. A chave privada fica em um Secret do GitHub Environment `production`, com rotação e revogação documentadas. O bootstrap instala a chave pública na VPS; o Ansible mantém `authorized_keys` e as políticas definitivas de SSH.

Para a VPS HostGator já existente, a documentação do provedor descreve acesso root por SSH. A credencial inicial deverá ser utilizada somente a partir de estação autorizada para criar e validar o usuário administrativo do Ansible, **sem disponibilizar a senha root inicial ao GitHub Actions**.

O pipeline deverá validar a identidade do host por meio de `known_hosts` cuja origem seja confiável, por exemplo, obtido por canal autenticado e conferido previamente ou emitido por uma autoridade SSH adotada pelo projeto. Não utilizar `StrictHostKeyChecking=no` nem confiar cegamente em `ssh-keyscan` executado na primeira conexão sem validação independente da fingerprint.

Preferir acesso privado via VPN ou bastion quando disponível. Caso o SSH público seja inevitável, restringir as origens e documentar as limitações dos endereços de saída dos runners hospedados pelo GitHub. Não instalar um runner privilegiado de produção na própria VPS gerenciada.

## Usuário e privilégios

Usar uma conta administrativa dedicada à automação, sem login por senha, com `sudo`/`become` apenas nas tarefas que exigem privilégios elevados. Como a instalação do k3s, as mudanças de firewall e a administração de serviços exigem acesso privilegiado, reconhecer explicitamente que essa conta possui alto impacto sobre a VPS.

Manter um acesso de emergência separado, protegido e testado. Restringir ou rotacionar o acesso de bootstrap somente após confirmar o acesso definitivo e o caminho de recuperação, sem encerrar antecipadamente a sessão administrativa funcional.

Não utilizar a mesma identidade ou chave para administração da VPS, acesso do ArgoCD ao Git e autenticação das aplicações.

## GitHub Secrets e Ansible Vault

| Tipo de dado | Armazenamento recomendado |
| --- | --- |
| Chave privada SSH do job Ansible | GitHub Environment Secret `production` |
| Senha de Ansible Vault, se utilizado | GitHub Environment Secret; nunca junto do arquivo cifrado |
| Fingerprint ou `known_hosts` validado | Configuração versionada ou variável protegida, conforme a política adotada |
| Chaves públicas e configuração não sensível | Git, quando apropriado |
| Credencial que precisa acompanhar configuração versionada | Ansible Vault, somente após justificar a necessidade |
| Segredo utilizado apenas durante a execução | Secret de runtime, sem persistência em artefatos ou logs |
| Credenciais do ArgoCD para repositórios Git | Mecanismo de secrets Kubernetes aprovado, com acesso restrito ao ArgoCD |
| Chaves privadas TLS e credenciais de emissão de certificados | Kubernetes Secrets e integração do cert-manager, com controles de acesso e backup definidos |

O Ansible Vault protege dados em repouso, mas não depois de descriptografados no runner ou no host. Usar `no_log: true` em tarefas que possam expor segredos e evitar `--diff` em arquivos sensíveis. Não guardar credenciais em outputs do Terraform, inventários, user-data, logs ou artefatos de CI.

A arquitetura selecionada para a entrada pública utiliza **NGINX Gateway Fabric com Gateway API diretamente exposto**, sem NGINX externo ou Certbot obrigatórios no host. A emissão e renovação TLS serão planejadas com cert-manager dentro do Kubernetes; o método de provisionar os Secrets necessários deverá ser definido sem registrar valores sensíveis no Git em texto claro.

O Ansible poderá utilizar credenciais temporárias e controladas durante o bootstrap do ArgoCD, mas não deverá continuar administrando os mesmos objetos Kubernetes que forem atribuídos à reconciliação do ArgoCD. O `AppProject` e a `Application` raiz permanecem sob o playbook enquanto estiverem excluídos do caminho reconciliado.

## Proteção do GitHub Actions e separação de jobs

O job de Pull Request executa lint, validações de YAML e `ansible-playbook --syntax-check` sem credenciais de produção nem conexão com a VPS.

O fluxo de produção segue `dev` → Pull Request para `main` → merge em `main` → execução aprovada. O merge em `dev` **não** deve disparar aplicação na VPS.

O job de apply deverá:

- Executar somente código de `main`, incluindo disparos manuais por `workflow_dispatch`, com validação explícita de `github.ref == 'refs/heads/main'`.
- Utilizar o GitHub Environment `production` com *required reviewers* e restrição de *deployment branches* à `main`.
- Receber os Secrets de produção somente após passar pelas proteções do Environment.
- Usar `permissions` mínimos e Actions fixadas por SHA, seguindo as políticas do repositório.
- Restringir playbooks, inventários e tags aceitos em disparos manuais; não aceitar comandos arbitrários nem referências Git fornecidas como entrada.
- Serializar execuções por VPS/ambiente via `concurrency`, sem cancelar automaticamente um apply que já esteja alterando o host.
- Registrar commit, ambiente, horário, status e verificações posteriores sem expor credenciais.

A aprovação do Environment **não substitui a revisão do código por Pull Request**. A origem do código implantado e a autorização da execução são controles distintos e necessários.

## Firewall, k3s e exposição de serviços

A role de firewall do Ansible deverá ser compatível com a rede do k3s single-node, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90). A documentação do k3s recomenda desabilitar o UFW ou, caso ele seja mantido, permitir a comunicação necessária entre pods e Services; os CIDRs padrão são `10.42.0.0/16` e `10.43.0.0/16`, respectivamente, sujeitos à configuração efetiva do cluster.

Restringir o acesso à API do Kubernetes (`6443/tcp`) às origens administrativas autorizadas. Alterações em SSH e firewall devem preservar uma sessão de recuperação e incluir testes de conectividade antes de encerrar a operação.

O UFW, isoladamente, não comprova o bloqueio de `NodePort`: regras e traduções realizadas pelo Kubernetes podem interferir no caminho esperado do firewall. Não expor desnecessariamente Services internos nem a faixa de NodePorts; validar as portas efetivamente acessíveis a partir de redes externas.

Na arquitetura selecionada, o Gateway Fabric será o ponto de entrada HTTP/HTTPS nas portas 80/443, por um mecanismo de exposição do k3s a ser validado na implementação. O Ansible deverá assegurar que a configuração da VPS não introduza conflitos com Traefik, ServiceLB ou outros serviços, sem assumir a gestão dos recursos Gateway API.

## Acesso emergencial, recuperação e resposta

Se GitHub Actions ou o caminho de rede habitual estiverem indisponíveis, um operador autorizado poderá acessar a VPS pelo procedimento de *break-glass*. Registrar o motivo, a alteração e o responsável; abrir PR para representar qualquer mudança permanente e executar Ansible posteriormente para restaurar a configuração versionada.

Em caso de suspeita de comprometimento, revogar e rotacionar a chave SSH e outros segredos afetados, verificar logs, revisar o acesso ao GitHub Environment e avaliar o impacto sobre as credenciais e os dados do Kubernetes.

O plano de recuperação deve contemplar tanto a configuração reproduzível do host quanto **backups e testes de restauração** do datastore do k3s, volumes persistentes e material sensível necessário à operação. Ansible e GitOps não substituem backups dos dados ou das chaves privadas indispensáveis à continuidade do serviço.

## Referências

- [Boas práticas de secrets do projeto](../boas-praticas/02-segredos-e-credenciais.md)
- [Boas práticas de GitHub Actions do projeto](../boas-praticas/07-github-actions.md)
- [Divisão de responsabilidades](03-divisao-de-responsabilidades.md)
- [Fluxo GitHub Actions + Ansible](06-fluxo-github-actions-e-ansible.md)
- [Estudo de TLS e certificados do Gateway](../nginx/03-tls-seguranca-e-acesso.md)
- [Requisitos de rede do k3s](https://docs.k3s.io/installation/requirements)
- [Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/index.html)
- [Ansible: conexão SSH](https://docs.ansible.com/ansible/latest/inventory_guide/connection_details.html)
- [GitHub Actions: secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions)
- [GitHub Actions: deployment environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [HostGator: acesso SSH à VPS](https://suporte.hostgator.com.br/hc/pt-br/articles/30812824748051-Como-acessar-um-servidor-via-SSH)
