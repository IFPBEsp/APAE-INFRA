# 02 — Matriz de proteção

[← Índice](README.md)

## Evidências e inventário obrigatório

Levantamento local em 05/11/2026, sem acesso à produção. Os manifests em `kubernetes/` contêm configurações e volumes `emptyDir`, mas não definem PVCs nem comprovam a topologia dos bancos. `emptyDir` é efêmero: não deve conter o único exemplar de uploads ou dados de negócio. O [Site Comemorativo](../../kubernetes/site-comemorativo/README.md) cita PostgreSQL externo e `BLOB_READ_WRITE_TOKEN`; a [issue #93](https://github.com/IFPBEsp/APAE-INFRA/issues/93) cita credenciais de banco e S3/MinIO. Isso indica dependências a investigar, sem comprovar fornecedores ou implantação.

Preencher um inventário privado para cada aplicação: namespace e ambiente, responsável titular e suplente, motor/versão/extensões de banco, localização e fornecedor, tamanho e crescimento, PVC/PV/StorageClass/caminho real, UID/GID, uploads locais e externos, vínculos entre banco e arquivos, endpoints e referências de credenciais. Registrar como chegar a cada backup e suas chaves sem depender da VPS. Não registrar valores de Secrets nesta documentação pública.

| Produto | Evidência no repositório | Confirmação necessária pelo squad |
| --- | --- | --- |
| APAE Geral | Bases `apae-geral` e referências a Secrets | Motor/localização do banco, anexos, integrações e credenciais |
| APAE Atendimento | Bases `apae-atendimento` | Dados de atendimento, banco, arquivos e retenção institucional |
| Gestão Escolar | Bases `gestao-escolar`; configuração Flyway | Motor, schema, política de migrations e documentos |
| Site Comemorativo | README cita PostgreSQL e token de blob | Provedor de PostgreSQL/blob, exportação e restauração |
| PostgreSQL compartilhado | Container `apae-postgres`, volume `apae_postgres_data`, fora do k3s nos dois modos | Mapear bancos por produto, versão, roles/grants e acesso para dumps nativos; confirmar tamanho e crescimento |
| MinIO compartilhado | Container `apae-minio-shared`, volume `apae-minio-shared_minio-shared-data`, fora do k3s nos dois modos | Mapear buckets/objetos por produto, metadados, versões e vínculo com o banco para captura coordenada |

Os serviços compartilhados constam no [inventário da alternância Compose/k3s](https://github.com/IFPBEsp/APAE-INFRA/blob/1b4323a30d1b98420e4fe4f49e7dfed8ee90c300/ansible/docs/runtime-mode.md) da #140 (PR #145) e são as origens conhecidas dos dumps PostgreSQL e dos objetos MinIO. Permanecem ativos nos dois modos e exigem backup próprio; a cópia do datastore k3s não protege esses volumes. Confirmar o mapeamento de cada produto sem substituir o inventário de dependências externas.

A [investigação dos repositórios em 06/11/2026](07-limites-de-upload-das-aplicacoes.md) confirma limites distintos por produto e referências a PostgreSQL, MinIO, S3 e Vercel Blob. Essas evidências refinam o inventário inicial acima, sem comprovar fornecedor ou volume em produção.

## Política proposta para aprovação

O responsável informou em 06/11/2026 que ainda não há produção e os bancos são de desenvolvimento. A capacidade inicial será estimada por cenários; medir produção não é pré-requisito para concluir o estudo. A proposta corrente passa a usar janela de 7 dias, substituindo as retenções semanais/mensais anteriores no destino primário. Ver [estimativa inicial](06-validacao-e-dimensionamento.md).

RPO é a perda máxima tolerada, medida até o ponto consistente recuperável **externo**, não até o início de um job local. RTO é contado desde a interrupção do serviço até a validação funcional e liberação; inclui detecção, suporte, preparação e transferência. São metas propostas, não garantias de SLA. Os RTOs por componente se sobrepõem: não representam promessa de restaurar toda a plataforma somando tempos ideais.

A versão e o datastore foram definidos na #90 (PR #118): k3s `v1.36.5+k3s1` com SQLite embarcado. Seguir o [procedimento de backup e recuperação do k3s](https://github.com/IFPBEsp/APAE-INFRA/blob/f534bc267dab69f4ccd972a2f6b4ec2439422b16/ansible/docs/k3s-backup-restore.md); os ramos etcd e datastore externo estão marcados como não aplicáveis.

Todas as horas abaixo usam `America/Recife`. A implementação deve declarar timezone explicitamente, sem herdar o fuso do host.

| Componente | Método e material indispensável | Frequência proposta | Retenção externa proposta | RPO / RTO alvo | Responsável por função |
| --- | --- | --- | --- | --- | --- |
| k3s `v1.36.5+k3s1` com SQLite embarcado (#90 / PR #118) | Sob a trava da alternância, registrar estado ativo/habilitado; com k3s parado, copiar `server/db/`, token e configuração; restaurar estado anterior mesmo em falha de captura | 01h/13h e antes/depois de mudanças críticas | Uma diária por 7 dias | 24h / 4h após host acessível | Infra |
| k3s com embedded etcd | Não aplicável à configuração atual (SQLite); exige revisão da estratégia se houver migração | Não aplicável | Não aplicável | Não aplicável | Infra |
| Datastore externo do k3s | Não aplicável à configuração atual (SQLite); exige revisão da estratégia se houver migração | Não aplicável | Não aplicável | Não aplicável | Infra e responsável do banco |
| Bancos de negócio, locais ou externos | Dump nativo consistente, roles/grants, versões/extensões e schema; origem conhecida: `apae-postgres` (`apae_postgres_data`) | Cada 6h: 00h, 06h, 12h, 18h | Todas as capturas das últimas 48h e uma diária até completar 7 dias | 8h / 8h no incidente completo | Squad e operador Infra |
| Uploads, anexos, PVCs com arquivos | Captura coordenada com banco; manifesto, checksums, UID/GID e mapeamento dos volumes | Junto do banco, cada 6h | Mesmas janelas do banco relacionado | 8h / 8h no incidente completo | Squad e operador Infra |
| Objetos MinIO e externos, se presentes | Exportação consistente por API, incluindo metadados e versões exigidos; origem conhecida: `apae-minio-shared` (`apae-minio-shared_minio-shared-data`); não apenas espelhamento de exclusões | Cada 6h, coordenado com referências no banco | Mesmas janelas dos dados relacionados | 8h / 8h no incidente completo | Squad |
| Secrets e chaves de recuperação | Cópia cifrada independente do cluster; fontes de Secrets e chaves do mecanismo escolhido na #93 | A cada criação/rotação, antes de ativar a nova chave | Toda chave necessária a backups ainda retidos | Nenhuma chave ativa sem cópia / 2h | Custodiantes de Secrets |
| Configuração do host e bootstrap | Git + cópia cifrada das exceções: configuração k3s, units/env, parâmetros de rede e versões; inventário de restauração | A cada alteração e às 01h/13h | Uma diária por 7 dias | 24h para exceções / 4h após host acessível | Infra |
| ArgoCD, manifests, Gateway e TLS | Git por commit; recuperar fontes de Secrets, credenciais de repositório, ACME/TLS quando não reemitíveis | A cada mudança; exceções diariamente | Histórico Git e política de configurações | Último commit acessível / incluso no RTO de 8h | Infra |
| Configuração Grafana/alertas e dados operacionais essenciais | Dashboards/regras em Git; exportar o que só existe no runtime | 01h/13h para exceções | Uma diária por 7 dias | 24h / 24h | Observabilidade |
| Logs/métricas históricos | Reconstruíveis por padrão; retenção e exportação se exigidos para auditoria | A definir se obrigatórios | Aprovação institucional | Sem meta até classificar | Observabilidade e gestor dos dados |
| State Terraform | Procedimento da #87, fora destes buckets/retenções | Conforme #87 | Conforme #87 | Conforme #87 | Responsável Terraform |

A janela de 6h reserva até 2h para concluir upload/validação dentro do RPO de 8h. Qualquer execução acima de 2h exige revisão de frequência ou metas. Para datastore e configurações a cada 12h, reservar até 2h para conclusão externa, produzindo idade máxima nominal de 14h em operação saudável, abaixo da meta de 24h. Serializar as capturas que coincidirem e contar a espera nessa duração. A retenção diária desses componentes mantém uma versão por dia, sem prometer preservar todas as capturas de 12h. Uma falha de execução pode violar RPO; o alerta não elimina a perda potencial.

Meta global inicial: recuperar serviços prioritários em até 8h, demais serviços em até 24h. A prioridade entre Atendimento, Gestão Escolar, Geral e Comemorativo deve ser aprovada pelo gestor, sem inferi-la pelo nome. Se disponibilidade de nova VPS, tamanho dos dados ou banda inviabilizarem as metas, revisar antes da produção. RPO menor exige nova proposta, por exemplo WAL/PITR para PostgreSQL ou binlogs para MySQL; dumps não permitem recuperação de qualquer instante.

## Como obter consistência

- PostgreSQL: `pg_dump` em formato custom por banco e `pg_dumpall --globals-only` para objetos globais, protegendo também informações sensíveis desses arquivos. Registrar extensões e usar clientes compatíveis. Dumps separados não garantem ponto global entre múltiplos bancos; coordenar aplicações quando houver dependências. [Documentação PostgreSQL](https://www.postgresql.org/docs/current/backup-dump.html).
- MySQL, somente se identificado: dump com `--single-transaction --routines --events --triggers`, validando engines, privilégios e versão. Bloquear DDL durante captura; tabelas não transacionais exigem bloqueio/parada ou ferramenta específica. Para MariaDB, selecionar a ferramenta/documentação da versão efetiva, sem assumir compatibilidade. [Documentação MySQL](https://dev.mysql.com/doc/refman/8.4/en/mysqldump.html).
- Arquivos e banco: bloquear novas escritas no produto, drenar filas e tarefas em andamento, capturar banco e arquivos no mesmo conjunto, então liberar escritas. Se houver mecanismo de snapshot consistente homologado, poderá encurtar a pausa. Cópia livre de arquivos mutáveis não é backup consistente.
- Datastore k3s: usar o método SQLite da matriz, preservando o diretório completo `server/db/`, inclusive arquivos WAL necessários à consistência, com o serviço parado. SQLite não usa `etcd-snapshot`. O backup do datastore protege estado Kubernetes, não os bytes dos PVs nem os volumes Docker compartilhados. O token correspondente é indispensável e deve ser recuperável fora do cluster. [Backup k3s](https://docs.k3s.io/datastore/backup-restore).

## Manifesto por conjunto

Gerar identificador único, ambiente, início/fim e ponto consistente em UTC, fuso do agendamento, componentes esperados e capturados, versões de SO/k3s/bancos/ferramentas, commit Git, digests das imagens, método de quiescência, checksums, tamanhos e referência de custódia das chaves. Após envio, registrar o ID do snapshot restic em recibo externo associado ao identificador do conjunto. Nunca incluir valores de credenciais em manifesto público. Um manifesto só recebe estado `completo` se todos os componentes obrigatórios estiverem confirmados no destino.

Manter conjuntos íntegros de banco e arquivos. Separar repositórios ou políticas por ambiente/componente para não eliminar dependências. A retenção de negócio é a união de todas as capturas das últimas 48h com uma diária até completar 7 dias; o dimensionamento reserva até 15 dumps por banco, sem descontar a sobreposição. A plataforma mantém uma diária por 7 dias. Implementar a janela intradiária por tempo explícito; `--keep-daily` sozinho não preserva todas as capturas das últimas 48h.

A janela de 7 dias limita a recuperação de exclusões/corrupções percebidas tardiamente. Não eliminar chaves ainda necessárias nem versões excepcionalmente preservadas durante incidentes. A rotina deve aplicar a janela por tempo real, sem permitir que a ausência de novos backups elimine a última cópia íntegra; falhas suspendem limpeza e geram alerta.
