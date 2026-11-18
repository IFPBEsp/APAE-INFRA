# Applications GitOps

Os manifests usam a `main` do APAE-INFRA e sincronização manual. A raiz
descobre `apps/dev/*.yaml` e `apps/prod/*.yaml`; cada filha reconcilia o overlay
do seu produto no namespace correspondente. Projetos, namespaces e raiz são
responsabilidade do bootstrap Ansible.

Os Deployments começam com zero réplicas. Publicação, aprovação e promoção
alteram referências de imagens por PR, sem iniciar os serviços automaticamente.

Ver [arquitetura e sincronização](../docs/argocd/fluxo-argocd.md) e
[operação de releases](../docs/workflows/releases-gitops.md).
