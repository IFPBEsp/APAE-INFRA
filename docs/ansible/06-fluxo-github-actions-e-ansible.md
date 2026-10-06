# 06 — Fluxo GitHub Actions + Ansible

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Fluxo aprovado

```text
Pull Request
  └── validação estática, sem acesso à VPS ou secrets de produção
        ↓ revisão e merge
Apply disparado após merge
  └── aguarda aprovação no GitHub Environment de produção
        ↓ aprovação
Ansible aplica o commit aprovado na VPS
        ↓
Verificação de saúde e registro do resultado
```

O workflow pode também ser iniciado por `workflow_dispatch` para uma operação controlada. Inputs devem selecionar somente playbooks, tags e inventários previamente permitidos; não aceitar comandos arbitrários. Execuções que atingem produção passam pelo mesmo Environment protegido. O Environment protege o job de apply: disparo após merge não significa execução sem aprovação.

## Validação em Pull Request

O CI não modifica a VPS e não recebe chave SSH, senha Vault, host de produção ou outros secrets de produção. Validar:

- YAML e formatação conforme as ferramentas adotadas;
- `ansible-lint`;
- `ansible-playbook --syntax-check` para playbooks e inventários selecionados;
- versões fixadas de Ansible, collections e Actions.

`--check` remoto não roda no PR nem contra produção. Ele só pode ser executado contra ambiente de teste isolado, com credenciais próprias. Se não houver esse ambiente, omitir essa etapa em vez de conectar CI à VPS de produção. A aplicação de produção é o playbook real após a aprovação do Environment; `--check` não é pré-aprovação nem mecanismo de rollback.

## Aplicação

O job de apply:

1. usa o commit já revisado e mergeado;
2. instala versões de dependências fixadas;
3. vincula-se ao Environment protegido de produção;
4. valida o host SSH por `known_hosts` confiável;
5. instala secrets apenas no job que executa Ansible;
6. executa o playbook/inventário permitidos;
7. verifica serviços e informa commit, ambiente e resultado sem revelar dados sensíveis.

Definir `concurrency` por ambiente/host para serializar aplicações e não cancelar execução que já possa estar alterando a VPS. As permissões GitHub devem ser declaradas por job no menor nível possível. Fixar actions externas por SHA conforme as boas práticas do projeto.

## Acesso de rede do runner

Preferir rede privada via VPN/bastion ou caminho administrado pelo provider. A implementação depende do provider e da topologia, ainda não definidos. Não abrir SSH irrestrito à internet nem colocar runner privilegiado na própria VPS alvo. Se acesso público restrito for a única opção, documentar origem permitida, limites de IPs de runners hospedados, monitoramento e caminho de recuperação antes da implantação.

## Mudanças seguras em serviços

Roles devem validar antes de alterar o serviço ativo. Para NGINX:

```text
renderizar configuração candidata
        ↓
nginx -t
  ├── falha → não ativar/recarregar
  └── sucesso → instalar configuração e reload
```

Usar handlers para evitar reload sem mudança. O template/configuração anterior deve permanecer recuperável até a validação, e o serviço deve ser verificado após reload. Para mudanças de SSH/firewall, aplicar com sessão de recuperação e testar conectividade antes de encerrar. Atualizações de SO/Kubernetes precisam de procedimento e janela próprios; `--check` não é um rollback nem representa fielmente todos os módulos.

## Falhas, rollback e emergência

Uma falha interrompe o playbook por padrão. Não mascarar erro com `ignore_errors` sem justificativa. Ansible pode aplicar mudanças parciais; rollback depende do recurso. Para configuração versionada, reverter o commit e executar Ansible. Infraestrutura volta pelo Terraform e recursos de cluster pelo fluxo ArgoCD.

Se a automação estiver indisponível, permitir SSH break-glass por operador autorizado. Registrar a alteração e convertê-la em PR; executar Ansible depois para restabelecer o estado versionado.

## Fluxo Kubernetes/ArgoCD

O playbook de bootstrap do cluster instala ArgoCD e registra a Application raiz uma vez. Depois disso, Actions não deve aplicar manifests de workloads: ArgoCD os reconcilia conforme a política de sync documentada em [Fluxo do ArgoCD](../argocd/fluxo-argocd.md). No estado atual, as Applications filhas estão documentadas com sync manual; não presumir sync automático.

## Referências oficiais

- [Ansible lint](https://docs.ansible.com/projects/lint/)
- [Check mode e diff mode](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_checkmode.html)
- [GitHub Actions Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [GitHub Actions: controlar concorrência](https://docs.github.com/en/actions/using-jobs/using-concurrency)
- [GitHub Actions: hardening de segurança](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
