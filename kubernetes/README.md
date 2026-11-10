# Manifests Kubernetes

Cada produto possui uma base e overlays `dev` (homologação) e `prod` (produção).
Ambos são reconciliados a partir da `main` do APAE-INFRA, em namespaces
separados (`apae-dev` e `apae-prod`), por Applications com sync manual.

Os overlays iniciais têm zero réplicas. As atualizações automatizadas alteram
somente os digests: a ativação exige configurar as dependências e revisar as
réplicas em outro PR. Não ativar produção com a referência `unpublished`.

Gestão Escolar usa `kubernetes/gestao-escolar`, embora sua release seja
identificada por `apae-gestao-escolar`. Não renomear as imagens por causa disso.

Ver [operação de releases](../docs/workflows/releases-gitops.md) e
[Applications e bootstrap](../docs/argocd/fluxo-argocd.md).
