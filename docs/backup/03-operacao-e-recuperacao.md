# 03 — Operação e recuperação

[← Índice](README.md)

## Credenciais e custódia

Separar acesso administrativo do bucket, execução de backup e leitura para restauração. No R2, limitar tokens aos buckets necessários e homologar as permissões reais; não prometer isolamento de exclusão por separação nominal de usuários. Se a credencial do job permitir apagar objetos, registrar esse risco e mitigá-lo com cópia independente sob outra administração. Não armazenar credenciais administrativas ou da segunda cópia na VPS.

Restic cifra dados no cliente e requer a senha do repositório para recuperação. Manter senha, credenciais de recuperação e token k3s em cofre institucional fora da VPS, acessível por titular e suplente com MFA. Testar acesso sem cluster, GitHub Actions ou identidade pessoal do titular. Não guardar a única senha dentro do próprio backup que ela desbloqueia. Ver [preparação de repositório restic](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html).

Na VPS, arquivos de senha/credenciais somente para o usuário executor, permissões `0600`, diretórios `0700`, sem valores em Git, logs ou argumentos da linha de comando. Cifrar staging em disco ou usar volume cifrado e janela curta de retenção; evitar dumps sensíveis persistentes fora dessa área. Não usar `set -x`. A criptografia do backup não protege dados em um host já comprometido.

A #93 deve acrescentar ao kit de recuperação: chave privada age/SOPS, chaves privadas do Sealed Secrets ou identidade e dados do cofre externo, conforme a decisão real. Preservar chaves antigas enquanto houver backups dependentes, inclusive token k3s após rotação. Trocar senha restic não invalida cópias de chaves já roubadas: incidente com exposição exige avaliar novo repositório e rotação das credenciais das aplicações.

## Pipeline de backup proposto

1. Obter lock exclusivo por conjunto e adquirir a mesma trava da alternância Compose/k3s (`/run/lock/apae-runtime-mode`, criação atômica de diretório, conforme #140 / PR #145), também usada pela renovação TLS. Verificar espaço livre, relógio, conectividade, versões e acesso às fontes. Serializar backup, alternância, manutenção e upgrades; não usar um lock independente para coordenar o k3s. Se a trava estiver ocupada, aguardar ou falhar com alerta, sem removê-la.
2. Criar staging fora dos diretórios de origem; validar capacidade para dumps e folga operacional. Não preencher disco do datastore com staging.
3. Aplicar quiescência do produto conforme matriz, com timeout e liberação garantida em rotina de saída. Sob a trava compartilhada, registrar os estados reais de atividade e habilitação do k3s antes de qualquer alteração. Para capturar o SQLite, parar o serviço somente se estiver ativo e confirmar que está parado. Prever rotina de saída e mecanismo independente para restaurar os estados anteriores mesmo em falha, timeout ou encerramento do job. No modo Compose, manter k3s parado e desabilitado; não iniciá-lo nem habilitá-lo ao finalizar o backup.
4. Capturar todos os componentes, validar códigos de saída e checksums, escrever manifesto de captura. Falha em dump não pode ser mascarada pelo sucesso do upload de um arquivo parcial.
5. Liberar a quiescência e restaurar os estados anteriores do k3s assim que a captura consistente terminar; se estava ativo, retomá-lo e validar sua saúde; se estava parado/desabilitado, preservar esses estados. Só então liberar a trava da alternância adquirida pelo job. Falha na retomada deve gerar alerta e não pode ser declarada sucesso. Enviar staging estável via restic para R2, sem prolongar a pausa para transmissão.
6. Exigir saída bem-sucedida de todas as etapas e confirmação do snapshot remoto por ID. Registrar esse ID em um recibo externo separado, ligado ao identificador do conjunto: o manifesto dentro de um snapshot não pode conter o próprio ID ainda não criado. Saída não zero, inclusive arquivos ilegíveis no restic, indica falha do conjunto. Ver [backup restic](https://restic.readthedocs.io/en/stable/040_backup.html).
7. Enviar ao monitor externo horário do ponto consistente, conclusão, conjunto, ID e resultado sem dados sensíveis. Limpar staging após confirmação; falhas preservam material apenas em janela controlada e com alerta de disco.
8. Manter no máximo duas capturas locais de contingência, se houver capacidade. Elas não contam como cópia externa nem substituem retenção remota.

Modelo de validação/restauração do repositório, com ambiente e arquivos de credenciais previamente preparados pelo operador:

```bash
# Somente no host isolado de recuperação; não imprime segredos.
export RESTIC_REPOSITORY='s3:https://<ACCOUNT_ID>.r2.cloudflarestorage.com/<BUCKET>/<PREFIXO>'
export RESTIC_PASSWORD_FILE='/run/credentials/restic-password'
# Injetar AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY pelo mecanismo seguro homologado.
restic snapshots
restic check
# Substituir o ID pelo snapshot do conjunto escolhido, nunca escolher latest sem análise.
restic restore '<SNAPSHOT_ID>' --target /srv/restore-isolado
```

Fixar versão/checksum do restic e testar endpoint S3 na #108. Não executar `init` em bucket existente durante recuperação. Procedimento detalhado de consulta e verificação em [repositórios restic](https://restic.readthedocs.io/en/stable/045_working_with_repos.html).

## Retenção e integridade

Executar seleção de retenção em dry-run antes de aplicar. `forget` remove referências e `prune` libera dados não referenciados; reservar janela separada dos backups e executar `check` após manutenção. A política deve preservar as capturas intradiárias e os conjuntos completos da matriz. Não usar lifecycle para expirar blocos restic. Ver [retenção restic](https://restic.readthedocs.io/en/stable/060_forget.html).

Propor check de metadados semanal e após prune; leitura de dados por amostragem semanal, cobrindo todo o repositório a cada mês, ou `check --read-data` mensal se o volume permitir. Medir tempo e custo. Check não substitui restauração funcional. Não apagar última cópia comprovadamente restaurável enquanto falhas de integridade estiverem em investigação. Suspender prune durante incidente.

## Detecção e resposta a falhas

O agendador roda no host, mas o detector de ausência de backup deve rodar fora da VPS/cluster. Na #108, selecionar serviço de heartbeat externo ou verificador independente que consulte os snapshots, com acesso somente de leitura e sem depender do Prometheus da VPS. Heartbeat sozinho não prova integridade: cruzar com ID/manifesto e restauração periódica.

| Condição | Regra proposta | Resposta |
| --- | --- | --- |
| Falha de qualquer etapa | Imediata | Avisar titular e suplente; retentar até duas vezes com intervalo de 15 min, sem concorrência |
| Backup de negócio atrasado | Sem conjunto completo por 7h; crítico ao atingir 8h | Investigar antes de violar RPO; declarar violação quando ocorrer |
| Datastore/configuração atrasados | Aviso a 14h; crítico a 24h | Verificar host, timer e destino externo |
| Job não finaliza | Limite inicial de 2h para conjunto de negócio | Alertar, investigar; não encerrar captura deixando aplicação parada |
| Falha de check ou restauração | Imediata | Preservar cópias anteriores e suspender prune |
| Capacidade/custo | 70% e 90% do limite aprovado; staging/disco com menos de 20% livre | Planejar capacidade e evitar falha por disco cheio |

Usar e-mail institucional do grupo de infraestrutura como canal primário e canal institucional alternativo a definir; testar ambos antes da produção. Proposta de atendimento: confirmação em até 1h, suplente acionado após 30 min sem confirmação e coordenação após 1h. Sem escala/cobertura aprovada, essa meta não está garantida. Alertas precisam incluir último ponto recuperável, erro sanitizado e responsável; nunca dumps ou credenciais.

## Sequência de recuperação de desastre

1. **Declarar e conter:** registrar início da interrupção, escopo, responsáveis e último ponto íntegro. Isolar host suspeito e impedir novas escritas, jobs, sincronização e prune. Preservar evidências; não sobrescrever o único disco recuperável.
2. **Escolher conjunto:** usar manifesto e ID explícito anterior à falha/corrupção. Confirmar banco, arquivos, chaves e versões compatíveis. Corrupção pode estar nos backups recentes; retenção determina o alcance de recuperação.
3. **Recuperar acesso independente:** acessar cofre, R2, Git, registry, DNS e Portal/suporte a partir de estação confiável. Obter token k3s, chaves #93 e senha restic. Se credenciais foram expostas, planejar substituição antes da reabertura.
4. **Reconstruir infraestrutura:** obter VPS nova ou reinstalada, registrar novo IP/fingerprint e aplicar Ansible no commit homologado. Configurar SO suportado, disco, SSH, firewall, rede e versões fixadas. Não pressupor que Terraform recrie a VPS HostGator; recuperar state conforme #87 apenas se necessário a recursos externos.
5. **Escolher caminho do cluster:** restaurar datastore para preservar estado, ou criar cluster limpo e reconstruir recursos por GitOps. Não combinar datastore antigo com cluster novo já em uso. No caminho limpo, Secrets e dados persistentes continuam exigindo restauração própria.
6. **Restaurar k3s, quando aplicável:** instalar a mesma versão do conjunto recuperado (versão inicial definida na #90: `v1.36.5+k3s1`), sem permitir reconciliação pública. Com o serviço parado e sob a trava da alternância, restaurar o diretório SQLite completo `server/db/`, token e configuração correspondentes, com permissões corretas, conforme o [procedimento de recuperação do k3s](https://github.com/IFPBEsp/APAE-INFRA/blob/f534bc267dab69f4ccd972a2f6b4ec2439422b16/ansible/docs/k3s-backup-restore.md). Iniciar e validar o cluster apenas se o modo de recuperação escolhido for cluster; no modo Compose, manter k3s parado e desabilitado. Embedded etcd e datastore externo não se aplicam à configuração atual; eventual migração exige revisão e homologação do procedimento na #108.
7. **Controlar reconciliação:** manter saída pública e escrita de workloads bloqueadas mesmo se o datastore restaurado recriar controllers automaticamente. Suspender auto-sync/prune, jobs, CronJobs e workers antes de liberar dependências. Garantir acesso de rede seguro ao repositório sem permitir notificações/pagamentos reais.
8. **Recuperar plataforma:** Ansible instala ArgoCD e bootstrap conforme #91; restaurar fontes de Secrets, CRDs/controllers, StorageClasses e volumes. Em cluster limpo, mapear novos PVs/caminhos; em restauração do datastore, verificar afinidade ao nó antigo e referências de PVC. ArgoCD não restaura conteúdo de PV.
9. **Restaurar dados:** criar banco vazio compatível, restaurar roles/grants, extensões e dumps com validação de erros. Restaurar arquivos do mesmo conjunto, metadados e permissões. Recuperar objetos externos e ajustar endpoints privados. Impedir migrations automáticas até validar schema/imagem; um commit novo pode alterar dados restaurados de forma irreversível.
10. **Validar e reabrir:** comparar checksums/contagens, testar autenticação e fluxos de negócio de cada produto, relação banco/anexo e TLS. Time de produto aceita o ponto recuperado e a perda medida. Ajustar DNS/IP e certificados, liberar tráfego e workers gradualmente, monitorar erros.
11. **Encerrar:** executar novo backup externo, verificar monitoramento e acesso dos suplentes, registrar RPO/RTO observados, custos e correções. Só desativar ambiente antigo após autorização de encerramento do incidente.

Para exclusão pontual, restaurar em área isolada e importar apenas registros/arquivos aprovados pelo squad; não reverter todo o cluster como primeira ação. Para comprometimento, recuperar em host confiável com novas credenciais e analisar a data de intrusão antes de selecionar backup.
