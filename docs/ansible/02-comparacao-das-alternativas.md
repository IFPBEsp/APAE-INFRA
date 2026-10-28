# 02 — Comparação das alternativas

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Critérios e premissas

A comparação é qualitativa. O resultado depende da qualidade dos scripts, playbooks e controles operacionais: GitHub Actions, por si só, não garante segurança, auditabilidade nem idempotência.

O cenário considerado é uma VPS HostGator com Ubuntu 22.04 LTS, destinada a hospedar um cluster **k3s single-node**, conforme a [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90). O repositório `APAE-INFRA` é a fonte da configuração declarada.

O estudo compara **formas de executar e controlar a configuração do host**, e não implementações de roteamento HTTP. Conforme a arquitetura selecionada no estudo da [issue #60](https://github.com/IFPBEsp/APAE-INFRA/issues/60), a entrada pública será realizada pelo **NGINX Gateway Fabric exposto diretamente no Kubernetes**, com roteamento por Gateway API. Portanto, NGINX externo e Certbot **não fazem parte do escopo obrigatório do Ansible**.

| Critério | Actions + SSH/scripts | Ansible direto | Actions + Ansible |
| --- | --- | --- | --- |
| Idempotência | Precisa ser implementada caso a caso nos scripts; há risco de efeitos repetidos | Boa quando módulos declarativos são usados; depende da disciplina operacional | Boa pelos mesmos recursos do Ansible, com execução padronizada |
| Reprodutibilidade | Comandos podem divergir entre workflows e acumular dependências implícitas | Playbooks são reproduzíveis, mas ambiente e versões locais podem variar | Alta quando versões, dependências, inventário e playbooks são versionados |
| Segurança | Credenciais e comandos privilegiados exigem controles próprios | Credenciais e logs ficam sob controle do operador; depende da estação e do processo | Permite centralizar secrets, permissões, aprovação e execução; runner e credenciais continuam sendo pontos críticos |
| Auditoria | Existem logs do workflow, mas o estado desejado tende a ficar fragmentado em comandos | Depende do registro e da padronização das execuções manuais | PR, revisão, commit, Environment e execução oferecem uma trilha consistente quando configurados |
| Manutenção | Inicialmente simples; tende a exigir tratamento manual de estados e erros | Reutilização por roles e módulos; operador mantém dependências e ambiente | Mesma modularidade do Ansible com CI padronizada; maior custo inicial de pipeline |
| Uso adequado | Comandos pontuais, sem pretensão de gerenciar estado contínuo | Bootstrap inicial, desenvolvimento, diagnóstico e contingência controlada | Configuração recorrente e caminho operacional padrão |

## 1. GitHub Actions + SSH/scripts

O workflow abre conexão SSH e executa comandos ou scripts imperativos. É uma abordagem rápida para tarefas pequenas, mas cada script precisa tratar estados preexistentes, falhas parciais, repetição e recuperação. Conforme o escopo cresce, a configuração pode se espalhar pelo YAML e por scripts auxiliares.

**Avaliação:** não recomendada como mecanismo permanente de gerenciamento de configuração. Ações SSH pontuais ainda podem ser úteis em operações excepcionais, desde que revisadas, autorizadas e registradas.

## 2. Ansible executado diretamente

Um operador executa playbooks e roles versionados a partir de uma estação administrativa autorizada. Isso mantém a configuração separada da execução e permite usar módulos declarativos, mas exige padronização de versões, credenciais e registros das operações.

É especialmente útil no **bootstrap da VPS existente**, quando ainda não houver um usuário e um caminho de acesso seguros para o runner do GitHub Actions, e em procedimentos emergenciais de recuperação.

**Avaliação:** adequado para bootstrap, desenvolvimento, troubleshooting e contingência; não será o fluxo recorrente principal para mudanças de produção.

## 3. GitHub Actions + Ansible

O GitHub Actions valida o conteúdo versionado, prepara dependências fixadas e executa os playbooks autorizados. O Ansible descreve e aplica o estado do host; o Actions controla o evento de execução, o ambiente, a aprovação e a rastreabilidade.

A divisão de responsabilidades proposta é:

- **Ansible:** configuração do Ubuntu, usuários, SSH, pacotes, firewall local, instalação e manutenção do k3s single-node e bootstrap inicial do ArgoCD, incluindo os objetos deliberadamente excluídos da reconciliação GitOps.
- **ArgoCD:** reconciliação dos recursos Kubernetes sob sua responsabilidade, incluindo os CRDs do Gateway API, o NGINX Gateway Fabric, os recursos Gateway/HTTPRoute e os workloads, observadas a ordem de instalação e as permissões adequadas.
- **GitHub Actions:** validação, aprovação e orquestração da execução do Ansible, sem administrar diretamente os mesmos recursos.
- **Terraform:** recursos externos ao host somente quando houver API ou integração suportada pela HostGator; a delimitação definitiva é tratada na [issue #86](https://github.com/IFPBEsp/APAE-INFRA/issues/86).

**Avaliação:** recomendada para mudanças recorrentes, com aprovação obrigatória para produção. A execução direta de Ansible permanece disponível como exceção controlada.

## Decisão

Adotar **GitHub Actions + Ansible** como fluxo normal de gerenciamento de configuração da VPS.

O fluxo proposto respeita as branches do repositório:

1. **Pull Requests para `dev`:** executar validações estáticas (`ansible-lint`, verificação de YAML e `ansible-playbook --syntax-check`), sem credenciais de produção ou conexão com a VPS.
2. **Merge em `dev`:** não executar aplicação automática em produção.
3. **Pull Request de `dev` para `main`:** exigir revisão e as validações aplicáveis.
4. **Push em `main`:** permitir o workflow de aplicação apenas quando houver alterações nos caminhos monitorados, incluindo playbooks, roles, inventários permitidos, configurações e o próprio workflow.
5. **GitHub Environment `production`:** exigir aprovação de revisor autorizado e restringir as branches de implantação exclusivamente à `main`.
6. **Aplicação:** executar apenas código já integrado à `main`, com verificação adicional de `github.ref == 'refs/heads/main'`, dependências fixadas, acesso SSH validado e concorrência serializada por ambiente/host.

O disparo manual por `workflow_dispatch` também deverá ficar restrito à `main`, ao Environment protegido e a entradas previamente autorizadas; não deverá aceitar comandos arbitrários, revisão Git informada pelo usuário ou playbooks não aprovados.

Essas restrições são **requisitos para a futura implementação do workflow**; este documento não afirma que o pipeline de aplicação já esteja instalado.

O desenho detalhado encontra-se em [06 — Fluxo GitHub Actions + Ansible](06-fluxo-github-actions-e-ansible.md), e a distribuição de responsabilidades em [03 — Divisão de responsabilidades](03-divisao-de-responsabilidades.md). A decisão consolidada está em [07 — Arquitetura proposta](07-arquitetura-proposta-e-proximos-passos.md).

## Limitações

- A execução depende de conectividade SSH com a VPS. Preferir VPN, bastion ou outro acesso privado quando disponível; o mecanismo concreto depende das capacidades do provedor.
- A chave de automação, as permissões administrativas no host e o runner são pontos sensíveis, mesmo com Environment protegido. Exigir validação da chave do host, controle de acesso e rotação de credenciais.
- Uma execução pode falhar após aplicar parte das tarefas. Ansible **não é transacional** e não oferece rollback universal; mudanças críticas exigem procedimento de recuperação e verificação posterior.
- Ansible converge o host quando executado; não mantém reconciliação contínua equivalente ao ArgoCD.
- A instalação e atualização de k3s em **single-node** podem interromper todas as aplicações. Exigir versões fixadas, janela de manutenção, backups apropriados e procedimento testado de recuperação.
- A proteção do firewall local precisa considerar a rede interna do k3s; UFW isoladamente não deve ser presumido suficiente para bloquear NodePorts.
- A arquitetura de Gateway API direto não elimina a necessidade de validar exposição das portas 80/443, certificados, privilégios e ordenação dos recursos Kubernetes na fase de implementação.
