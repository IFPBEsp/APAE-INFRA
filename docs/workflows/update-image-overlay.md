# Atualização de imagens nos overlays GitOps

## Objetivo e decisões

O workflow `update-image-overlay-reusable.yml` implementa a issue #82: recebe os
outputs de uma publicação bem-sucedida e abre ou atualiza um PR para `main` no
APAE-INFRA. Apenas o ambiente `dev` é aceito. Ambiente e branch Git são conceitos
independentes: os overlays de desenvolvimento são versionados em `main`.

A atualização é feita por GitHub Actions com GitHub App, sem instalar ArgoCD
Image Updater no cluster. A referência gravada é `image@sha256:<digest>`; a tag
`sha-*` e o commit completo ficam no PR para rastreabilidade humana. Isso segue a
[política de imagens](../boas-praticas/16-politica-tags-imagens-docker.md).

O workflow edita exclusivamente a lista `images` do `kustomization.yaml` do
overlay, usando PyYAML 6.0.3 como equivalente a `kustomize edit set image`.
Substitui `newTag` por `digest`, preserva `newName` quando há alias e renderiza
o overlay com `kubectl kustomize` antes e depois da alteração. A operação falha
se a imagem não existir nos workloads, se houver regras ambíguas ou se imagens
de outros serviços forem alteradas. O editor pode normalizar a formatação YAML
e remover comentários do arquivo editado; as demais propriedades são preservadas.

Somente o arquivo do overlay é incluído no commit. A branch é estável por
aplicação, ambiente e imagem, por exemplo:
`gitops/apae-geral/dev/apae-geral-backend`. Novas publicações da mesma imagem
atualizam o mesmo PR aberto. Backend e frontend usam branches diferentes.
Se o digest já estiver em `main`, não é necessário criar novo PR.

O job serializa execuções da mesma imagem dentro do repositório chamador e não
cancela uma execução em andamento. Para centralizar essa coordenação entre os
repositórios, prefira o dispatcher no APAE-INFRA. Eventos devem ser enviados na
ordem de publicação: o workflow não determina a ordem cronológica dos commits.
PRs de imagens distintas podem alterar o mesmo arquivo; conflitos devem ser
resolvidos e os checks reexecutados antes do merge.

## Inputs

Todos os inputs são strings.

| Input | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- |
| `image` | Sim | — | Nome completo da imagem GHCR, sem tag ou digest, presente na allowlist. |
| `image-tag` | Sim | — | `sha-` seguido de 7 a 40 caracteres hexadecimais, prefixo do commit de origem. |
| `image-digest` | Sim | — | Digest final publicado, no formato `sha256:` e 64 caracteres hexadecimais. |
| `application` | Sim | — | Identificador da aplicação conforme tabela abaixo. |
| `environment` | Não | `dev` | Ambiente do overlay. Somente `dev` é permitido. |
| `source-repository` | Sim | — | Repositório de origem no formato `IFPBEsp/nome`. |
| `source-commit` | Sim | — | SHA completo de 40 caracteres do commit usado no build. |

| Output | Descrição |
| --- | --- |
| `pull-request-url` | URL do PR criado ou atualizado; pode ser vazio quando não há diferença. |

## Aplicações e dependência da issue #92

| Repositório de origem | `application` | Imagens autorizadas em `ghcr.io/ifpbesp/` | Overlay |
| --- | --- | --- | --- |
| `IFPBEsp/APAE` | `apae-geral` | `apae-geral-backend`, `apae-geral-frontend` | `kubernetes/overlays/dev/apae` |
| `IFPBEsp/APAE-atendimento` | `apae-atendimento` | `apae-atendimento-backend`, `apae-atendimento-frontend` | `kubernetes/overlays/dev/apae-atendimento` |
| `IFPBEsp/apae-site-comemorativo` | `site-comemorativo` | `apae-site-comemorativo` | `kubernetes/overlays/dev/apae-site-comemorativo` |

Os overlays e as Applications ainda dependem da #92. O workflow exige que o
overlay já exista em `main`; não cria estrutura de deploy, não modifica bases e
não aplica manifests no cluster. Os caminhos seguem o contrato do
[fluxo do ArgoCD](../argocd/fluxo-argocd.md).

Gestão escolar tem caminho reservado no resolvedor, mas ainda não tem manifests
base nesta implementação. Sua ativação exige definir as imagens publicadas,
adicionar os pares exatos à allowlist do reutilizável e criar o overlay na #92.
`management-app:unpublished` também permanece fora da allowlist até existir uma
imagem publicada e um contrato de atualização definido.

## Credenciais e aprovação humana

Crie um GitHub App instalado **somente no APAE-INFRA**, com estas permissões de
repositório:

| Permissão | Acesso | Uso |
| --- | --- | --- |
| Contents | Read and write | Checkout e escrita na branch do PR. |
| Pull requests | Read and write | Criar e atualizar o PR. |
| Metadata | Read | Permissão implícita do GitHub App. |

Não são necessárias permissões de administração, Actions, packages nem acesso
ao Kubernetes. O token de instalação é gerado com escopo explícito para
`IFPBEsp/APAE-INFRA` e essas duas permissões de escrita; a action revoga o token
ao terminar o job. A chave privada permanece em secrets, e o checkout usa
`persist-credentials: false`. As actions são fixadas por SHA.

| Secret do reutilizável | Conteúdo | Secret usado pelo dispatcher no APAE-INFRA |
| --- | --- | --- |
| `IMAGE_UPDATER_APP_ID` | ID do GitHub App. | `IMAGE_UPDATER_APP_ID` |
| `IMAGE_UPDATER_APP_PRIVATE_KEY` | Chave privada PEM do GitHub App. | `IMAGE_UPDATER_APP_PRIVATE_KEY` |

Configure a proteção/ruleset de `main` para exigir revisão humana e checks
obrigatórios, invalidar aprovações após novos commits e impedir bypass pelo App.
O workflow abre PRs e não habilita auto-merge. A credencial tem escrita em nível
de repositório; a proteção de `main` é o controle que impede escrita direta.
Após revisão e merge, o sync das Applications filhas no ArgoCD continua manual,
conforme a política atual.

## Integração direta após o publish

Os repositórios de produtos possuem `UPDATER_IMAGE_DISPATCH_TOKEN`; para usar
essa credencial existente, siga a integração por `repository_dispatch` da seção
seguinte. A chamada direta abaixo é uma alternativa que exige disponibilizar
também os secrets do App no repositório chamador.

Nos repositórios de aplicação (#44), encadeie o novo job ao reusable de publicação.
Este exemplo para o backend do APAE usa os outputs já existentes da #35:

```yaml
name: Publish backend and propose GitOps update

on:
  push:
    branches: [dev]

permissions:
  contents: read
  packages: write

jobs:
  publish:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@<commit-sha>
    with:
      context: .
      dockerfile: Dockerfile
      image-name: apae-geral-backend

  update-overlay:
    needs: publish
    uses: IFPBEsp/APAE-INFRA/.github/workflows/update-image-overlay-reusable.yml@<commit-sha>
    with:
      application: apae-geral
      environment: dev
      image: ${{ needs.publish.outputs.image }}
      image-tag: ${{ needs.publish.outputs.sha-tag }}
      image-digest: ${{ needs.publish.outputs.digest }}
      source-repository: ${{ github.repository }}
      source-commit: ${{ github.sha }}
    secrets:
      IMAGE_UPDATER_APP_ID: ${{ secrets.IMAGE_UPDATER_APP_ID }}
      IMAGE_UPDATER_APP_PRIVATE_KEY: ${{ secrets.IMAGE_UPDATER_APP_PRIVATE_KEY }}
```

Substitua `<commit-sha>` pelo SHA completo aprovado no APAE-INFRA e ajuste contexto
e Dockerfile ao serviço. O `needs` impede a atualização quando a publicação
falhar ou for ignorada. Para cada imagem, use os outputs do respectivo job de
publicação; não reconstrua tag nem digest no consumidor.

Na chamada direta, os secrets do App precisam estar disponíveis no repositório
chamador. A identidade `github.repository` deve coincidir com `source-repository`.
O `GITHUB_TOKEN` do consumidor não substitui a credencial de escrita no APAE-INFRA.

## Integração por repository_dispatch

Para manter a chave privada do App de PRs somente no APAE-INFRA, use o workflow
`update-image-overlay-dispatch.yml`. Ele recebe `gitops-image-published` e delega
toda a validação ao reutilizável. O dispatcher deve estar na branch padrão do
APAE-INFRA para receber eventos.

No consumidor, em vez de chamar diretamente o reutilizável, use este job após
`publish`:

```yaml
  notify-infra:
    needs: publish
    runs-on: ubuntu-latest
    permissions: {}
    steps:
      - name: Notify APAE-INFRA
        env:
          GH_TOKEN: ${{ secrets.UPDATER_IMAGE_DISPATCH_TOKEN }}
          IMAGE: ${{ needs.publish.outputs.image }}
          IMAGE_TAG: ${{ needs.publish.outputs.sha-tag }}
          IMAGE_DIGEST: ${{ needs.publish.outputs.digest }}
          SOURCE_REPOSITORY: ${{ github.repository }}
          SOURCE_COMMIT: ${{ github.sha }}
        run: |
          set -euo pipefail
          jq -n \
            --arg image "$IMAGE" \
            --arg tag "$IMAGE_TAG" \
            --arg digest "$IMAGE_DIGEST" \
            --arg repository "$SOURCE_REPOSITORY" \
            --arg commit "$SOURCE_COMMIT" \
            '{event_type: "gitops-image-published", client_payload: {
              application: "apae-geral", environment: "dev", image: $image,
              image_tag: $tag, image_digest: $digest,
              source_repository: $repository, source_commit: $commit
            }}' > "$RUNNER_TEMP/gitops-dispatch.json"
          gh api --method POST repos/IFPBEsp/APAE-INFRA/dispatches \
            --input "$RUNNER_TEMP/gitops-dispatch.json"
```

`UPDATER_IMAGE_DISPATCH_TOKEN` pode ser um fine-grained PAT restrito ao APAE-INFRA com
`Contents: write`, exigido pelo endpoint de dispatch, com expiração e rotação.
Outra opção é um token de instalação de um App remetente separado, instalado
somente no APAE-INFRA, também com `Contents: write`. Não conceda `Pull requests:
write` ao remetente. O App que abre PRs fica separado e sua chave não é enviada
ao consumidor. A proteção de `main` também deve impedir bypass pelo remetente.

No payload, `environment` é opcional e assume `dev`. Os outros campos são
obrigatórios. A API aceitar o evento não significa que a atualização foi
concluída: acompanhe o run no APAE-INFRA e o PR resultante.

Os campos de origem do dispatch são declarações de quem possui a credencial.
A allowlist verifica a combinação, mas não autentica o repositório remetente
por meio desses campos nem comprova a publicação no GHCR. Envie o evento apenas
de pipelines confiáveis após o publish. A verificação de assinatura/proveniência
da imagem permanece na #64; a validação local confirma formato e consistência
entre tag e SHA.

## Validação e aceite operacional

Execute localmente, com Python, PyYAML 6.0.3, kubectl e actionlint disponíveis:

```bash
python3 -m unittest discover -s tests -v
actionlint .github/workflows/update-image-overlay-reusable.yml \
  .github/workflows/update-image-overlay-dispatch.yml \
  .github/workflows/gitops-workflows-test.yml
```

Os testes executam os scripts do próprio workflow em overlays temporários,
incluindo a renderização real do Kustomize, atualização de digest, alias,
idempotência, preservação de outras imagens e rejeição de payloads inválidos.
O workflow `gitops-workflows-test.yml` executa os testes em PRs que alteram essa
implementação.

O aceite com uma imagem real exige os overlays da #92 em `main`, as credenciais
configuradas e a integração do consumidor. Publique uma imagem, confirme que o
PR contém o digest e o link do commit correto e repita a notificação para
verificar que o mesmo PR é atualizado. Após merge, repetir o mesmo digest não
deve abrir novo PR. Uma publicação com falha não deve disparar atualização.
Registre os links do run de publicação, do run GitOps e do PR na issue #82.

## Referências

- [Contrato do fluxo GitOps](../argocd/fluxo-argocd.md)
- [Comunicação entre repositórios](../fluxo-comunicacao-repositorios.md)
- [GitHub: eventos repository_dispatch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch)
- [GitHub: criação de repository_dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [GitHub App token](https://github.com/actions/create-github-app-token)
- [Criação e atualização de PRs](https://github.com/peter-evans/create-pull-request)
