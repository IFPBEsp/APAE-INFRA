# APAE-INFRA

Repositório responsável por centralizar a infraestrutura e o DevOps do projeto APAE, orquestrando os repositórios de aplicação abaixo.

## Objetivo

Manter em um único lugar tudo que é infraestrutura como código, pipelines de CI/CD e observabilidade usados pelos sistemas da APAE, em vez de espalhar isso por cada repositório de aplicação.

## Tecnologias utilizadas

- ArgoCD
- Kubernetes
- Docker
- GitHub Actions
- Terraform
- Grafana
- Prometheus
- Loki

## Repositórios orquestrados

- [APAE](https://github.com/IFPBEsp/APAE)
- [APAE-atendimento](https://github.com/IFPBEsp/APAE-atendimento)
- [APAE-gestao-escolar](https://github.com/IFPBEsp/APAE-gestao-escolar)
- [apae-site-comemorativo](https://github.com/IFPBEsp/apae-site-comemorativo)

## Estrutura de diretórios

```
.github/
  workflows/      # pipelines de CI/CD (GitHub Actions)
argocd/           # manifests de aplicação para o ArgoCD
docker/           # Dockerfiles e configurações de containers
docs/             # documentação de padrões e boas práticas do repositório
kubernetes/       # manifests e configurações do cluster
monitoring/
  grafana/        # dashboards
  prometheus/     # regras e configuração de métricas
  loki/           # configuração de logs
terraform/
  modules/        # módulos reutilizáveis
  environments/   # configuração por ambiente (dev/hml/prod)
```

> Proposta inicial para validação com o time — pode ser revisada conforme surgirem necessidades reais de cada aplicação.

### Separação por ambiente (dev/hml/prod)

- **Terraform:** cada ambiente tem sua própria pasta em `terraform/environments/`, com variáveis e state próprios, usando os módulos compartilhados de `terraform/modules/`.
- **Kubernetes/ArgoCD:** padrão Kustomize — manifests comuns em `kubernetes/base/`, e os ajustes de cada ambiente em `kubernetes/overlays/{dev,hml,prod}/`.

### Separação por aplicação

Os 4 repositórios orquestrados (listados acima) são organizados como uma subdivisão dentro de cada ambiente:

- **Kubernetes:** `kubernetes/base/{aplicacao}/` e `kubernetes/overlays/{ambiente}/{aplicacao}/`;
- **ArgoCD:** uma `Application` por combinação aplicação + ambiente, agrupada em `argocd/{aplicacao}/`.

As subpastas de cada aplicação e ambiente serão criadas conforme o trabalho avançar — por enquanto só existe o esqueleto base.

## Como contribuir

Padrões de branch, commits e Pull Request estão centralizados em [CONTRIBUTING.md](CONTRIBUTING.md).