# 06 — Fluxo GitHub Actions + Ansible

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Fluxo aprovado

```text
Pull Request para dev
  └── validação estática, sem acesso à VPS ou secrets de produção
        ↓
Revisão e merge em dev
  └── nenhuma aplicação automática em produção
        ↓
Pull Request de dev para main
  └── revisão e validações obrigatórias
        ↓
Merge em main
  └── workflow de apply acionado apenas para paths autorizados
        ↓
GitHub Environment production
  └── aprovação obrigatória de responsável autorizado
        ↓
Ansible aplica o commit aprovado na VPS
        ↓
Verificação de saúde e registro do resultado
```

A branch `dev` é utilizada para integração e validação das mudanças. O merge em `dev` não inicia um apply de produção.

A aplicação automática em produção somente poderá ser iniciada por um `push` na branch `main`, após integração das alterações aprovadas, e quando houver modificações nos caminhos monitorados pelo workflow Ansible.

Também será permitido `workflow_dispatch` para operações controladas. Entretanto, **qualquer execução destinada à produção deverá utilizar exclusivamente código da branch `main`, previamente revisado e integrado por Pull Request**.

Para garantir essa restrição, o GitHub Environment `production` deverá ser configurado com:

- **Deployment branches and tags:** permitir exclusivamente a branch `main`.
- **Required reviewers:** exigir aprovação de responsável autorizado antes do job de aplicação.
- **Environment secrets:** disponibilizar credenciais de produção apenas aos jobs vinculados ao Environment protegido.

O job de aplicação deverá possuir validação adicional da referência Git (`github.ref == 'refs/heads/main'`), inclusive em execuções iniciadas por `workflow_dispatch`. O checkout deverá utilizar o commit da execução autorizada, sem aceitar um `ref` arbitrário como input.

Os inputs do disparo manual deverão permitir somente playbooks, tags e inventários previamente autorizados. Não permitir comandos shell, caminhos, inventários ou referências Git arbitrários fornecidos pelo usuário.

**A aprovação do Environment não substitui a revisão de código.** O fluxo de produção exige tanto a integração prévia na `main` quanto a aprovação da execução. As proteções deverão ser verificadas na configuração real do repositório antes de habilitar o acesso à VPS.

## Validação em Pull Request

O CI não modifica a VPS e não recebe chave SSH, senha Vault, host de produção ou outros secrets de produção. Validar:

- YAML e formatação conforme as ferramentas adotadas;
- `ansible-lint`;
- `ansible-playbook --syntax-check` para playbooks e inventários selecionados;
- versões fixadas de Ansible, collections e Actions;
- consistência dos arquivos de inventário e variáveis não sensíveis;
- conformidade com o fluxo de branches e os caminhos monitorados.

`--check` remoto não roda no PR nem contra produção. Ele só poderá ser executado contra ambiente de teste isolado, com credenciais próprias. Se não houver esse ambiente, omitir essa etapa em vez de conectar a CI à VPS de produção.

O `--check` não substitui aprovação, aplicação real, testes de recuperação ou rollback.

## Aplicação

O job de apply:

1. Confirma que a execução utiliza a branch `main` e um commit permitido.
2. Instala versões fixadas das dependências.
3. Vincula-se ao Environment protegido de produção e aguarda sua aprovação.
4. Valida a identidade SSH da VPS utilizando `known_hosts` confiável.
5. Disponibiliza secrets apenas ao job que executa Ansible, sem registrá-los em logs ou artefatos.
6. Executa apenas o playbook e o inventário previamente autorizados.
7. Valida conectividade, serviços do host e, quando alterado, o estado do k3s.
8. Registra commit, ambiente e resultado, sem revelar informações sensíveis.

Definir `concurrency` por ambiente/host para serializar execuções e não cancelar um apply que já possa estar modificando a VPS. As permissões GitHub devem ser declaradas com o menor escopo necessário. Fixar Actions externas por SHA conforme as boas práticas do projeto.

### Exemplo de gatilhos para o futuro `ansible-apply.yml`

```yaml
name: Ansible Apply

on:
  push:
    branches:
      - main
    paths:
      - "ansible/**"
      - ".github/workflows/ansible-apply.yml"

  workflow_dispatch:

permissions:
  contents: read

jobs:
  apply:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    concurrency:
      group: ansible-production-vps
      cancel-in-progress: false
    steps:
      - name: Checkout do commit aprovado
        uses: actions/checkout@<SHA_COMPLETO_FIXADO>
      # Instalar dependências, validar a identidade SSH e executar
      # apenas playbooks/inventários autorizados em etapas futuras.
```

O YAML acima é **um exemplo conceitual**, não um workflow pronto para executar: substituir `<SHA_COMPLETO_FIXADO>` pelo commit completo e verificado da Action antes da implementação, e adicionar as etapas efetivas de aplicação e validação.

A proteção do Environment `production` deve ser configurada no GitHub; ela não é criada pelo YAML. O filtro de `paths` vale para `push`, não para `workflow_dispatch`. O bloqueio por branch no job e as regras do Environment permanecem obrigatórios para ambos os casos.

Se outros arquivos afetarem o comportamento do Ansible (por exemplo, arquivos de dependências ou scripts auxiliares fora de `ansible/`), eles também deverão ser incluídos no filtro antes da ativação. Para workflows de validação em PR, não reutilizar o filtro de produção de modo a deixar alterações relevantes sem checagem.

## Acesso de rede do runner

Preferir rede privada via VPN/bastion ou caminho administrado pelo provedor. A solução concreta depende dos recursos disponíveis na VPS HostGator e ainda deve ser definida.

Não abrir SSH irrestrito à Internet nem instalar runner privilegiado de produção na própria VPS administrada. Se o acesso público restrito for a única opção viável, documentar origens permitidas, limitações dos IPs de runners hospedados, monitoramento, rotação de credenciais e caminho de recuperação.

O acesso à API Kubernetes (`6443/tcp`) também deverá ser restrito a origens administrativas autorizadas; a automação rotineira do host não exige expor indiscriminadamente essa API ou os Services do cluster.

## Mudanças seguras em serviços

As roles deverão validar configurações antes de ativá-las e evitar reinicializações desnecessárias. Exemplos:

- **SSH:** validar a sintaxe da configuração e testar uma nova sessão antes de restringir o acesso anterior.
- **Firewall:** preservar acesso administrativo e recuperação; validar comunicação entre pods, Services e componentes do k3s.
- **Serviços `systemd`:** validar arquivos de configuração quando houver ferramenta apropriada e utilizar handlers somente após mudanças efetivas.
- **k3s:** fixar versões, documentar parâmetros de instalação, planejar janela de manutenção e verificar a saúde do cluster após alterações.

Na arquitetura selecionada no [estudo NGINX/Gateway API](../nginx/README.md), **NGINX Gateway Fabric recebe diretamente o tráfego público HTTP/HTTPS dentro do k3s**. Portanto, configurar NGINX externo, executar `nginx -t` no host ou gerenciar Certbot **não são etapas obrigatórias do workflow Ansible**.

A validação das configurações do Gateway Fabric, dos recursos Gateway API, do cert-manager e dos certificados ocorre no fluxo GitOps/Kubernetes sob responsabilidade do ArgoCD, respeitando a política de sincronização de cada Application.

Alterações de SSH/firewall exigem sessão ou caminho de recuperação. Atualizações de SO e k3s exigem procedimentos e janelas de manutenção específicos. `--check` não é mecanismo de rollback nem reproduz fielmente todos os módulos.

## Falhas, rollback e emergência

Uma falha interrompe o playbook por padrão. Não mascarar erros com `ignore_errors` sem justificativa. O Ansible pode deixar mudanças parcialmente aplicadas; a recuperação depende do recurso e deverá ter procedimento documentado.

Para configurações do host versionadas, avaliar a reversão do commit e a reexecução controlada do Ansible, sem presumir que isso reverta upgrades, migrações ou mudanças destrutivas. Recursos externos do provedor seguem o processo aprovado de Terraform, **quando houver integração suportada**, e os recursos Kubernetes seguem o fluxo ArgoCD.

Como o k3s é single-node, atualizações que reiniciem componentes críticos podem interromper todas as aplicações. Exigir backup consistente do datastore e dos dados persistentes relevantes, plano de recuperação, compatibilidade de versões e validação após manutenção. Ansible não substitui backup nem restauração de dados.

Se a automação estiver indisponível, permitir acesso SSH *break-glass* por operador autorizado. Registrar a intervenção, representar a mudança permanente em PR e executar Ansible para restabelecer o estado versionado. Rotacionar credenciais quando necessário.

## Fluxo Kubernetes/ArgoCD

O Ansible prepara a VPS, instala e configura o k3s single-node e executa o bootstrap inicial do ArgoCD. Também mantém o `AppProject` e a Application raiz enquanto os manifestos correspondentes (`project.yaml` e `app-of-apps.yaml`) permanecerem excluídos da reconciliação do ArgoCD.

Após o bootstrap, **GitHub Actions + Ansible não deve aplicar diretamente manifestos de workloads nem assumir o gerenciamento do Gateway API**. O ArgoCD reconcilia as Applications filhas e os componentes Kubernetes que lhe foram atribuídos, incluindo:

- CRDs do Gateway API;
- NGINX Gateway Fabric e seu data plane;
- recursos GatewayClass, Gateway e HTTPRoute;
- cert-manager e os recursos de certificados, quando implementados;
- Services, Deployments e observabilidade executados no cluster.

A ordem de dependências deverá ser tratada por Applications e políticas de sincronização apropriadas: primeiro os CRDs necessários, depois os controllers e, por fim, os recursos dependentes. Components de infraestrutura que exigirem recursos cluster-scoped ou namespaces próprios deverão contar com AppProject e permissões específicas; não ampliar irrestritamente o AppProject compartilhado das aplicações.

A política de sincronização das Applications filhas atualmente documentada é manual; não presumir sincronização automática. O fluxo detalhado está em [Fluxo do ArgoCD](../argocd/fluxo-argocd.md).

## Referências oficiais

- [Ansible lint](https://docs.ansible.com/projects/lint/)
- [Check mode e diff mode](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_checkmode.html)
- [GitHub Actions Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [GitHub Actions: controlar concorrência](https://docs.github.com/en/actions/using-jobs/using-concurrency)
- [GitHub Actions: hardening de segurança](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [Estudo de NGINX e Gateway API](../nginx/README.md)
