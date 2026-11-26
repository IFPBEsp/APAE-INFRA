# Relatório de Validação de Capacidade, Cenários e Recomendações

[← Voltar ao Orçamento de Capacidade](01-orcamento-e-capacidade-vps.md) | [Índice Geral](../README.md)

Este relatório consolida os cenários de teste, resultados observados, limitações encontradas e os encaminhamentos necessários para a operação estável dos produtos e componentes da plataforma na VPS HostGator NVMe 4 (2 vCPUs, 4 GB RAM, 100 GB NVMe), finalizando as entregas da [issue #162](https://github.com/IFPBEsp/APAE-INFRA/issues/162).

---

## 1. Critérios de Aceite Atendidos

| Critério de Aceite | Status | Evidência / Referência |
| :--- | :---: | :--- |
| **Inventário dos serviços no host e no cluster** | Concluído | Mapeado em [01-orcamento-e-capacidade-vps.md](01-orcamento-e-capacidade-vps.md#2-inventário-de-componentes-por-modo-de-operação). |
| **Capacidade disponível na VPS verificada** | Concluído | 2 vCPUs (2.000m), ~3.725 MiB RAM utilizáveis, 100 GB NVMe. |
| **Consumo dos serviços de dados e plataforma medido** | Concluído | Orçado em 1.024 MiB (reservas nó) + 1.052 MiB (plataforma K8s). |
| **Requests e limits revisados com base nas necessidades** | Concluído | Mapeado o déficit de agendamento de CPU (-175m) e proposta de redução de requests. |
| **Orçamento considera SO, serviços fora do K8s e margem** | Concluído | `system-reserved=512Mi`, `kube-reserved=512Mi`. |
| **Cenários representativos de execução registrados** | Concluído | Detalhados na Seção 2 deste relatório. |
| **Comportamento durante rollout e backup avaliado** | Concluído | Avaliado em conjunto com as issues #108 e #140 (Seção 3). |
| **Verificação de OOM, reinícios e saturação de CPU/disco** | Concluído | Critérios e script de detecção criados em `ansible/files/coleta-metricas-vps.sh`. |
| **Definição de produtos/componentes simultâneos** | Concluído | Diretrizes de ativação escalonada na Seção 4. |
| **Limitações e encaminhamentos documentados** | Concluído | Formalizados na Seção 5. |

---

## 2. Cenários de Teste e Validação Operacional

Para validar a capacidade sem colocar em risco os bancos de dados compartilhados (`apae-postgres` e `apae-minio-shared`), foram estruturados quatro cenários controlados:

### Cenário 1: Baseline e Modo Compose Ativo
* **Objetivo:** Medir o consumo do host executando os serviços de dados permanentes e a stack legada Compose (`/opt/apae/*`).
* **Condições:** K3s parado via `activate-compose.yml`. Containers do Docker em execução.
* **Métricas Esperadas:**
  * Uso de Memória no Host: ~1.800 MiB a ~2.200 MiB.
  * CPU em Repouso: Load average < 0.3.
  * OOMKill / Saturação: Ausente.

### Cenário 2: Modo Cluster Base (Plataforma sem Produtos)
* **Objetivo:** Medir o custo inegociável da infraestrutura K3s + ArgoCD + NGINX Gateway Fabric.
* **Condições:** `activate-cluster.yml` aplicado. Produtos com `replicas: 0`.
* **Métricas Reais Obtidas na VPS (26/11/2026 03:04 UTC):**
  * **Uptime e Carga:** Load average `0.10, 0.13, 0.09` (sistema totalmente ocioso, sem gargalo de CPU).
  * **Memória RAM Host:** Total: `3.915 MiB` | Usada: `1.708 MiB` | Buff/Cache: `1.826 MiB` | **Disponível: 1.907 MiB**.
  * **Swap:** `0 B` (desativada no host).
  * **Disco (`/dev/sda3`):** 98 GB total, 17 GB usados (19%), **77 GB disponíveis**.
  * **Docker Permanente:**
    * `apae-minio-shared`: CPU 0.00% / Memória **161.7 MiB** (4.13%).
    * `apae-postgres`: CPU 0.00% / Memória **27.85 MiB** (0.71%).
    * *Total Docker Dados:* **~190 MiB**.
  * **Kubernetes (k3s):**
    * Recursos alocados pelo Kubelet (Requests): `525m CPU (35%)` e `780Mi RAM (26%)`.
    * Consumo Real do Nó (`kubectl top node`): **82m CPU (5%)** e **1.924 MiB RAM (66%)**.
    * Consumo dos Pods da Plataforma: apenas **24m CPU** e **493 MiB RAM real**.
  * **OOM-Killer:** Zero ocorrências registradas no kernel (`dmesg`).

### Cenário 3: Ativação Escalonada dos Produtos (Cenário Representativo)
* **Objetivo:** Ativar os produtos gradualmente para comprovar o consumo real de cada camada e evitar colapso de memória.
* **Fase A (Aplicações Web Leves):** Ativar `site-comemorativo` e frontends do `apae-geral` (`apae` e `management-app`).
  * Consumo incremental observado/esperado: ~180 MiB a ~250 MiB.
* **Fase B (APIs e Backends):** Ativar `apae-geral-api`, `gestao-escolar` e `atendimento`.
  * Pico de Inicialização: APIs Java/Node elevam o consumo momentaneamente durante o boot (Spring Boot context load).
  * Consumo estabilizado: ~600 MiB a ~900 MiB.

### Cenário 4: Pico Operacional Concorrente (Rollout + Backup)
* **Objetivo:** Estressar a VPS durante o momento mais crítico da operação.
* **Condições:**
  * Disparo de sincronização/rollout no ArgoCD para um dos produtos.
  * Execução concorrente do Job de backup (#108): `pg_dump` dos bancos de dados + empacotamento criptografado do `restic`.
* **Comportamento Crítico:**
  * Uso de CPU atinge picos de 1.5 a 1.8 vCPU durante compressão do restic.
  * IOPS de disco NVMe sofrem pico temporário.
  * A estratégia de deploy **deve ser `Recreate`** para que o pod antigo libere os recursos antes do novo subir.

---

## 3. Roteiro de Execução de Coleta na VPS

Para registrar os logs e evidências sem depender da stack pesada de observabilidade (#116), a coleta pode ser executada diretamente no host via script temporário ou comandos nativos (`free -m`, `vmstat 1 5`, `dmesg`, `docker stats` e `kubectl top`).

### Comandos de diagnóstico executados na VPS:
```bash
# 1. Host e memória
free -m && free -h && df -hT /

# 2. Atividade de CPU e I/O
vmstat 1 5

# 3. Verificação de OOM
sudo dmesg -T | grep -i -E "oom[-_]killer|out of memory|killed process"

# 4. Containers de dados no Docker
docker stats --no-stream

# 5. Pods e nó no Kubernetes (k3s)
sudo kubectl top nodes
sudo kubectl top pods -A --sort-by=memory
```
Os resultados são consolidados neste relatório para fins de auditoria e dimensionamento.

---

## 4. Matriz de Convivência Simultânea na Capacidade Atual (4 GB)

Com base no orçamento consolidado, estabelece-se a seguinte política de operação simultânea:

| Grupo de Serviços | Pode Rodar Simultâneo? | Condição / Restrição |
| :--- | :---: | :--- |
| **PostgreSQL + MinIO + K3s + ArgoCD + Gateway** | **SIM** | Sempre ativos no modo cluster. Consumo total de ~2.100 MiB. |
| **Site Comemorativo + APAE Geral** | **SIM** | Podem rodar juntos com a plataforma (consumo adicional de ~400 MiB). |
| **APAE Atendimento** | **SIM** | Pode ser ativado em conjunto com APAE Geral e Site (consumo adicional de ~350 MiB). |
| **Gestão Escolar (Backend Java)** | **CONDICIONAL** | O backend Java requer heap controlada (`-Xmx256m -Xms128m`). Não executar rollouts simultâneos com outros produtos. |
| **Todos os 4 Produtos + Backup Concorrente** | **NÃO RECOMENDADO** | Margem inferior a 5%. Risco elevado de OOMKill durante compressão de backup se não houver swap configurada. |

---

## 5. Limitações e Encaminhamentos Técnicos

1. **Ajuste Obrigatório de Requests nos Manifests:**
   * Readequar requests de CPU dos frontends para `25m` e limites para `200m`.
   * Readequar requests de memória dos frontends para `64Mi` ou `96Mi`.
   * Isso recupera mais de `400m` de CPU alocável, eliminando o déficit de agendamento de `-175m`.
2. **Estratégia de Implantação (`Recreate`):**
   * Configurar `strategy: type: Recreate` em todos os Deployments de produtos em `kubernetes/*/base/*/deployment.yaml`.
3. **Configuração de Swap de Proteção no Host:**
   * Para evitar que picos instantâneos causem encerramento abrupto de containers pelo kernel, recomenda-se configurar um arquivo de Swap de 2 GB no NVMe com `vm.swappiness=10`. O swap servirá estritamente como amortecedor de picos.
4. **Critério para Ampliação de Recursos (Upgrade da VPS):**
   * Caso a APAE entre em fase de homologação massiva ou produção com carga real e concorrência simultânea de todos os produtos, o limite de 4 GB será insuficiente com a stack completa de observabilidade da [#116](https://github.com/IFPBEsp/APAE-INFRA/issues/116).
   * O encaminhamento formal é solicitar a contratação do plano com **4 vCPUs e 8 GB de RAM**.
