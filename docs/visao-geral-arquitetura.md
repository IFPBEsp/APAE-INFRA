# Visão Geral da Arquitetura de Infraestrutura — APAE

Este documento apresenta uma visão de alto nível de como todas as peças da infraestrutura APAE se conectam: repositórios de aplicação, provisionamento via Terraform, build e entrega de imagens (GitHub Actions), entrega contínua via ArgoCD e observabilidade. Funciona como ponto de entrada para a documentação de infraestrutura, com referências para os documentos detalhados de cada fluxo.

![Diagrama de Visão Geral da Arquitetura](diagramas/visao-geral-arquitetura.svg)

---

## Os cinco pilares da arquitetura

### 1. Repositórios de Aplicação

O projeto APAE é composto por quatro repositórios de código-fonte, cada um representando um sistema independente:

| Repositório | Responsabilidade |
| --- | --- |
| [APAE](https://github.com/IFPBEsp/APAE) | Sistema principal (backend Spring Boot) |
| [APAE-atendimento](https://github.com/IFPBEsp/APAE-atendimento) | Sistema de atendimento |
| [APAE-gestao-escolar](https://github.com/IFPBEsp/APAE-gestao-escolar) | Sistema de gestão escolar |
| [apae-site-comemorativo](https://github.com/IFPBEsp/apae-site-comemorativo) | Site comemorativo |

Cada repositório de aplicação segue o mesmo ciclo de vida, de forma completamente independente dos demais. Eles **não se comunicam entre si** nem aplicam nada diretamente no cluster — toda a orquestração passa pelo **APAE-INFRA**.

### 2. Provisionamento de Infraestrutura — Terraform + GitHub Actions

O Terraform é responsável pela **infraestrutura fundacional**: VPS, rede, firewall e bootstrap do host (incluindo a instalação inicial do Kubernetes e do ArgoCD). Após esse bootstrap, o ArgoCD passa a ser gerenciado exclusivamente via Git.

**Decisão arquitetural:** o Terraform é executado pelo GitHub Actions (workflows de `fmt`, `validate`, `plan` com aprovação manual e `apply`), **não** pelo ArgoCD. Isso evita o problema de bootstrap circular e mantém o ArgoCD focado na reconciliação de recursos Kubernetes.

O state do Terraform é armazenado remotamente no **Contabo Object Storage**, com locking habilitado para prevenir aplicações concorrentes.

> Detalhes: [docs/terraform/](terraform/README.md)

### 3. Build e Entrega de Imagens — GitHub Actions (CI)

Cada repositório de aplicação possui um pipeline de CI em três estágios:

1. **PR para `dev`** — lint, testes, build, validação do Dockerfile, análise SCA (dependências vulneráveis) e análise SAST via SonarQube.
2. **Merge na `dev`** — testes de integração.
3. **Merge na `main`** — build da imagem Docker, push para o **GHCR (GitHub Container Registry)** e **Image Updater**: um job que abre um PR no APAE-INFRA atualizando a tag da imagem no overlay Kustomize correspondente.

O ArgoCD não acessa o GHCR diretamente — ele lê apenas o APAE-INFRA e reage à mudança de tag nos manifestos.

> Detalhes: [docs/fluxo-comunicacao-repositorios.md](fluxo-comunicacao-repositorios.md)

### 4. Entrega Contínua — ArgoCD (GitOps)

O **APAE-INFRA** é o repositório GitOps: a única fonte de verdade lida pelo ArgoCD. O padrão adotado é o **App of Apps**:

- **`apae-root`** (Application raiz) — monitora `argocd/` com busca recursiva e garante que as 4 Applications filhas existam no cluster.
- **4 Applications filhas** — cada uma aponta para o overlay Kustomize correspondente em `kubernetes/overlays/dev/{aplicacao}/` e sincroniza de forma independente.

**Política atual:** sync **manual** em todas as Applications filhas. O ArgoCD sinaliza "Out of Sync", mas só aplica quando alguém aprovar manualmente (UI ou CLI). Essa política será reavaliada quando o pipeline de CI/CD tiver testes obrigatórios e histórico estável de releases.

Todo estado do cluster é descrito nos manifestos do APAE-INFRA. **Não há `kubectl apply` manual** — qualquer mudança no cluster passa por um commit no APAE-INFRA seguido de aprovação de sync no ArgoCD.

> Detalhes: [docs/argocd/fluxo-argocd.md](argocd/fluxo-argocd.md)

### 5. Observabilidade — Prometheus, Loki e Grafana

A stack de observabilidade roda no **namespace `monitoring`** do mesmo cluster, gerenciada pelo mesmo padrão GitOps (Applications filhas do ArgoCD lendo de `monitoring/`):

| Componente | Função |
| --- | --- |
| **Prometheus** | Coleta métricas dos Pods, nodes (node-exporter), estado do cluster (kube-state-metrics) e do próprio ArgoCD |
| **Loki + Grafana Alloy** | Centraliza logs dos containers (Alloy como agente DaemonSet, substituto do Promtail descontinuado) |
| **Grafana** | Dashboards por aplicação e por cluster; datasources provisionados via GitOps |
| **Grafana Alerting** | Regras de alerta com notificação via Discord |

Descoberta de alvos do Prometheus via **Prometheus Operator** (`ServiceMonitor` / `PodMonitor`), declarativo e alinhado ao GitOps.

> Detalhes: [docs/fluxo-observabilidade.md](fluxo-observabilidade.md)

---

## Como uma mudança se propaga até o cluster

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Repositório de Aplicação                                                         │
│  commit → PR → CI (lint/testes/build) → merge main                              │
│    → build imagem Docker → push GHCR → Image Updater abre PR no APAE-INFRA     │
└────────────────────────────────┬─────────────────────────────────────────────────┘
                                 │ PR revisado + mergeado
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ APAE-INFRA (GitOps repo)                                                         │
│  kubernetes/overlays/dev/{app}/kustomization.yaml  ← tag atualizada             │
└────────────────────────────────┬─────────────────────────────────────────────────┘
                                 │ ArgoCD detecta Out-of-Sync
                                 │ Aprovação manual → sync
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Cluster Kubernetes                                                               │
│  ArgoCD aplica rolling update → Pods sobem com a nova imagem do GHCR            │
│  Prometheus + Loki coletam métricas/logs → Grafana exibe dashboards             │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Estrutura do APAE-INFRA

```text
APAE-INFRA/
├── .github/
│   └── workflows/          # Workflows reutilizáveis: build-publish, SCA, remoção de branches
├── argocd/                 # App of Apps: project.yaml, app-of-apps.yaml, {app}/dev.yaml
├── kubernetes/
│   ├── base/{app}/         # Manifests Kubernetes comuns (Deployment, Service...)
│   └── overlays/{env}/{app}/ # Patches de ambiente (réplicas, variáveis, tag de imagem)
├── monitoring/
│   ├── grafana/            # Datasources, dashboards e alertas provisionados via GitOps
│   ├── prometheus/         # Prometheus Operator, ServiceMonitors/PodMonitors
│   └── loki/               # Loki + Grafana Alloy (agente DaemonSet)
├── terraform/
│   ├── modules/            # Módulos reutilizáveis
│   └── environments/       # Configuração por ambiente (dev/hml/prod)
└── docs/                   # Documentação de padrões e fluxos
    └── diagramas/          # Diagramas Excalidraw e SVG
```

---

## Documentação detalhada por fluxo

| Fluxo | Documento |
| --- | --- |
| Comunicação entre repositórios e CI/CD | [docs/fluxo-comunicacao-repositorios.md](fluxo-comunicacao-repositorios.md) |
| Terraform — arquitetura e decisões | [docs/terraform/README.md](terraform/README.md) |
| ArgoCD — GitOps e App of Apps | [docs/argocd/fluxo-argocd.md](argocd/fluxo-argocd.md) |
| Observabilidade — Prometheus, Loki, Grafana | [docs/fluxo-observabilidade.md](fluxo-observabilidade.md) |
| Boas práticas gerais | [docs/boas-praticas/](boas-praticas/) |

---

## Diagramas

- [Diagrama de Visão Geral (SVG)](diagramas/visao-geral-arquitetura.svg)
- [Diagrama de Visão Geral (Excalidraw editável)](diagramas/visao-geral-arquitetura.excalidraw)
- [Fluxo do ArgoCD (SVG)](diagramas/fluxo-argocd.svg)
- [Fluxo de Comunicação entre Repositórios (SVG)](diagramas/fluxo-comunicacao-repositorios.svg)
- [Fluxo de Observabilidade (SVG)](diagramas/fluxo-observabilidade.svg)

Issue relacionada: `APAE-INFRA#14`
