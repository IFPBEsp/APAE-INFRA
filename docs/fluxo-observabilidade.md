# Fluxo de observabilidade

Este documento descreve, em nível conceitual, como a stack de observabilidade (Prometheus, Loki, Grafana) é organizada: de onde vêm as métricas, de onde vêm os logs, como são coletados/agregados, e como o Grafana consome essas fontes para dashboards e alertas.

## Visão geral

A stack de observabilidade roda no mesmo cluster monitorado, gerenciada via GitOps no mesmo padrão **App of Apps** já adotado para as 4 aplicações ([fluxo do ArgoCD](argocd/fluxo-argocd.md)):

- **Prometheus** coleta métricas dos Pods/Deployments de todas as aplicações e do próprio cluster;
- **Loki** centraliza os logs de todos os Pods;
- **Grafana** consome Prometheus e Loki como datasources e concentra dashboards e alertas.

## 1. Coleta de métricas

Duas origens de métricas:

1. **Métricas do cluster** — via [`kube-state-metrics`](https://github.com/kubernetes/kube-state-metrics) (estado dos objetos Kubernetes: Deployments, Pods, réplicas) e `cAdvisor` (consumo de CPU/memória por container, já embutido no kubelet). O Prometheus faz scrape de ambos.
2. **Métricas das aplicações** — conforme [boas práticas de observabilidade](boas-praticas/08-observabilidade.md#83-métricas), aplicações expõem métricas quando houver suporte. O backend Spring Boot já expõe `/apae-geral/actuator/health` (ver [ADR 001](adr/001-remocao-healthchecks.md)); o mesmo mecanismo (Actuator + Micrometer, endpoint `/actuator/prometheus`) pode ser reaproveitado para métricas de aplicação.

O Prometheus descobre os alvos de scrape via `ServiceMonitor`/`PodMonitor` (padrão do Prometheus Operator) ou configuração estática de scrape — **decisão em aberto**, ver seção de pendências.

## 2. Coleta de logs

Aplicações já seguem a diretriz de enviar logs para stdout/stderr ([boas práticas de observabilidade, 8.1](boas-praticas/08-observabilidade.md#81-logs)). A partir daí, um agente rodando como `DaemonSet` em cada nó do cluster lê os logs dos containers e envia ao Loki.

**Decisão em aberto:** qual agente usar — `Promtail` (o coletor histórico do ecossistema Loki, hoje em modo de manutenção) ou `Grafana Alloy` (substituto recomendado atualmente pela Grafana Labs, mesmo binário usado para métricas e logs). Ver seção de pendências.

## 3. Grafana como camada de consumo

O Grafana é provisionado com dois datasources, ambos apontando para os serviços internos do cluster:

- `Prometheus` (métricas);
- `Loki` (logs).

O provisionamento dos datasources segue o mesmo princípio de GitOps das demais aplicações: definido em manifesto versionado (`monitoring/grafana/`), aplicado pelo ArgoCD, sem configuração manual pela UI.

## 4. Organização de dashboards

Seguindo [boas práticas de observabilidade, 8.4](boas-praticas/08-observabilidade.md#84-dashboards) (dashboards com finalidade clara), a proposta é organizar por:

- **Aplicação** — um dashboard por repositório orquestrado (APAE, APAE-atendimento, APAE-gestao-escolar, apae-site-comemorativo), com CPU, memória, disponibilidade, taxa de erros e latência daquela aplicação;
- **Cluster** — um dashboard geral de saúde do cluster (uso de recursos por node, reinicializações de Pods, estado das Applications do ArgoCD).

Dashboards por ambiente (dev/hml/prod) seguem a mesma separação já usada em `kubernetes/overlays/{ambiente}`, conforme os ambientes forem estruturados.

## 5. Fluxo de alertas

Quem dispara o alerta, os critérios e o canal de notificação ainda não foram decididos pela equipe. Duas abordagens possíveis:

- **Prometheus Alertmanager** — regras de alerta definidas junto ao Prometheus, roteamento e agrupamento de notificações no Alertmanager;
- **Grafana Alerting** — regras definidas no próprio Grafana, reaproveitando os mesmos datasources já provisionados, sem precisar de um componente adicional.

**Decisão em aberto**, ver seção de pendências.

## Onde a stack roda

Seguindo o padrão já estabelecido no `fluxo-argocd.md`, a stack de observabilidade seria mais uma Application (ou grupo de Applications) filha da raiz `apae-root`, com seus manifestos organizados em `kubernetes/base/monitoring/` e `kubernetes/overlays/{ambiente}/monitoring/`, do mesmo jeito que as 4 aplicações.

**Decisão em aberto:** namespace dedicado (`monitoring`, por exemplo) versus um namespace por componente. Ver seção de pendências.

## Decisões em aberto (para validação da equipe)

| Ponto | Opções | Observação |
| --- | --- | --- |
| Agente de coleta de logs | Promtail / Grafana Alloy | Alloy é o caminho recomendado atualmente pela Grafana Labs |
| Ferramenta de alertas | Prometheus Alertmanager / Grafana Alerting | Grafana Alerting evita um componente a mais no cluster |
| Canal de notificação de alertas | A definir (ex: Slack, Discord, e-mail) | Depende de onde a equipe já centraliza avisos |
| Descoberta de alvos do Prometheus | ServiceMonitor/PodMonitor (Prometheus Operator) / scrape config estático | Impacta se vamos adotar o Prometheus Operator ou instalação mais simples |
| Namespace(s) da stack | Um namespace único `monitoring` / um por componente | Segue o mesmo raciocínio de `apae-*` já usado para as aplicações |

## Diagrama

O diagrama Excalidraw será produzido depois que este texto for validado pela equipe, seguindo o mesmo fluxo usado na issue #10 (texto primeiro, diagrama depois, para reduzir retrabalho).

Issue relacionada: `APAE-INFRA#13`