# Estrutura do Repositório

Este documento descreve a estrutura de diretórios base do repositório **APAE-INFRA** e as estratégias de organização adotadas.

> Proposta inicial para validação com o time — a estrutura definitiva deve ser revisada conforme as necessidades reais de cada aplicação surgirem.

## Estrutura de diretórios

```
/terraform
  /modules        # módulos reutilizáveis
  /environments   # configuração por ambiente (dev, hml, prod)
/kubernetes        # manifests base e overlays por ambiente/aplicação
/argocd             # Application/AppProject manifests do ArgoCD
/docker             # Dockerfiles e configs de build compartilhadas
/.github/workflows  # pipelines de CI/CD (GitHub Actions)
/monitoring
  /grafana        # dashboards e datasources
  /prometheus     # regras de alerta e configs de scrape
  /loki           # configs de coleta de logs
/docs               # documentação do repositório
```

## Estratégia de separação por ambiente (dev/hml/prod)

* **Terraform:** cada ambiente tem sua própria pasta em `terraform/environments/{dev,hml,prod}/`, com variáveis e backend de state próprios, consumindo os módulos compartilhados de `terraform/modules/`;
* **Kubernetes/ArgoCD:** padrão Kustomize — manifests comuns em `kubernetes/base/` e ajustes específicos de cada ambiente em `kubernetes/overlays/{dev,hml,prod}/`.

## Estratégia de separação por aplicação

Os 4 repositórios orquestrados (APAE, APAE-atendimento, APAE-gestao-escolar, apae-site-comemorativo) são organizados como uma subdivisão dentro de cada ambiente:

* **Kubernetes:** `kubernetes/base/{aplicacao}/` e `kubernetes/overlays/{ambiente}/{aplicacao}/`;
* **ArgoCD:** uma `Application` por combinação aplicação + ambiente, agrupadas em `argocd/{aplicacao}/`.

As subpastas por aplicação e ambiente serão criadas conforme o trabalho de cada uma avançar — esta issue cobre apenas o esqueleto base.

## Referências

* [Padronização de mensagens de commit](padronizacao-commits.md)
* [Padronização de abertura de Pull Requests](padronizacao-pull-requests.md)
* [Padronização de Markdown](padronizacao-markdown.md)
