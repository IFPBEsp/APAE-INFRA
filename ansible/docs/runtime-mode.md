# Alternância entre Docker Compose e K3s

Procedimento operacional da [issue #140](https://github.com/IFPBEsp/APAE-INFRA/issues/140).
As trocas são iniciadas manualmente pelo administrador. Não há agendamento
de troca nem execução pelo GitHub Actions nesta etapa.

## Objetivo e limites

A VPS possui aproximadamente 4 GiB de memória e dois vCPUs. O modo Compose
disponibiliza os produtos para demonstrações e testes com a APAE. O modo
cluster libera os recursos dessas aplicações para continuar a implantação
do K3s e do ArgoCD.

PostgreSQL e MinIO compartilhado ficam no Docker nos dois modos. A alternância
não migra dados para Kubernetes, não copia arquivos e não cria bancos novos.
O mesmo banco e os mesmos objetos serão usados pelas aplicações Kubernetes
quando a conexão interna restrita for implementada.

Os playbooks não fazem build, pull de imagens, atualização dos produtos,
bootstrap do cluster nem sincronização de Applications do ArgoCD. Os arquivos
Compose e as imagens da demonstração permanecem fixos. Mudanças nesse ambiente
devem ser tratadas explicitamente, fora da troca de modo.

## Arquivos da implementação

| Arquivo | Responsabilidade |
| --- | --- |
| `ansible/playbooks/activate-compose.yml` | Solicitar o modo Compose. |
| `ansible/playbooks/activate-cluster.yml` | Solicitar o modo cluster. |
| `ansible/playbooks/configure-runtime-tls.yml` | Instalar ou atualizar scripts e timer TLS. |
| `ansible/roles/runtime_mode/` | Pré-requisitos, trava, parada, inicialização e verificações. |
| `ansible/inventories/production/group_vars/production.yml` | Inventário operacional, ordem dos projetos, portas, verificações e limites. |

Consulte também o [guia TLS](runtime-tls.md) e as
[evidências de validação](runtime-mode-evidence.md).

## Inventário operacional

### Serviços permanentes

| Container | Volume nomeado | Destino no container |
| --- | --- | --- |
| `apae-postgres` | `apae_postgres_data` | `/var/lib/postgresql/data` |
| `apae-minio-shared` | `apae-minio-shared_minio-shared-data` | `/data` |

Esses containers devem estar rodando antes da troca. A role verifica seu estado
e os volumes esperados antes e depois da operação. Se estiverem parados ou com
montagens diferentes, a troca falha; a role não tenta recriá-los ou recuperá-los.

Os containers legados `apae-geral-minio`, `apae-gestao-minio` e
`apae-atendimento-minio` devem permanecer parados. Não fazem parte da seleção
de serviços iniciados pelos playbooks.

### Aplicações do Compose

Ordem de inicialização; a parada usa a ordem inversa:

| Projeto | Diretório na VPS | Arquivos | Serviços selecionados |
| --- | --- | --- | --- |
| Geral | `/opt/apae/geral` | `compose.yml`, `compose.shared.yaml` | `api` |
| Gestão | `/opt/apae/gestao` | `compose.yml`, `compose.shared.yaml` | `api` |
| Atendimento | `/opt/apae/atendimento` | `compose.yml`, `compose.shared.yaml` | `api`, `frontend` |
| Frontends | `/opt/apae/frontends` | `compose.yml` | `geral`, `gestao` |
| Site comemorativo | `/opt/apae/site-comemorativo` | `compose.yaml` | `site` |
| Proxy | `/opt/apae/proxy` | `compose.yml` | `proxy` |

O serviço `migrate` do site não é selecionado. O `up` utiliza `--no-deps`,
`--no-build`, `--pull never` e `--wait`. Isso evita iniciar dependências antigas
e exige que as imagens necessárias já estejam no Docker local.

As APIs ainda podem executar migrations automaticamente durante sua própria
inicialização. Excluir um serviço chamado `migrate` não desabilita o Flyway
ou outra ferramenta incorporada à aplicação.

### Componentes do cluster

A lista atual de disponibilidade obrigatória contém:

- `kube-system`: deployments `coredns`, `local-path-provisioner` e `metrics-server`.
- `argocd`: deployments `argocd-redis`, `argocd-repo-server` e `argocd-server`;
  statefulset `argocd-application-controller`.

O Ansible inicia o K3s e aguarda esses recursos. A retomada do ArgoCD segue
a política de sincronização já declarada nos manifests, sem executar
`argocd app sync` pelo playbook. Aplicações futuras devem ser incorporadas às
verificações quando se tornarem necessárias para considerar o modo disponível.

## Preparação e comandos

Na máquina de administração, use o inventário de produção existente e o
diretório `ansible/` do repositório. O acesso utiliza o usuário administrativo
`ansible`, chave SSH e sudo; a porta administrativa da VPS é `22022`.
Os dados específicos do host ficam no inventário local, sem versionar chaves,
senhas ou arquivos `.env` dos produtos.

Instale a automação TLS antes da primeira ativação do Compose:

```bash
ansible-playbook playbooks/configure-runtime-tls.yml --syntax-check
ansible-playbook playbooks/configure-runtime-tls.yml
```

Para disponibilizar os produtos:

```bash
ansible-playbook playbooks/activate-compose.yml --syntax-check
ansible-playbook playbooks/activate-compose.yml
```

Para liberar a VPS para o desenvolvimento do cluster:

```bash
ansible-playbook playbooks/activate-cluster.yml --syntax-check
ansible-playbook playbooks/activate-cluster.yml
```

Não use `--check`, `--start-at-task` ou seleção de tarefas para contornar as
etapas de segurança. Os playbooks rejeitam `--check`; `--syntax-check` valida
a sintaxe sem simular a troca.

Antes de executar, combine a janela de indisponibilidade e confirme que não
há operações de apresentação, upload ou manutenção concorrentes. A troca
interrompe as aplicações do modo anterior.

## Sequência e verificações

### Pré-requisitos comuns

Antes de alterar serviços, a role adquire a trava e confere:

- Modo solicitado e estrutura do inventário operacional.
- Acesso ao Docker e disponibilidade do Compose.
- Arquivos Compose, configuração e serviços selecionados.
- Containers e volumes de PostgreSQL e MinIO; ausência dos MinIO legados ativos.
- Executáveis do K3s e unidades systemd necessárias.
- Memória total de pelo menos 3500 MiB e espaço livre de pelo menos 1024 MiB
  no filesystem raiz, conforme valores ajustáveis do inventário.
- Para Compose: formato do certificado, núcleo TLS instalado e imagens locais
  dos produtos e do Certbot.

O limite de memória confere a capacidade total, não a memória disponível para
cada workload. A role não impõe limites de consumo nem substitui o acompanhamento
de recursos da VPS. As verificações das portas do destino acontecem após a parada
do modo anterior, porque ele pode estar usando essas portas legitimamente.

### Ativar Compose

1. Parar e desabilitar o serviço K3s.
2. Quando houver atividade do K3s, executar `k3s-killall.sh` para encerrar seus
   containers e limpar sua rede. Parar apenas o serviço não basta para liberar
   os recursos. O script não desinstala o cluster.
3. Confirmar ausência dos processos de containers do K3s e fechamento da API
   local na porta 6443. Um arquivo de socket antigo, sem listener, não é
   interpretado sozinho como atividade do cluster.
4. Conferir as portas 80, 443 e 9003. Publicações Docker existentes só são
   aceitas se pertencerem ao proxy Compose configurado.
5. Renovar o certificado, se necessário, sob a mesma trava da alternância.
6. Iniciar os serviços selecionados na ordem do inventário.
7. Validar e recarregar o Nginx para atualizar os destinos dos containers.
8. Conferir os cinco endpoints HTTPS com certificado confiável: Geral, Gestão,
   Atendimento, site comemorativo e saúde pública do MinIO na porta 9003.
9. Conferir novamente os serviços de dados e registrar `compose` como concluído.

HTTP 200 nas páginas não valida todas as funções do produto. Após mudanças
relevantes, também faça login e confira registros e documentos no navegador.

### Ativar cluster

1. Parar as aplicações Compose na ordem inversa, começando pelo proxy.
2. Conferir ausência de publicações Docker nas portas 80 e 443; antes de iniciar
   um K3s inativo, conferir também se as portas locais estão livres.
3. Iniciar e habilitar `k3s-api-firewall`; verificar as regras existentes de
   proteção IPv4 e IPv6 nas portas administrativas definidas pelo provisionamento.
4. Iniciar e habilitar o K3s.
5. Aguardar a API na porta 6443, `/readyz`, nós `Ready` e rollout dos componentes
   obrigatórios definidos no inventário.
6. Conferir os serviços de dados e registrar `cluster` como concluído.

No estado atual, o endpoint público do MinIO na porta 9003 depende do proxy
Compose e fica indisponível no modo cluster. O container e seus dados continuam
ativos. O acesso público aos documentos no cluster dependerá da implementação
do Gateway e dos endpoints correspondentes.

## Conferir o resultado na VPS

```bash
sudo cat /var/lib/apae/runtime-mode
sudo systemctl is-active k3s
sudo systemctl is-enabled k3s
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
sudo ss -lntp
```

No modo Compose, K3s deve estar `inactive` e `disabled`. No modo cluster,
deve estar `active` e `enabled`, e os containers das aplicações Compose parados.
PostgreSQL e MinIO devem estar rodando nos dois casos. `systemctl is-active`
e `is-enabled` retornam código diferente de zero para alguns desses estados
esperados; isso não significa, por si só, falha na alternância.

No modo cluster, acrescente:

```bash
sudo k3s kubectl get nodes
sudo k3s kubectl get pods,svc,pvc -A
```

O arquivo `/var/lib/apae/runtime-mode` registra o último modo concluído com
sucesso. Não é um reconciliador e não comprova o estado atual dos serviços.

## Concorrência e recuperação de falhas

A criação atômica de `/run/lock/apae-runtime-mode` impede duas trocas simultâneas
e coordena a renovação TLS. A operação libera sua própria trava ao terminar.
Uma execução que não conseguiu adquirir a trava não remove a trava existente.

Se uma etapa falhar, o playbook informa a tarefa e interrompe a sequência.
Não há reversão automática: o modo anterior pode já estar parado e o destino
parcialmente iniciado. O registro do último sucesso não é atualizado.

### Procedimento de recuperação

1. Preserve a saída original e identifique a primeira tarefa que falhou.
2. Consulte o estado real com os comandos acima. Confira também os dois
   containers de dados e seus volumes antes de retomar a operação.
3. Corrija a causa: arquivo ou imagem ausente, serviço de dados parado,
   conflito de porta, erro de certificado ou componente Kubernetes indisponível.
4. Reexecute o playbook completo do modo desejado. Não edite o registro de modo
   para declarar uma troca que não passou nas verificações.
5. Se precisar voltar aos produtos, execute `activate-compose.yml` completo;
   ele encerra os workloads do K3s antes de retomar as aplicações.

Para investigar as causas mais comuns:

```bash
sudo docker logs --tail 100 apae-geral-api
sudo docker logs --tail 100 apae-gestao-api
sudo docker logs --tail 100 apae-atendimento-api
sudo docker logs --tail 100 proxy-proxy-1
sudo journalctl -u k3s -n 100 --no-pager
sudo journalctl -u k3s-api-firewall -n 100 --no-pager
```

No cluster, use `kubectl describe` e `kubectl logs` no recurso que não concluiu
o rollout. Para falhas do certificado, siga o [procedimento TLS](runtime-tls.md).

### Trava deixada por uma execução interrompida

Antes de removê-la, confira se há playbook em outra máquina, serviço TLS ou
Certbot em andamento. A ausência de processo Ansible local na VPS não exclui
uma execução remota em andamento. Confirme com os demais administradores.

```bash
sudo systemctl status apae-compose-tls-renew.service --no-pager
sudo docker ps -a --filter name=apae-certbot-renew
sudo ls -ld /run/lock/apae-runtime-mode
```

Somente após confirmar que a trava está abandonada:

```bash
sudo rmdir /run/lock/apae-runtime-mode
```

Não use remoção recursiva nem cron para apagar travas. Se houver problema de
permissão ou dúvida sobre uma operação ativa, interrompa a recuperação.

### Serviços de dados e acesso administrativo

Não execute `docker compose down -v`, `docker volume prune`, desinstalação do
K3s ou restauração de backup como parte da alternância. Se um serviço de dados
falhar, trate sua recuperação separadamente, preservando o volume identificado
no inventário. A alternância não substitui o procedimento de backup da issue #108.

Os playbooks não alteram o SSH, seu usuário, chaves ou porta 22022. A retomada
do cluster utiliza a proteção administrativa provisionada pelas issues #90/#91.
Mantenha acesso ao console do provedor para recuperação de problemas do host.

## Comportamento após reiniciar a VPS

Não existe serviço de boot que leia `runtime-mode` e execute o playbook.
O comportamento resulta das configurações persistentes dos serviços:

| Última ativação concluída | Configuração gravada |
| --- | --- |
| Compose | K3s parado e desabilitado no systemd. |
| Cluster | K3s iniciado e habilitado no systemd. |
| Ambos | Timer TLS habilitado; volumes e registro do último modo preservados. |

A retomada dos containers Docker depende do Docker habilitado no boot e da
política `restart` efetiva de cada container. Os playbooks de alternância não
reconfiguram essas políticas. `unless-stopped` mantém parados os containers
que foram parados explicitamente; políticas como `always` podem fazê-los
retornar após reiniciar o daemon e devem ser avaliadas para evitar concorrência.

A trava fica em `/run` e não persiste ao reboot. O timer com `Persistent=true`
pode disparar uma verificação pendente; ainda exige modo Compose registrado e
K3s inativo. No modo cluster ele adia a renovação. Se o certificado vencer
durante um período longo no cluster, a ativação do Compose tenta renová-lo
antes de iniciar os sites.

Após um reboot, consulte o estado real e reexecute o playbook completo do modo
desejado para validar e normalizar a operação. Os testes registrados nesta
issue não incluem reboot físico da VPS; não se deve interpretar a configuração
dos serviços como evidência de um teste de reinicialização executado.

## Responsabilidades das próximas issues

Toda issue que alterar o cluster deve avaliar, no próprio PR:

- Atualização de `runtime_mode_cluster_workloads`, portas e dependências de
  inicialização quando um novo componente passar a ser obrigatório.
- Ajustes nas roles do host e nos manifests GitOps afetados, preservando a
  responsabilidade do ArgoCD pelos recursos Kubernetes e sua política de sync.
- Validação da ida ao cluster e do retorno ao Compose, com HTTPS e documentos
  acessíveis, registrando qualquer mudança no procedimento de recuperação.
- Manutenção de PostgreSQL e MinIO nos mesmos containers e volumes enquanto
  esta estratégia de coexistência estiver em uso.

### Acesso interno aos dados

Quando as aplicações Kubernetes forem implantadas, suas issues devem definir
o endpoint interno do PostgreSQL e do MinIO e validar a conectividade real dos
pods. O DNS `minio-shared` e outros aliases da rede Docker não são, por si só,
nomes resolvíveis pelo Kubernetes.

Não publicar PostgreSQL ou a API interna do MinIO indiscriminadamente em
`0.0.0.0`. A solução deve restringir a interface/endereço de destino, as origens
permitidas no firewall e, conforme o CNI e os manifests adotados, as políticas
de rede; deve incluir Secrets e credenciais com os acessos necessários.
Validar tanto a conexão autorizada quanto a recusa a origens não autorizadas.
Não montar o diretório de dados do PostgreSQL em uma segunda instância.

Essa conexão ainda não foi demonstrada pelos testes desta issue: os produtos
não estavam implantados no cluster. A definição e a validação devem acompanhar
as issues #92, #93 e as implantações dos respectivos produtos.

### Compatibilidade das migrations

O banco é compartilhado com as versões fixas do Compose. Antes de sincronizar
uma aplicação Kubernetes que execute migrations, verificar se essas versões
continuarão funcionando após a mudança. Não depender de rollback de imagem
para reverter uma alteração de schema.

O PR responsável pela migration deve registrar a análise de compatibilidade,
o backup aplicável e a validação do retorno ao Compose. Mudanças incompatíveis
ou experimentais devem usar banco separado, nunca o banco compartilhado desta
demonstração. Prefira mudanças aditivas e remova estruturas antigas apenas
quando nenhum consumidor depender delas.

### Issues relacionadas

- #90 e #91: provisionamento do K3s e bootstrap do ArgoCD.
- #92 e #93: Applications, overlays e Secrets dos produtos.
- #109: validação dos playbooks e roles.
- #111 e #112: Gateway, portas públicas e TLS do cluster.
- #108 e #117: backup, recuperação e contingência.
- #110: integração futura com execução protegida pelo GitHub Actions.

As referências completas estão no corpo da [issue #140](https://github.com/IFPBEsp/APAE-INFRA/issues/140).
