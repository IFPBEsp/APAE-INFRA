# APAE-INFRA

Repositório responsável por centralizar a infraestrutura e os processos de DevOps do projeto APAE, orquestrando os repositórios de aplicação abaixo.

## Objetivo

Manter em um único lugar tudo que é infraestrutura como código, pipelines de CI/CD e observabilidade usados pelos sistemas da APAE, em vez de espalhar essas configurações por cada repositório de aplicação.

## Tecnologias utilizadas

- [ArgoCD](https://argo-cd.readthedocs.io/en/stable/)
- [Kubernetes](https://kubernetes.io/)
- [Docker](https://www.docker.com/)
- [GitHub Actions](https://github.com/features/actions)
- [Terraform](https://www.terraform.io/)
- [Grafana](https://grafana.com/)
- [Prometheus](https://prometheus.io/)
- [Loki](https://grafana.com/oss/loki/)

## Repositórios orquestrados

- [APAE](https://github.com/IFPBEsp/APAE)
- [APAE-atendimento](https://github.com/IFPBEsp/APAE-atendimento)
- [APAE-gestao-escolar](https://github.com/IFPBEsp/APAE-gestao-escolar)
- [apae-site-comemorativo](https://github.com/IFPBEsp/apae-site-comemorativo)

## Estrutura de diretórios

```text
.github/
  workflows/        # pipelines de CI/CD (GitHub Actions)

argocd/             # manifests de aplicações para o ArgoCD

docker/             # Dockerfiles e configurações relacionadas a containers

docs/               # documentação de padrões e boas práticas do repositório

kubernetes/         # manifests e configurações Kubernetes
  {aplicacao}/
    base/           # manifests base e componentes Kustomize da aplicação
    overlays/       # customizações por ambiente (dev/hml/prod)

monitoring/
  grafana/          # dashboards
  prometheus/       # regras e configuração de métricas
  loki/             # configuração de logs

terraform/
  modules/          # módulos reutilizáveis
  environments/     # configuração por ambiente (dev/hml/prod)
```

> Estrutura sujeita a evolução conforme surgirem novas necessidades de infraestrutura e de cada aplicação.

## Organização por ambiente

### Terraform

Cada ambiente possui sua própria pasta em:

```text
terraform/environments/
```

com variáveis e state próprios, utilizando os módulos compartilhados de:

```text
terraform/modules/
```

### Kubernetes

O padrão adotado é baseado em Kustomize.

Cada aplicação possui sua própria estrutura dentro de:

```text
kubernetes/{aplicacao}/
```

Os manifests comuns ficam em:

```text
kubernetes/{aplicacao}/base/
```

e os ajustes específicos de ambiente ficam em:

```text
kubernetes/{aplicacao}/overlays/{dev,hml,prod}/
```

### ArgoCD

O ArgoCD é responsável por apontar para os manifests ou overlays correspondentes a cada aplicação e ambiente.

## Organização por aplicação

Cada produto possui uma estrutura própria dentro de `kubernetes/`.

O padrão adotado é:

```text
kubernetes/
└── {aplicacao}/
    ├── base/
    │   ├── components/
    │   ├── {servico-1}/
    │   ├── {servico-2}/
    │   └── kustomization.yaml
    └── overlays/
        ├── dev/
        ├── hml/
        └── prod/
```

Os manifests base de cada serviço ficam em:

```text
kubernetes/{aplicacao}/base/{servico}/
```

Componentes Kustomize reutilizáveis dentro da aplicação, como configurações comuns de segurança, ficam em:

```text
kubernetes/{aplicacao}/base/components/
```

Os ajustes específicos de ambiente ficam em:

```text
kubernetes/{aplicacao}/overlays/{ambiente}/
```

Exemplos de aplicações já organizadas nesse padrão:

```text
kubernetes/apae-geral/
kubernetes/apae-atendimento/
```

## Como contribuir

Padrões de branch, commits e Pull Request estão centralizados em [CONTRIBUTING.md](CONTRIBUTING.md).
