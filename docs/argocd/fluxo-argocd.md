# Fluxo do ArgoCD e GitOps

O ArgoCD lê os manifests da `main` do APAE-INFRA. A publicação de uma imagem
no GHCR não implanta o produto: a automação abre PRs com digests verificados,
a equipe revisa e mescla esses PRs e um operador solicita a sincronização.

## Bootstrap e AppProjects

O bootstrap Ansible instala o ArgoCD e aplica os recursos que não pertencem
às Applications de produto:

- `argocd/project-infra.yaml`: AppProject `apae-infra`, usado pela raiz.
- `argocd/project.yaml`: AppProject `apae`, usado pelos produtos.
- `argocd/namespaces.yaml`: namespaces `apae-dev` e `apae-prod`.
- `argocd/app-of-apps.yaml`: Application raiz `apae-root`.

O projeto dos produtos aceita somente este repositório, destinos `apae-*` e
tipos de recurso explicitamente permitidos. Os produtos não criam namespaces
nem recursos de escopo de cluster. O projeto da raiz permite gerenciar as
Applications filhas no namespace `argocd`.

O filtro `apps/*/*.yaml` da raiz exclui os projetos, namespaces e a própria
raiz de sua reconciliação. Alterações nesses arquivos precisam ser aplicadas
pelo bootstrap; sincronizar uma Application de produto não os atualiza.

## Applications e ambientes

```text
argocd/
  app-of-apps.yaml
  project-infra.yaml
  project.yaml
  namespaces.yaml
  apps/
    dev/
      apae-geral-dev.yaml
      apae-atendimento-dev.yaml
      gestao-escolar-dev.yaml
      site-comemorativo-dev.yaml
    prod/
      apae-geral-prod.yaml
      apae-atendimento-prod.yaml
      gestao-escolar-prod.yaml
      site-comemorativo-prod.yaml
```

Cada filha lê `kubernetes/<diretório do produto>/overlays/<dev ou prod>` na
`main`. Gestão Escolar usa o diretório `gestao-escolar`, embora o identificador
de release seja `apae-gestao-escolar`.

Há duas reconciliações independentes. A raiz acompanha os objetos Application;
cada filha acompanha os workloads do seu overlay. Um PR que altera apenas o
digest no overlay exige sync da filha, sem necessidade de sync da raiz.
Uma nova filha ou alteração em sua política exige sync da raiz.

## Sincronização manual

A raiz e as filhas não configuram `syncPolicy.automated`. Após a revisão e o
merge na `main`, inspecionar o diff e solicitar explicitamente a sincronização
da Application correspondente. Não habilitar auto-sync, prune ou self-heal
automáticos para contornar essa etapa de revisão operacional.

Ao migrar das Applications anteriores, atualizar a raiz pelo bootstrap e
sincronizá-la para remover o auto-sync das filhas existentes. A ausência dessa
opção no Git não altera uma Application no cluster antes da adoção.

Os overlays de bootstrap mantêm todos os Deployments com zero réplicas. Isso
permite preparar a reconciliação sem iniciar serviços com dependências ainda
não configuradas. A primeira promoção troca `unpublished` em produção por
digests aprovados, preservando as réplicas. A ativação exige configuração de
runtime, Secrets e dependências e uma alteração revisada das réplicas.

## Releases e evidências

A notificação de publicação abre PR de homologação na `main`, incluindo o
overlay `dev` e o registro candidato. Depois do sync e da validação funcional,
um segundo PR registra a aprovação. A promoção usa esse registro para abrir
um PR restrito ao overlay `prod`, sem reconstruir as imagens. O rollback
recupera os digests de uma combinação aprovada e registrada anteriormente.

O histórico do Git registra a intenção de implantação. A evidência do ArgoCD,
dos digests dos Pods e dos testes funcionais demonstra o que foi executado.

- [Publicação pela main dos produtos](../workflows/publicacao-main-produtos.md)
- [Operação de releases, aprovação, promoção e rollback](../workflows/releases-gitops.md)
- [Estudo de gerenciamento da VPS](../ansible/README.md)
