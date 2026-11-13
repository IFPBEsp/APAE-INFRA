# 06 — Validação documental e dimensionamento

[← Índice](README.md)

## Revisão de 06/11/2026

Revisão local e consulta às fontes oficiais; sem conexão à VPS, criação de buckets ou execução de backups. Não representa revisão do time ou aprovação operacional.

| Verificação | Resultado e evidência |
| --- | --- |
| Fronteira #107/#108 | Conferidos os textos das issues: #107 define e aprova a estratégia; #108 implanta e comprova recuperação |
| Backups HostGator | A documentação pública mantém a responsabilidade do cliente; snapshot, rescue e prazo da assinatura continuam sem confirmação |
| Método k3s | Conferido token obrigatório e distinção entre SQLite, embedded etcd e datastore externo |
| Dados das aplicações | Bases locais não definem PVC; README de APAE Geral deixa PostgreSQL/MinIO fora do escopo dos manifests; Comemorativo cita PostgreSQL e blob externos |
| RPO e agenda | Ajustada proposta de SQLite/configurações para 12h; captura diária sem margem não assegurava RPO de 24h |
| Identificador de backup | Separado manifesto de captura do recibo externo com ID restic, evitando autorreferência impossível |
| Retenção | Preservação intradiária deve usar política explícita; versões diárias não representam todas as capturas |
| Teste de recuperação | Plano inclui perda completa, Secrets, consistência de dados, falha/ausência de jobs e recuperação sem R2 |
| Capacidade gratuita | Estimada em 5 GB no cenário de referência com retenção curta; validação operacional futura na #108 |

Fontes reconsultadas: [issue #107](https://github.com/IFPBEsp/APAE-INFRA/issues/107), [issue #108](https://github.com/IFPBEsp/APAE-INFRA/issues/108), [HostGator](https://suporte.hostgator.com.br/hc/pt-br/articles/45911662214419-Como-funciona-a-VPS-simples), [backup k3s](https://docs.k3s.io/datastore/backup-restore), [restore restic](https://restic.readthedocs.io/en/stable/050_restore.html), [retenção restic](https://restic.readthedocs.io/en/stable/060_forget.html) e [preços R2](https://developers.cloudflare.com/r2/pricing/).

## Estimativa inicial sem dados de produção

O responsável confirmou em 06/11/2026 que ainda não há produção; existem apenas bancos de desenvolvimento. PDFs e anexos de produto são o perfil esperado. Portanto, o estudo pode concluir uma avaliação inicial por cenários, sem depender de medição de produção inexistente. Os números abaixo são hipóteses de planejamento, não medidas nem previsão de quantidade de usuários.

Proposta corrente: backups de negócio a cada 6h, preservando todas as capturas das últimas 48h e uma diária até completar 7 dias; plataforma com uma versão diária por 7 dias. Sem retenção semanal/mensal no R2 inicial. Para cálculo conservador, reservar até 15 dumps por banco (`8 intradiários + 7 diários`, sem descontar sobreposição), além da captura em andamento coberta pela folga. A seleção efetiva deve ser homologada por tempo na #108. Dumps são orçados sem benefício de deduplicação.

Os 10 GB-mês são armazenamento ao longo do mês, não novos uploads com liberação de espaço na virada. A franquia deve considerar outros buckets da conta.

| Parcela retida, em GB decimais | Pequeno | Referência inicial | Crescimento |
| --- | --- | --- | --- |
| Soma dos dumps por captura | 0,025 | 0,100 | 0,250 |
| Até 15 dumps retidos | 0,375 | 1,500 | 3,750 |
| Arquivos atuais | 0,500 | 2,000 | 4,000 |
| Arquivos antigos/alterações ainda retidos | 0,100 | 0,500 | 1,000 |
| Datastore e configurações, todas as versões retidas | 0,300 | 0,700 | 1,000 |
| Metadados e resíduos operacionais previstos | 0,200 | 0,300 | 0,500 |
| **Total retido estimado** | **1,475** | **5,000** | **10,250** |

O cenário de referência reserva 100 MB para a soma de todos os dumps por captura, 2 GB para arquivos atuais (por exemplo, 1.000 documentos de 2 MB) e 500 MB para conteúdo antigo/alterado. Esses exemplos não impõem tamanho por arquivo nem quotas aos produtos. A hipótese de plataforma de 700 MB inclui suas versões retidas, não apenas um snapshot. Validar cada parcela posteriormente; bancos maiores podem dominar o consumo.

**Conclusão do estudo: os 10 GB são suficientes no cenário de referência proposto, com consumo estimado de 5 GB, mas não em todos os cenários.** Isso justifica planejar o início gratuito; não garante sua duração. O limite de 50 MB por upload é teto técnico, não tamanho médio. Ver [levantamento das aplicações](07-limites-de-upload-das-aplicacoes.md).

Arquivos iguais podem ser deduplicados pelo restic; o cálculo considera o conteúdo atual e versões alteradas ainda referenciadas. Não multiplicar todos os PDFs pelo número de dumps, nem assumir compressão adicional de JPEG/PDF. As três parcelas de arquivos, dumps e plataforma são distintas, evitando dupla contagem.

## Condições para manter o cenário gratuito

- Meta de planejamento de até 7 GB retidos, reservando margem até os 10 GB para variação, captura nova e manutenção; o espaço temporário real também precisa caber.
- Conta dedicada ou inclusão do consumo de outros buckets no cálculo; dados ativos e backups na mesma conta compartilham a franquia.
- Limpeza por restic após novo conjunto completo confirmado; não apagar objetos internos por lifecycle. Falha de integridade/backup suspende limpeza e exige resposta.
- Alertas a 7 GB e 9 GB e acompanhamento de operações, conforme a franquia do provedor. Quantificar requisições na implementação; a estimativa de bytes não garante gratuidade de todas as operações.
- Ao projetar ultrapassagem da capacidade, aprovar excedente, migrar ou rever formalmente a política antes de perder backups. Não descartar a última cópia útil para caber no gratuito.
- Aceitar explicitamente a perda da possibilidade de recuperar pontos com mais de 7 dias; a segunda cópia B2 diária com a mesma janela não resolve corrupção descoberta após essa janela.

## Ficha mínima de inventário e estimativa

Preencher uma ficha por produto/ambiente em registro privado. Este modelo não solicita senhas, tokens, dados pessoais ou conteúdo dos bancos.

| Campo | Valor a confirmar |
| --- | --- |
| Produto/ambiente e titular/suplente | Pendente |
| Situação | Ainda não implantado / teste / produção |
| Banco | Motor, versão, localização e tamanho lógico |
| Dump | Tamanho após compressão e tempo de captura |
| Arquivos | Tamanho, crescimento diário e localização/PVC/provedor |
| Consistência | Relação banco/arquivos e mecanismo de pausa |
| Datastore k3s | Tipo, versão, tamanho e configuração de data-dir |
| Volume externo retido previsto | Dumps + arquivos + cluster + metadados + folga |
| Crescimento | Projeção para 30 e 90 dias |
| Custos | Armazenamento, operações, leitura/checks, transferência e executor externo |
| Evidência | Data, método e responsável pela medição/estimativa |

Nesta etapa, preencher apenas o que já estiver definido e usar os cenários acima para valores desconhecidos. O piloto de 14 dias e a medição física da retenção ficam na #108; revisar a estimativa após a primeira semana de uso representativo e mensalmente. A ausência de medições atuais não impede a decisão inicial por estimativa.

## Próxima decisão necessária

Consolidar as fichas e respostas do provedor, escolher destino e segunda cópia, orçamento e pessoas responsáveis. Registrar aprovação da política no documento 05. Até isso ocorrer, a validação documental está registrada e a validação organizacional permanece pendente; implantação e ensaio não foram antecipados.
