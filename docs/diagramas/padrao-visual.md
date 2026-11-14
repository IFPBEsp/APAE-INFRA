# Padrão visual dos diagramas

Este documento define o padrão visual dos diagramas Excalidraw de fluxo e arquitetura do APAE-INFRA. Todo diagrama novo ou revisado em `docs/diagramas/` deve seguir estas regras, para que a documentação de arquitetura possa ser lida em conjunto sem que cada diagrama use um estilo próprio.

O padrão tem como referência o diagrama de fluxo de deploy usado no planejamento da infraestrutura: caixas de contorno limpo, logo da tecnologia no canto superior esquerdo, título ao lado da logo e detalhes em lista logo abaixo.

## Arquivos

| Arquivo | Conteúdo |
| :--- | :--- |
| `docs/diagramas/<nome>.excalidraw` | Fonte editável do diagrama, com as logos embutidas |
| `docs/diagramas/<nome>.svg` | Exportação usada nos documentos Markdown e no README |
| `docs/diagramas/logos/` | Logos padronizadas para reutilizar em diagramas novos |

O `.excalidraw` e o `.svg` têm sempre o mesmo nome e são atualizados juntos, no mesmo PR.

## Estilo base

| Propriedade | Valor | Onde fica no Excalidraw |
| :--- | :--- | :--- |
| Fonte | Nunito | Fonte "Normal" |
| Traço | Arquiteto (sem efeito rabiscado) | Sloppiness: Architect (`roughness: 0`) |
| Espessura | Fina | Stroke width: thin (`strokeWidth: 2`) |
| Cantos | Arredondados | Edges: round |
| Preenchimento | Transparente | Background: transparent |
| Fundo do canvas | Branco | `#ffffff` |

Não se usa preenchimento colorido nas caixas. A cor fica somente no contorno, e o texto é sempre preto (`#1e1e1e`), exceto no título do cluster e nas notas secundárias.

## Tamanhos de texto

| Uso | Tamanho |
| :--- | :--- |
| Título do diagrama | 40 |
| Título do cluster Kubernetes | 34 a 40, na cor do cluster |
| Título de grupo | 22 a 28 |
| Título de caixa | 20 a 28 (menor só quando o nome não cabe) |
| Detalhes da caixa, rótulos de seta e notas | 18 a 20 |

## Elementos

Cada tipo de elemento usa sempre a mesma forma, cor de contorno e logo em todos os diagramas.

| Elemento | Forma | Contorno | Logo |
| :--- | :--- | :--- | :--- |
| Repositório Git (aplicação ou APAE-INFRA) | Caixa | Preto `#1e1e1e` | Git |
| Pipeline de CI / job do GitHub Actions | Caixa | Azul `#4071e2` | GitHub Actions |
| Registry de imagens (GHCR) | Caixa | Roxo `#6741d9` | GHCR |
| Controle GitOps (ArgoCD, App of Apps, Applications) | Caixa | Laranja `#f08c00` | ArgoCD |
| Workload no cluster (namespace, Application de produto, Pods) | Caixa | Verde `#2f9e44` | Cubo |
| Ferramenta de observabilidade (Prometheus, Loki, Alloy, Grafana) | Caixa | Preto `#1e1e1e` | Logo da ferramenta |
| Provisionamento e configuração (Terraform, Ansible) | Caixa | Preto `#1e1e1e` | Terraform / Ansible |
| Servidor ou recurso externo (VPS) | Caixa | Preto `#1e1e1e` | Servidor |
| Serviço externo (Discord) | Caixa | Preto `#1e1e1e` | Logo do serviço |
| Etapa de processo sem tecnologia própria (Commit, Code Review, Merge) | Caixa | Preto `#1e1e1e` | Sem logo |
| Elemento planejado, ainda não implantado | Caixa tracejada | Cinza `#868e96` | Logo da tecnologia |

### Agrupadores

| Agrupador | Forma | Contorno |
| :--- | :--- | :--- |
| Cluster Kubernetes (limite físico) | Caixa sólida, título com logo do Kubernetes | Azul `#1971c2` |
| Agrupamento lógico (namespace, conjunto de repositórios, "Observabilidade") | Caixa tracejada | Preto `#1e1e1e` |
| Pipeline que contém etapas | Caixa tracejada com logo do GitHub Actions | Azul `#4071e2` |

Elipses e losangos não são usados. Toda informação fica em caixas.

## Composição da caixa

```text
┌──────────────────────────────────────┐
│ [logo]  Título                       │
│                                      │
│ - detalhe 1                          │
│ - detalhe 2                          │
└──────────────────────────────────────┘
```

* A logo fica no canto superior esquerdo, com 56 a 88 px.
* O título fica à direita da logo, centralizado verticalmente em relação a ela.
* Os detalhes ficam em lista iniciada por hífen, alinhados à esquerda, abaixo da logo.
* Caixas sem logo têm só o título no topo e, se precisar, a lista abaixo.
* Logo, retângulo e textos de uma caixa ficam agrupados (Ctrl+G), para moverem juntos.

## Logos

As logos ficam em [`logos/`](logos/) e devem ser reaproveitadas em vez de baixadas de novo, para manter o mesmo desenho em todos os diagramas.

| Arquivo | Uso |
| :--- | :--- |
| `git.png` | Repositórios Git |
| `actions.png` | GitHub Actions e etapas de CI |
| `ghcr.png` | GitHub Container Registry |
| `argocd.png` | ArgoCD, App of Apps, Applications e AppProject |
| `kubernetes.png` | Cluster Kubernetes e componentes nativos (kube-state-metrics, kubelet) |
| `cube.png` | Workloads: namespace, Application de produto, Pods |
| `prometheus.png` | Prometheus e Prometheus Operator |
| `grafana.png` | Grafana e Grafana Alloy |
| `loki.png` | Loki |
| `terraform.svg` | Terraform, módulos, ambientes e state |
| `ansible.svg` | Ansible |
| `discord.svg` | Discord |
| `springboot.svg` | Backends Spring Boot |
| `docker.svg` | Dockerfile e imagens, quando a imagem for o assunto principal |
| `server.svg` | VPS e servidores (a HostGator não tem logo padronizada) |

Logos novas devem ter fundo transparente, ser recortadas sem margem e ter no máximo 160 px no maior lado, para não aumentar demais o `.excalidraw`.

## Conectores

| Seta | Significado |
| :--- | :--- |
| Sólida, uma ponta | Fluxo principal: execução, dado ou artefato indo de um ponto a outro |
| Tracejada, uma ponta | Gestão ou configuração: provisiona, faz bootstrap, ajusta permissões, puxa uma imagem |
| Sólida, duas pontas | Leitura e escrita contínuas entre os dois lados (ex: Terraform ↔ state) |

* Pontas em triângulo cheio, cor preta (`#1e1e1e`).
* Setas em ângulo reto. Diagonais não são usadas.
* A seta sai e chega no centro da borda da caixa, ligada à caixa (binding), para acompanhar quando a caixa for movida.
* O fluxo principal corre da esquerda para a direita ou de cima para baixo.

## Rótulos e notas

* O rótulo da seta é texto solto, sem caixa, posicionado ao lado do trecho que descreve, sem cruzar outras linhas.
* Use verbos curtos no rótulo: `lê`, `sync`, `scrape`, `envia`, `alertas`, `merge aprovado`.
* Notas explicativas e observações secundárias usam texto cinza (`#868e96`) e tamanho 18.
* Itens planejados levam `(planejado)` no título, além do contorno tracejado cinza.
* Todo diagrama começa com um título (tamanho 40) e, opcionalmente, um subtítulo cinza com o escopo.

## Exportação para SVG

1. Abra o `.excalidraw` no [excalidraw.com](https://excalidraw.com) ou no plugin Excalidraw do Obsidian.
2. Exporte como SVG, com fundo branco e sem embutir a cena.
3. Salve o arquivo com o mesmo nome do `.excalidraw`, substituindo o `.svg` anterior.
4. Confira no preview do PR se o diagrama aparece corretamente no documento que o referencia.

## Checklist de revisão

* [ ] Fonte Nunito, traço arquiteto e cantos arredondados em todos os elementos
* [ ] Cada elemento usa a forma, a cor e a logo da tabela de elementos
* [ ] Logos reaproveitadas de `docs/diagramas/logos/`
* [ ] Setas em ângulo reto, sólidas para fluxo e tracejadas para gestão ou configuração
* [ ] Rótulos sem sobrepor caixas ou outras setas
* [ ] Planejado em tracejado cinza, com `(planejado)` no título
* [ ] `.excalidraw` e `.svg` atualizados no mesmo PR

## Aderência dos diagramas existentes

Antes deste padrão, cada diagrama usava uma fonte diferente (Virgil, Excalifont ou Nunito), alguns tinham preenchimento colorido e outros não, e o fluxo do ArgoCD usava elipses para descrever etapas. Os cinco diagramas foram refeitos neste padrão:

| Diagrama | Issue | Situação |
| :--- | :--- | :--- |
| [`fluxo-comunicacao-repositorios`](fluxo-comunicacao-repositorios.svg) | #10 | Refeito no padrão. Application e Pods de cada produto passaram a ser uma única caixa por produto |
| [`fluxo-argocd`](fluxo-argocd.svg) | #11 | Refeito no padrão. Elipses de etapas viraram caixas de CI. O quadro vazio "Fluxo Repositórios Terraform" foi removido, porque esse fluxo está em `fluxo-terraform`. Pods → Loki e Loki → Grafana substituem a seta Prometheus → Loki |
| [`fluxo-terraform`](fluxo-terraform.svg) | #12 | Refeito no padrão |
| [`fluxo-observabilidade`](fluxo-observabilidade.svg) | #13 | Refeito no padrão, com o cluster Kubernetes como limite explícito |
| [`visao-geral-arquitetura`](visao-geral-arquitetura.svg) | #14 | Refeito no padrão |
