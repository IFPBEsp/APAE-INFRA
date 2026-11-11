# Publicação de imagens a partir da main dos produtos

A origem das imagens que chegam ao APAE-INFRA é sempre a `main` de cada
repositório de produto. A referência `@main` do workflow reutilizável seleciona
a versão da automação da infraestrutura; o evento `push` na `main` do produto
seleciona o código da aplicação a construir. As duas referências precisam estar
corretas.

## Contrato de publicação e recebimento

1. Um push na `main` do produto inicia o build de todos os seus serviços.
   O reutilizável também aceita execução manual na `main`, mas o caller deve
   habilitar tanto a publicação quanto a notificação nesse evento para isso
   funcionar de ponta a ponta. Publicar ambos permite associar as
   imagens ao mesmo commit, mesmo quando apenas um serviço mudou.
2. O produto chama `IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@main`.
   O caller concede `contents: read`, `packages: write`, `id-token: write` e
   `attestations: write`.
3. O workflow aceita somente eventos `push` ou `workflow_dispatch` na `main`.
   Confere o HEAD do produto antes do build e novamente antes da promoção das
   tags, após scan, assinatura e verificação de proveniência.
4. Uma publicação aprovada expõe imagem, digest, tag por commit, repositório,
   commit e referência Git de origem. `latest` serve apenas para conveniência;
   a tag `dev` deixa de ser publicada pelo workflow.
5. O caller notifica o APAE-INFRA apenas quando a publicação termina com
   sucesso e a origem continua sendo `refs/heads/main`. Geral, Atendimento e
   Gestão Escolar enviam `gitops-release-published`, com frontend e backend da
   mesma execução. Somente o Site envia `gitops-image-published`.
6. O receptor verifica o commit atual da `main`, a existência da tag, o digest e
   a proveniência autenticada. Reconfere o HEAD antes de abrir ou atualizar o
   PR do overlay. Um evento de commit antigo ou uma falha na API interrompe a
   atualização, sem abrir PR com aquela imagem.
7. Um PR para a `main` do APAE-INFRA altera somente o overlay `dev` do produto
   e seu registro em `releases/candidates/`. O overlay usa
   `image@sha256:<digest>`. `dev` é o nome do ambiente de homologação;
   as imagens e os manifests vêm das respectivas branches `main`.

Se o scan do commit mais recente falhar, a infraestrutura mantém a imagem já
aprovada. Não se troca a origem para a branch `dev` nem se desabilita o scan
para forçar a atualização. A nova imagem depende da correção do produto e de
uma publicação aprovada de sua `main`.

Os checks de HEAD representam o estado no instante de cada consulta. Uma
mudança posterior na `main` pode tornar um PR aberto obsoleto; a revisão humana
deve confirmar a origem novamente antes do merge. Estes workflows não fazem
merge automático nem sincronizam o cluster.

## Produtos e imagens

| Produto | Aplicação no payload | Imagens |
| --- | --- | --- |
| `IFPBEsp/APAE` | `apae-geral` | `apae-geral-backend`, `apae-geral-frontend` |
| `IFPBEsp/APAE-atendimento` | `apae-atendimento` | `apae-atendimento-backend`, `apae-atendimento-frontend` |
| `IFPBEsp/APAE-gestao-escolar` | `apae-gestao-escolar` | `apae-gestao-escolar-backend`, `apae-gestao-escolar-frontend` |
| `IFPBEsp/apae-site-comemorativo` | `site-comemorativo` | `apae-site-comemorativo` |

## Ordem de ativação

- Publicar as alterações da infraestrutura em sua `main` antes de integrar os
  callers dos produtos. Os workflows dos produtos dependem dos novos outputs
  e da publicação de proveniência do workflow compartilhado.
- Disponibilizar na `main` do APAE-INFRA os overlays de homologação previstos
  pelo receptor. Os caminhos são `kubernetes/apae-geral/overlays/dev`,
  `kubernetes/apae-atendimento/overlays/dev`,
  `kubernetes/gestao-escolar/overlays/dev` e
  `kubernetes/site-comemorativo/overlays/dev`. O identificador no payload de
  Gestão Escolar continua sendo `apae-gestao-escolar`.
- Configurar no environment `gitops-dispatch` dos produtos a variável
  `GITOPS_DISPATCH_APP_ID` e o secret `GITOPS_DISPATCH_APP_PRIVATE_KEY` do App
  de notificação, com `contents: write` somente no APAE-INFRA. Esse App não abre
  PRs. No environment `gitops-image-updater` da infraestrutura, configurar os
  secrets `IMAGE_UPDATER_APP_ID` e `IMAGE_UPDATER_APP_PRIVATE_KEY` para o App
  que abre PRs, com `contents: write` e `pull_requests: write` somente no
  APAE-INFRA. A chave desse segundo App permanece exclusivamente na INFRA.
- Permitir a branch padrão da INFRA, atualmente `dev`, nos environments
  `gitops-image-updater`, `release-approval` e `production-promotion`.
  O `repository_dispatch` executa pela branch padrão. Nos produtos, permitir
  `main` no environment `gitops-dispatch`. Os registros e manifests da INFRA
  continuam na `main`, independentemente da revisão da automação.
- Garantir leitura das imagens no GHCR. O receptor pode usar
  `GHCR_READ_USERNAME` e `GHCR_READ_TOKEN` quando o token da infraestrutura não
  tiver acesso aos pacotes. A consulta da referência `main` também exige
  acesso de leitura ao repositório do produto.
- Integrar os callers na `main` dos produtos e acompanhar a publicação.
  Corrigir eventuais falhas do scan no produto antes de tentar novamente.
- Conferir o PR gerado, o digest, o commit da `main` e os checks antes do merge.
  A promoção posterior para produção deve reutilizar o mesmo digest aprovado.

O passo a passo de aprovação, promoção, rollback, configuração dos frontends e
coleta de evidências está em [Releases GitOps](releases-gitops.md).

## Validação local

Os testes de `tests/test_main_image_policy.py` executam os scripts reais dos
workflows com a API simulada. Cobrem HEAD atual, builds antigos, origem `dev`,
feature branches, tags e falhas de consulta. Também verificam as barreiras
antes de promover tags ou criar PRs. A suíte de GitOps existente continua
validando registro, proveniência e edição de overlays.

```bash
python3 -m unittest discover -s tests -v
actionlint .github/workflows/docker-build-publish-image.yml .github/workflows/update-image-overlay-reusable.yml .github/workflows/gitops-workflows-test.yml
```

A suíte completa requer Kustomize 5.8.1, instalado pelo composite action
`.github/actions/setup-kustomize` na CI.
