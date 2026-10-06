# 02 — Comparação das alternativas

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Critérios e premissas

A comparação é qualitativa. O resultado depende da qualidade dos scripts/playbooks e dos controles operacionais: Actions, por si só, não garante segurança, auditabilidade nem idempotência. Considera-se execução em VPS Linux, configuração recorrente e uso do APAE-INFRA como fonte de verdade.

| Critério | Actions + SSH/scripts | Ansible direto | Actions + Ansible |
| --- | --- | --- | --- |
| Idempotência | Precisa ser implementada caso a caso nos scripts; fácil produzir efeitos repetidos | Boa quando os módulos declarativos são usados; depende de disciplina do operador | Boa pelos mesmos recursos do Ansible, com execução padronizada |
| Reprodutibilidade | Comandos podem divergir entre workflows e acumular dependências implícitas | Playbooks são reproduzíveis, mas ambiente e versões locais podem variar | Alta se versões, dependências, inventário e playbooks forem versionados |
| Segurança | Credenciais e comandos privilegiados ficam no caminho de cada script; controles precisam ser construídos | Credenciais e logs ficam sob controle do operador; postura depende da estação/processo | Pode centralizar secrets, permissões, aprovação e execução; runner e credenciais continuam sendo pontos críticos |
| Auditoria | Há logs do workflow, mas o estado desejado tende a ficar imperativo e fragmentado | Pode haver logs, mas histórico e contexto variam entre operadores | PR, revisão, commit, Environment e run oferecem trilha consistente quando configurados |
| Manutenção | Inicialmente simples; tende a exigir tratamento manual de estados e erros | Reutilização por roles e módulos; operador mantém dependências e ambiente | Mesma modularidade do Ansible com CI padronizada; maior custo inicial de pipeline |
| Uso adequado | Comandos pontuais simples, sem pretensão de gerenciar estado contínuo | Desenvolvimento, diagnóstico, bootstrap ou operação excepcional controlada | Configuração recorrente e caminho operacional padrão |

## 1. GitHub Actions + SSH/scripts

O workflow abre SSH e executa comandos ou scripts imperativos. É rápido para uma tarefa pequena, mas cada script precisa tratar usuário já existente, arquivo sem mudança, erro parcial, repetição e rollback. Conforme o escopo cresce, a configuração se espalha pelo YAML e por scripts auxiliares.

**Avaliação:** não recomendado como mecanismo permanente de configuration management. Ações SSH pontuais ainda podem ser úteis em operações excepcionais, desde que revisadas e registradas.

## 2. Ansible executado diretamente

O operador executa playbooks e roles versionados a partir de uma estação administrativa. Mantém a configuração separada da execução e oferece módulos declarativos, mas requer padronização de versões, credenciais e registro das execuções.

**Avaliação:** adequado para desenvolvimento, troubleshooting e contingência; não será o fluxo recorrente principal.

## 3. GitHub Actions + Ansible

Actions instala dependências fixadas, valida e executa os playbooks versionados. Ansible define o estado do host; Actions controla o momento, o ambiente, a aprovação e o registro.

**Avaliação:** recomendado para mudanças recorrentes, com aprovação obrigatória em produção. A execução manual de Ansible continua disponível como exceção controlada.

## Decisão

Adotar **GitHub Actions + Ansible** para operação normal. PR executa validações estáticas sem credenciais ou conexão com a VPS. Após merge, o workflow de apply é disparado e aguarda aprovação pelo Environment protegido de produção. `workflow_dispatch` permite execuções controladas e também passa pela proteção do ambiente.

O desenho detalhado do fluxo e seus controles está em [06 — Fluxo GitHub Actions + Ansible](06-fluxo-github-actions-e-ansible.md). A decisão consolidada está em [07 — Arquitetura proposta](07-arquitetura-proposta-e-proximos-passos.md).

## Limitações

- A execução depende de conectividade SSH. Preferir acesso privado via VPN/bastion quando disponível; a solução concreta depende do provider.
- Credenciais do runner e acesso administrativo à VPS são riscos privilegiados e devem ter escopo mínimo e rotação.
- Uma execução pode falhar após aplicar parte das tarefas; Ansible não é transação nem rollback universal.
- Ansible converge o host quando executado; não mantém um controlador contínuo equivalente ao ArgoCD.
