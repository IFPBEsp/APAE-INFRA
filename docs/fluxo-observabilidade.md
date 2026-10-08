# Fluxo de observabilidade

Este documento descreve, em nível conceitual, como a stack de observabilidade (Prometheus, Loki, Grafana) é organizada: de onde vêm as métricas, de onde vêm os logs, como são coletados/agregados, e como o Grafana consome essas fontes para dashboards e alertas.

## Visão geral

A stack de observabilidade roda no mesmo cluster monitorado, gerenciada via GitOps no mesmo padrão **App of Apps** já adotado para as 4 aplicações ([fluxo do ArgoCD](argocd/fluxo-argocd.md)):

- **Prometheus** coleta métricas dos Pods/Deployments de todas as aplicações e do próprio cluster;
- **Loki** centraliza os logs de todos os Pods;
- **Grafana** consome Prometheus e Loki como datasources e concentra dashboards e alertas.

## 1. Coleta de métricas

Quatro origens de métricas:

1. **Estado dos objetos Kubernetes** — via [`kube-state-metrics`](https://github.com/kubernetes/kube-state-metrics) (Deployments, Pods, réplicas).
2. **Recursos de containers e nós** — `cAdvisor` (consumo de CPU/memória por container, já embutido no kubelet) e [`node-exporter`](https://github.com/prometheus/node_exporter) (uso de CPU, memória, disco e rede por node, rodando como `DaemonSet`).
3. **ArgoCD** — métricas expostas pelos componentes do próprio ArgoCD (application-controller, server e repo-server), que permitem acompanhar o estado das Applications (sincronização e saúde).
4. **Aplicações** — conforme [boas práticas de observabilidade](boas-praticas/08-observabilidade.md#83-métricas), aplicações expõem métricas quando houver suporte. O backend Spring Boot já expõe `/apae-geral/actuator/health` (ver [ADR 001](adr/001-remocao-healthchecks.md)), pois usa o context path `/apae-geral`. A decisão é usar Actuator + Micrometer para expor as métricas de aplicação, e o caminho definitivo será registrado após a configuração da aplicação. Mantido o context path atual, o endpoint tende a ser `/apae-geral/actuator/prometheus`.

O Prometheus descobre os alvos de scrape via **Prometheus Operator**, com recursos `ServiceMonitor` e `PodMonitor`. Essa abordagem é declarativa e combina com o GitOps já adotado: cada alvo é um manifesto versionado no repositório. Em contrapartida, o Operator traz CRDs e RBAC cluster-scoped, cujo impacto no `AppProject` está em [Onde a stack roda](#onde-a-stack-roda).

## 2. Coleta de logs

Aplicações já seguem a diretriz de enviar logs para stdout/stderr ([boas práticas de observabilidade, 8.1](boas-praticas/08-observabilidade.md#81-logs)). A partir daí, um agente rodando como `DaemonSet` em cada nó do cluster lê os logs dos containers e envia ao Loki.

**Decisão:** o agente é o **`Grafana Alloy`**, substituto recomendado atualmente pela Grafana Labs. O `Promtail`, coletor histórico do ecossistema Loki, foi descontinuado e não é mais uma opção real, e adotá-lo significaria começar uma implementação nova com um componente legado.

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

**Decisão:** os alertas são definidos e disparados pelo **Grafana Alerting**, com regras no próprio Grafana reaproveitando os datasources já provisionados (Prometheus e Loki). Para o tamanho atual da stack, isso evita adicionar e operar o Prometheus Alertmanager como outro componente.

O canal de notificação é o **Discord**.

Se no futuro houver necessidade de roteamento e agrupamento de notificações mais complexos, o uso do Alertmanager pode ser reavaliado.

## Onde a stack roda

Seguindo o padrão já estabelecido no [`fluxo-argocd.md`](argocd/fluxo-argocd.md), a stack de observabilidade é composta por Applications filhas da raiz `apae-root`, definidas em `argocd/` junto das demais.

### Fonte dos manifestos: diretório `monitoring/`

Os manifestos da stack ficam em `monitoring/`, estrutura já existente no repositório desde a organização inicial do APAE-INFRA:

```text
monitoring/
  grafana/      # Grafana (datasources provisionados, dashboards, alertas)
  prometheus/   # Prometheus Operator, ServiceMonitors/PodMonitors
  loki/         # Loki e agente de coleta de logs (Grafana Alloy)
```

Diferente das aplicações, a stack **não** usa `kubernetes/base/` e `kubernetes/overlays/{ambiente}/`. Manter os artefatos em um único lugar evita duas fontes de verdade para a mesma stack. Cada Application de observabilidade aponta o `source.path` para o diretório do respectivo componente em `monitoring/`, a partir do mesmo repositório (`APAE-INFRA`), e é aplicada pelo ArgoCD como as demais.

### Namespace

A stack roda em um **namespace único, `monitoring`**. Para o tamanho atual do ambiente, separar Grafana, Loki e Prometheus em namespaces diferentes acrescentaria complexidade sem ganho relevante. Esse namespace não segue o padrão `apae-*` usado pelas aplicações.

### Impacto no AppProject

O `AppProject` `apae` ([fluxo do ArgoCD](argocd/fluxo-argocd.md#appproject-governança-compartilhada)) hoje só permite como destino os namespaces `apae-*` e `argocd`, e só libera o recurso cluster-scoped `Namespace`. Sem ajustes, o sync da stack de observabilidade falharia. É necessário:

- adicionar o namespace `monitoring` em `destinations`;
- avaliar e liberar em `clusterResourceWhitelist` os recursos cluster-scoped exigidos pelo Prometheus Operator, como `CustomResourceDefinition`, `ClusterRole` e `ClusterRoleBinding`.

Como alternativa, a stack pode ter um `AppProject` próprio, isolando essas permissões mais amplas das Applications das aplicações. A decisão inicial é ajustar o `AppProject` atual, por ser a menor mudança.

## Decisões tomadas

| Ponto | Decisão | Motivo |
| --- | --- | --- |
| Agente de coleta de logs | Grafana Alloy | Promtail foi descontinuado; Alloy é o substituto recomendado pela Grafana Labs |
| Ferramenta de alertas | Grafana Alerting | Evita operar o Alertmanager como componente adicional; pode ser reavaliado se o roteamento ficar mais complexo |
| Canal de notificação de alertas | Discord | Definido pela equipe |
| Descoberta de alvos do Prometheus | Prometheus Operator + ServiceMonitor/PodMonitor | Integração declarativa com Kubernetes, alinhada ao GitOps; exige CRDs/RBAC e ajuste no AppProject |
| Namespace(s) da stack | Namespace único `monitoring` | Separar por componente acrescentaria complexidade sem ganho para o tamanho atual do ambiente |
| Localização dos manifestos | Diretório `monitoring/` | Estrutura já existente; evita duas fontes de verdade (`kubernetes/base/monitoring` e `overlays`) |

## Diagrama

O diagrama Excalidraw será produzido depois que este texto for validado pela equipe, seguindo o mesmo fluxo usado na issue #10 (texto primeiro, diagrama depois, para reduzir retrabalho).

Issue relacionada: `APAE-INFRA#13`