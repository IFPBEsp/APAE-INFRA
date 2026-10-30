# Backup e recuperação do k3s — APAE Produção

## Ambiente

- **Cluster:** k3s single-node na VPS HostGator
- **Versão inicial:** `v1.36.5+k3s1`
- **Provisionamento:** Ansible, issue #90
- **Datastore:** SQLite embarcado (confirmado na VPS em 30/10/2026)
- **Modo de operação:** SQLite com arquivos WAL
- **Configuração:** `/etc/rancher/k3s/config.yaml`
- **Kubeconfig administrativo:** `/etc/rancher/k3s/k3s.yaml`

Antes de executar um procedimento de recuperação, confirmar o tipo de datastore utilizado.

## Dados que precisam ser preservados

| Caminho | Finalidade |
|---|---|
| `/var/lib/rancher/k3s/server/db/` | Datastore SQLite do cluster |
| `/var/lib/rancher/k3s/server/token` | Token original necessário à recuperação |
| `/etc/rancher/k3s/config.yaml` | Configuração declarativa do servidor |

O repositório Git mantém os arquivos Ansible que recriam a configuração do host. Não armazenar tokens, kubeconfigs administrativos ou backups contendo dados sensíveis no Git.

**Atenção:** o backup do datastore Kubernetes não substitui backups dos volumes persistentes das aplicações, como bancos PostgreSQL e arquivos armazenados por workloads.

## Procedimento de backup

Para obter uma cópia consistente dos arquivos SQLite, realizar o backup em uma janela de manutenção, com o serviço k3s interrompido.

```bash
sudo systemctl stop k3s
```

Criar um diretório protegido e copiar os dados:

```bash
BACKUP_DIR="/root/k3s-backup-$(date +%Y%m%d-%H%M%S)"

sudo install -d -m 0700 "$BACKUP_DIR"

sudo cp -a /var/lib/rancher/k3s/server/db "$BACKUP_DIR/"
sudo cp -a /var/lib/rancher/k3s/server/token "$BACKUP_DIR/token"
sudo cp -a /etc/rancher/k3s/config.yaml "$BACKUP_DIR/config.yaml"

sudo chmod -R go-rwx "$BACKUP_DIR"
```

Reiniciar e validar o cluster:

```bash
sudo systemctl start k3s
sudo k3s kubectl wait --for=condition=Ready nodes --all --timeout=120s
sudo k3s kubectl get pods -A
```

Transferir o backup por um canal seguro para um destino externo à VPS, com criptografia, controle de acesso e política de retenção. Um backup mantido somente no disco da mesma VPS não protege contra perda completa do servidor.

O datastore utiliza SQLite em modo WAL. O backup deve preservar o diretório completo server/db, incluindo os arquivos necessários à consistência do banco. Não copiar isoladamente state.db enquanto o serviço estiver em execução.

## Procedimento de restauração

A restauração é uma **operação destrutiva**: substitui o estado atual do datastore pelo estado preservado no backup.

Não executá-la em produção sem janela de manutenção, backup recente e plano de reversão.

Procedimento de referência:

1. Confirmar a versão do k3s e a compatibilidade com o backup.
2. Garantir que o Ansible tenha restaurado as configurações de sistema, SSH e firewall.
3. Interromper o serviço k3s.
4. Preservar separadamente o estado atual antes de substituí-lo.
5. Restaurar o conteúdo original do diretório `server/db` e o token correspondente.
6. Conferir permissões e configuração do servidor.
7. Iniciar o k3s e verificar nós, pods e aplicações.
8. Restaurar separadamente os volumes persistentes das aplicações, quando necessário.

A restauração deve ser ensaiada em ambiente isolado antes de sua utilização em produção.

## Verificações após recuperação

```bash
sudo systemctl is-active k3s
sudo k3s --version
sudo k3s kubectl get nodes -o wide
sudo k3s kubectl get pods -A
sudo k3s secrets-encrypt status
```

Executar também o playbook de verificação Ansible e o smoke test temporário.

## Limitações e próximos passos

- O procedimento documentado ainda precisa de um teste real de restauração em ambiente isolado.
- Definir armazenamento externo, criptografia, retenção e frequência dos backups.
- Automatizar backup e monitoramento em tarefa específica, sem executar restauração automaticamente.
- Incluir uma estratégia de backup para os volumes persistentes e dados das aplicações.
- Validar o processo após mudanças de versão do k3s.

Referência: [Documentação oficial de backup e restauração do k3s](https://docs.k3s.io/datastore/backup-restore).
