# 01 — Estratégia e armazenamento externo

[← Índice](README.md)

## Premissas e decisão proposta

Uma única VPS é um domínio de falha: perda do disco, indisponibilidade da conta ou comprometimento do host afetam cluster e volumes juntos. Manter dados originais, backup externo e, mediante aprovação, uma segunda cópia independente. A arquitetura inicial com R2 apenas não satisfaz três cópias em domínios independentes. Disponibilidade do bucket não significa recuperabilidade da aplicação.

Propor restic no host, agendado por timers systemd e configurado por Ansible. Isso permite proteger o datastore mesmo com a API Kubernetes indisponível. O job coordena dumps nativos e captura de arquivos consistentes; restic cuida de transporte, deduplicação e criptografia. Não adotar inicialmente Velero/CSI snapshots: não há driver de snapshots nem storage persistente homologados, e esses recursos não dispensam consistência de aplicações.

## Capacidades da HostGator

A [documentação oficial da VPS simples](https://suporte.hostgator.com.br/hc/pt-br/articles/45911662214419-Como-funciona-a-VPS-simples) atribui backups ao cliente e informa que a HostGator não os realiza. Documenta acesso root por SSH e uso do Portal para administração da conta. Consulta pública em 05/11/2026; não houve validação do contrato nem do Portal desta assinatura.

| Capacidade | Evidência e limite | Conduta de recuperação |
| --- | --- | --- |
| Backup do provedor | Não fornecido segundo a documentação pública | Manter cópias externas próprias |
| Snapshot de disco/VM | Disponibilidade, preço, consistência, retenção e exportação não confirmados | Não depender deste recurso para RPO/RTO |
| Restauração de snapshot | Fluxo, granularidade, prazo e alteração de IP não confirmados | Confirmar antes de usar; preservar backups independentes |
| Reinstalação/substituição da VPS | Operação pelo Portal/suporte prevista no levantamento #86; prazo contratual não confirmado | Assumir potencial perda de todo o disco; recuperar dados externos |
| Console fora de banda, rescue/ISO e recuperação sem SSH | Não confirmados para esta assinatura | Testar acesso alternativo ou prever nova VPS com suporte |
| Retenção de disco após falha/cancelamento | Não confirmada | Não contar com recuperação do disco original |
| OCI/API | Identificação OCI não comprova tenancy/IAM do cliente | Não presumir acesso ao provider Oracle nem automação de snapshots |

O responsável de infraestrutura deve obter um chamado com: recursos disponíveis nesta assinatura, procedimento em caso de perda de SSH/disco, horários e prazo de atendimento, reinstalação destrutiva, preservação do IP, exportação de snapshots e custo de substituição. Guardar protocolo, data e resposta em registro privado; publicar apenas conclusões sem credenciais. Até lá, o RTO permanece meta não homologada. Não foi aberto chamado nesta entrega.

## R2 Standard e a franquia gratuita

Conforme a [tabela oficial do R2](https://developers.cloudflare.com/r2/pricing/#free-tier), consultada em 05/11/2026:

| Item | Franquia mensal | Excedente Standard |
| --- | --- | --- |
| Armazenamento | 10 GB-mês | US$ 0,015/GB-mês |
| Operações classe A | 1 milhão | US$ 4,50/milhão |
| Operações classe B | 10 milhões | US$ 0,36/milhão |
| Saída para Internet | Sem cobrança de egress | Sem cobrança de egress |

A franquia é de Standard, não de Infrequent Access, e deve ser orçada considerando o consumo compartilhado da conta. GB-mês mede armazenamento ao longo do mês, não tamanho máximo de um arquivo. O excedente é faturável; não assumir bloqueio automático ao alcançar a franquia. A tabela prevê arredondamentos de unidades de cobrança. Estimativas abaixo são apenas de armazenamento, antes de operações, arredondamentos, tributos e câmbio:

| Média retida mensal | Parcela estimada de armazenamento |
| --- | --- |
| 8 GB | US$ 0 |
| 50 GB | US$ 0,60 |
| 100 GB | US$ 1,35 |

## Backblaze B2 e a franquia gratuita

Condições verificadas em 05/11/2026 nas páginas oficiais de [preços B2](https://www.backblaze.com/cloud-storage/pricing) e [operações da API](https://www.backblaze.com/cloud-storage/transaction-pricing):

| Item | Condição publicada |
| --- | --- |
| Armazenamento gratuito | Primeiros 10 GB da conta |
| Armazenamento excedente | Página comercial anuncia preço a partir de US$ 6,95/TB/mês; confirmar cotação aplicável à conta/região |
| Download | Gratuito até 3× o armazenamento médio mensal; depois US$ 0,01/GB |
| Permanência mínima | Sem cobrança por duração mínima ou tamanho mínimo de arquivo |
| Upload e operações A/B/C | Gratuitos na tabela consultada |
| Operações D | Têm tabela própria; conferir caso sejam usados eventos/notificações |

A página de operações ainda contém nota de armazenamento com valor diferente da página comercial. Para orçamento, usar a página comercial e confirmar a tarifa da conta antes da implantação. A franquia considera todo o histórico retido. Checks e testes de restauração também consomem download. Não interpretar armazenamento gratuito como recuperação ilimitada.

### Integração e uso proposto

Avaliar B2 como alternativa de destino primário ou como segunda cópia de R2, sem substituir a proposta principal antes da aprovação do time. Para restic, homologar o endpoint S3 compatível da região escolhida; a [documentação do restic](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html) descreve a configuração dos backends. Fixar versão e validar backup, check, retenção e restore na PoC.

Para uma segunda cópia, propor execução diária por executor externo confiável, com acesso de leitura ao R2 e escrita ao repositório B2 separado; a credencial B2 não fica na VPS. Copiar snapshots completos pela ferramenta homologada e verificar manifesto/ID no destino. Não usar espelhamento destrutivo nem propagar exclusões automaticamente. Definir retenção própria: uma diária por 7 dias, inicialmente, sujeita a dimensionamento e aprovação.

Meta proposta para perda do destino R2: ponto recuperável no B2 com no máximo 26h, considerando intervalo diário e até 2h de transferência/validação; RTO global de 8h sujeito ao teste. Essa segunda cópia não preserva automaticamente o RPO de 8h dos dados de negócio: para isso, aumentar sua frequência e medir a conclusão externa dentro da janela. Alertar ausência de cópia concluída antes de ultrapassar a meta aprovada.

Usar conta institucional com MFA, bucket privado, application key restrita ao bucket e senha de repositório sob custódia externa. Homologar permissões de listagem, leitura, escrita e exclusão necessárias ao restic. Avaliar retenção imutável separadamente em ambiente descartável, sem assumir compatibilidade com prune ou proteção contra exclusão só por usar outro fornecedor.

R2 e B2 podem permanecer gratuitos se cada cópia completa e seu histórico couberem nas respectivas franquias e demais limites. Dois destinos de 10 GB não equivalem a uma cópia redundante de 20 GB. Se o executor ou a conta de administração alcançar ambos com permissão de exclusão, permanece risco de comprometimento comum; separar identidades e credenciais.

## Comparação entre R2, B2 e GCP Coldline

| Aspecto | R2 Standard | Backblaze B2 | GCP Coldline |
| --- | --- | --- | --- |
| Uso proposto | Backups frequentes e recuperação operacional | Alternativa primária ou segunda cópia diária | Segunda cópia de baixa frequência |
| Gratuidade | 10 GB-mês e franquias de operações descritas acima | Primeiros 10 GB; limites de download descritos acima | Não presumir Coldline coberto por free tier ou créditos |
| Permanência mínima | Sem mínimo | Sem mínimo | 90 dias; remoção antecipada pode gerar cobrança |
| Recuperação | Sem taxa de retrieval Standard nem egress | Download gratuito até 3× a média armazenada; excedente cobrado | Retrieval e operações cobrados; transferência depende do destino |
| Acesso aos dados | Online | Online | Online, sem espera típica de recuperação de fita |
| Preço de armazenamento | Tabela acima | Tarifa comercial e confirmação da conta, conforme seção B2 | Depende da localização e da moeda |
| Retenção proposta | Política restic por componente | Segunda cópia: uma diária por 7 dias | Conjuntos independentes mantidos por 100 dias |

As características de Coldline constam em [classes de armazenamento](https://cloud.google.com/storage/docs/storage-classes) e [preços GCS](https://cloud.google.com/storage/pricing). Não selecionar região nem apresentar preço único antes de decidir localização, volume, frequência de leitura e destino da restauração. Orçar armazenamento, operações, retrieval, transferência, exclusão antecipada e cópias retidas por soft delete/versionamento, se habilitados. Coldline não é automaticamente mais barato no custo total.

Não colocar o repositório restic ativo em Coldline por simples lifecycle: verificações e prune leem/regravam dados, com potencial custo. Não aplicar expiração por idade aos objetos internos do restic; blocos antigos podem sustentar snapshots recentes. Expiração deve ser feita pela ferramenta de backup. Para Coldline, gerar mensalmente um conjunto completo autossuficiente e cifrado, com manifesto e checksums, a partir de um ponto consistente; testar restauração sem acesso ao repositório R2. A segunda conta não deve ser administrável pela credencial existente na VPS.

## Dimensionamento e decisão de entrada em produção

Sem dados de produção nesta etapa, adotar os cenários explícitos do [documento 06](06-validacao-e-dimensionamento.md) para a decisão inicial. Na #108, durante o piloto, medir por pelo menos 14 dias: tamanho protegido, tamanho comprimido, bytes novos por execução, objetos/requisições, tempo de upload/download, crescimento dos dumps e pico de staging. Não assumir deduplicação eficiente de dumps comprimidos ou dados já cifrados.

Estimativa conservadora: `volume retido ≈ cópia inicial + alterações retidas + dumps completos retidos + metadados + folga`. Para conjuntos sem deduplicação, somar cada versão mantida. Calcular a união das janelas de retenção; não simplesmente multiplicar dados vivos por um fator otimista.

Alertar a 70% e 90% da franquia e do orçamento mensal aprovado. Orçamento é aviso, não garantia de bloqueio de cobrança. Não apagar backups ou reduzir a retenção aprovada para permanecer gratuito. Se os dados ultrapassarem a franquia, aprovar pagamento ou revisar formalmente a arquitetura. A gratuidade não é requisito de integridade.

## Segurança do destino

Bucket privado, sem endpoint público, conta institucional com MFA e dois responsáveis. HTTPS com validação de certificados e criptografia no cliente; escolher localização após avaliação institucional de tratamento de dados. Usar nomes técnicos sem dados pessoais em buckets, tags e logs.

Os [tokens R2](https://developers.cloudflare.com/r2/api/tokens/) oferecem escopo por bucket. Não presumir que uma credencial de escrita seja append-only: validar exclusão e sobrescrita na PoC. Os [bucket locks](https://developers.cloudflare.com/r2/buckets/bucket-locks/) devem ser avaliados em bucket de teste separado; regras de retenção podem conflitar com locks temporários e prune do restic. Não afirmar proteção imutável antes de homologar permissões e política. A cópia independente é a mitigação proposta para comprometimento do host/conta primária.
