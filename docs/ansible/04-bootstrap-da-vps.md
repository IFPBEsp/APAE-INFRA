# 04 — Bootstrap da VPS

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Objetivo

Preparar a VPS HostGator simples atual, sem painel, com Ubuntu 22.04 LTS, para que Ansible possa assumir sua configuração e definir o fluxo de reconstrução. Para novas instâncias, usar **Terraform + cloud-init mínimo + Ansible** somente se o plano/provedor confirmar suporte a provisionamento por API e user-data. Para a VPS existente, não presumir que Terraform ou cloud-init possam reprovisionar ou injetar user-data retroativamente.

## Fluxo inicial

1. **Instância existente:** operador autorizado acessa o SSH root fornecido pela HostGator a partir de estação controlada, valida a identidade do host e executa o bootstrap versionado. Não colocar a senha root inicial em GitHub Actions.
2. Ansible cria usuário administrativo com chave pública, configura `sudo`, valida nova sessão e restringe root SSH somente depois de confirmar o acesso alternativo e o caminho de recuperação.
3. Ansible configura o estado completo do host e instala Kubernetes após decisão da distribuição/topologia.
4. Playbook separado instala ArgoCD, aplica o AppProject e registra a Application raiz.
5. ArgoCD assume a reconciliação das Applications filhas e dos demais recursos Kubernetes que lhe forem atribuídos.

Para uma instância futura, Terraform provisiona recursos do provider e cloud-init cria o acesso inicial somente se HostGator confirmar suporte para o plano. Depois, Ansible segue as etapas 2–5.

### Responsabilidades do cloud-init

Executar apenas o necessário para acesso de gestão inicial:

- criar usuário administrativo de bootstrap sem autenticação por senha;
- instalar a chave pública autorizada;
- garantir Python se ausente na imagem;
- conceder `sudo` suficiente para o Ansible completar a configuração;
- manter SSH acessível enquanto o Ansible aplica o hardening definitivo.

Não instalar NGINX, Certbot, Kubernetes ou agentes, nem manter configuração recorrente do host via cloud-init. User-data não deve conter chave privada, senha ou token permanente. Considerar que user-data pode ser retido pelo provider ou exposto no state: fornecer somente dados não secretos.

### Configuração pelo Ansible

O playbook recorrente assume SO, usuários, SSH, pacotes, firewall local, NGINX/Certbot, diretórios e serviços. Alterações em SSH/firewall devem preservar uma sessão de recuperação e validar o novo acesso antes de encerrar a sessão atual. Deve existir caminho de console/recuperação provido pelo host.

### Bootstrap do ArgoCD

Após o cluster estar saudável, um playbook Ansible separado instala o ArgoCD, aplica o `AppProject` exigido pela raiz e registra a Application raiz definida no repositório. Essas definições de bootstrap também permanecem sob responsabilidade do playbook: o guia atual do ArgoCD exclui `project.yaml` e `app-of-apps.yaml` do path reconciliado pela raiz. Mudanças nesses dois arquivos exigem nova execução controlada do playbook; Applications filhas e seus recursos seguem sob ArgoCD. Não fazer Ansible e ArgoCD aplicar os mesmos objetos.

Se for necessário reinstalar o cluster, executar novamente o bootstrap a partir de uma revisão conhecida e repetir a verificação da raiz. O processo de bootstrap deve ser documentado e testável antes da VPS ser considerada reconstruível.

## Identidade e conectividade SSH

O bootstrap instala somente chave pública. A chave privada fica em GitHub Environment Secret para o job de apply ou em estação autorizada para recuperação. As instruções públicas da HostGator indicam login SSH root para VPS Linux e documentam portas de conexão que devem ser confirmadas na instância específica. Root é um acesso inicial/de recuperação, não o usuário permanente do Ansible. O runner valida a identidade do host via `known_hosts` obtido por canal confiável ou mecanismo equivalente; não usar `StrictHostKeyChecking=no` nem confiar cegamente em `ssh-keyscan` feito no primeiro contato sem validação independente.

Preferir caminho privado de acesso via VPN/bastion quando disponível. A escolha específica depende do provider/topologia. Não expor SSH irrestrito à internet e não instalar runner privilegiado de produção na própria VPS gerenciada.

O plano atual é sem painel; portanto, não depende de WHM/HG Firewall Administration. Ansible gerenciará o firewall local do Ubuntu. A existência de firewall de rede externo não está confirmada. Se o SSH estiver exposto publicamente, restringir a origem conforme as capacidades disponíveis e documentar o risco residual.

## Reinstalação e evidências

Uma reconstrução futura deve começar por Terraform/cloud-init apenas se a HostGator confirmar API de provisionamento e user-data para o plano utilizado; caso contrário, documentar e executar a criação inicial no portal do provedor. Em ambos os casos, executar playbooks Ansible e verificar serviços, acesso e estado do cluster. Registrar no runbook o método de acesso de recuperação, as versões usadas e os critérios de sucesso. A configuração essencial não pode depender de alteração manual não registrada.

## Referências

- [Responsabilidades das ferramentas](03-divisao-de-responsabilidades.md)
- [Secrets, SSH e segurança](05-secrets-ssh-e-seguranca.md)
- [Documentação cloud-init](https://cloudinit.readthedocs.io/)
- [Requisitos de nós gerenciados pelo Ansible](https://docs.ansible.com/ansible/latest/getting_started/introduction.html#managed-nodes)
- [HostGator: acesso SSH à VPS](https://suporte.hostgator.com.br/hc/pt-br/articles/30812824748051-Como-acessar-um-servidor-via-SSH)
- [HostGator: abertura e fechamento de portas](https://www.hostgator.com.br/blog/como-abrir-e-fechar-portas-em-um-servidor-da-hostgator/)
