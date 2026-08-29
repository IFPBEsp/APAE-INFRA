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

## Padronização

- Commits: [docs/padronizacao-commits.md](docs/padronizacao-commits.md)
- Pull Requests: [docs/padronizacao-pull-requests.md](docs/padronizacao-pull-requests.md)

## Como contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md).
