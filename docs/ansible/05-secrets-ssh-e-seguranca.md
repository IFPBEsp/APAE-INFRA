# 05 — Secrets, SSH e segurança

[← Índice do estudo](README.md) · [Síntese e decisões](07-arquitetura-proposta-e-proximos-passos.md)

## Princípios

- Nenhuma chave privada, senha, token ou certificado privado em texto claro no Git.
- Secrets de runtime ficam em GitHub Secrets/Environment Secrets e só são expostos ao job de apply que precisa deles.
- Ansible Vault é reservado a dados sensíveis que precisem ser versionados cifrados; a senha do Vault fica fora do repositório.
- Workflows declaram permissões mínimas, fixam Actions/dependências privilegiadas e não imprimem dados sensíveis.
- Acesso manual SSH é excepcional; alterações permanentes voltam ao Git e são reconciliadas por Ansible.

## Chaves SSH e identidade do host

Usar uma chave de automação dedicada, sem reutilizá-la para uso pessoal. A chave privada fica em um Secret do Environment de produção, com rotação e revogação documentadas. Bootstrap entrega a chave pública ao host; Ansible mantém `authorized_keys` e políticas definitivas. Para a VPS HostGator já existente, a documentação do provedor descreve root via SSH; usar a credencial inicial somente de uma estação autorizada para criar e validar o usuário Ansible, sem disponibilizar senha root ao workflow.

O pipeline deve validar a chave do host por `known_hosts` cuja origem seja confiável (por exemplo, obtida no provisionamento por canal autenticado ou emitida por uma autoridade SSH adotada pelo projeto). Não desabilitar host-key checking nem aceitar automaticamente uma chave coletada em rede não verificada.

O caminho de rede preferencial é privado via VPN/bastion, se o provider suportar. SSH público só pode ser considerado com origem restrita e revisão das limitações de IPs de runners hospedados. Não instalar um runner de produção privilegiado na própria VPS alvo.

## Usuário e privilégios

Usar conta administrativa dedicada à automação, sem login por senha, com `sudo`/`become` para as tarefas que exigem root. Como instalação de pacotes, firewall e serviços requer privilégio administrativo amplo, documentar que o usuário é privilegiado; evitar prometer isolamento granular que Ansible não oferece para essas tarefas.

Manter acesso de emergência separado e protegido. Remover ou rotacionar o acesso de bootstrap depois de validar o acesso definitivo, sem eliminar o caminho de recuperação fora da sessão que está sendo alterada.

## GitHub Secrets e Ansible Vault

| Tipo de dado | Armazenamento recomendado |
| --- | --- |
| Chave privada SSH do job | GitHub Environment Secret de produção |
| Senha de Ansible Vault | GitHub Environment Secret; nunca junto do arquivo cifrado |
| Chaves públicas e configuração não sensível | Git, quando apropriado |
| Credencial que precisa acompanhar a configuração versionada | Ansible Vault, somente após avaliar necessidade |
| Segredo usado apenas durante execução | Secret de runtime, sem persistir em artefato/log |

Vault protege dados em repouso, não depois de descriptografados no runner/host. Usar `no_log: true` em tarefas que possam expor segredos; não habilitar `--diff` para conteúdo sensível. Não guardar credenciais nos outputs do Terraform, inventários ou user-data.

## Separação de jobs

O job de PR executa lint e verificações estáticas sem credenciais nem conexão à VPS. Secrets de produção são fornecidos apenas ao job de apply, vinculado ao Environment protegido. Execuções concorrentes para o mesmo host/ambiente são serializadas.

## Acesso emergencial e resposta

Se Actions ou a rede privada estiver indisponível, operador autorizado pode acessar a VPS por mecanismo de break-glass. Registrar a intervenção, abrir PR para representar a mudança permanente e executar Ansible para reconciliar o estado. Rotacionar credenciais expostas ou usadas fora do fluxo normal.

## Referências

- [Boas práticas de secrets do projeto](../boas-praticas/02-segredos-e-credenciais.md)
- [Boas práticas de GitHub Actions do projeto](../boas-praticas/07-github-actions.md)
- [Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/index.html)
- [Ansible: conexão SSH](https://docs.ansible.com/ansible/latest/inventory_guide/connection_details.html)
- [GitHub Actions: secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions)
- [HostGator: acesso SSH à VPS](https://suporte.hostgator.com.br/hc/pt-br/articles/30812824748051-Como-acessar-um-servidor-via-SSH)
