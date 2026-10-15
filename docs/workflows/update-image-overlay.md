# Atualização de imagens nos overlays GitOps

## Arquitetura e decisões

A integração recomendada da issue #82 é `repository_dispatch`. Depois de um
publish bem-sucedido, o produto envia `gitops-image-published` ao APAE-INFRA.
O dispatcher valida o payload e chama internamente
`update-image-overlay-reusable.yml`, que valida as combinações autorizadas,
consulta o GHCR e propõe um PR para `main`.

O reutilizável exige execução no próprio `IFPBEsp/APAE-INFRA`: chamadas vindas
de outro repositório são rejeitadas. A chave privada do App de PRs fica
**exclusivamente no APAE-INFRA**, sem distribuição aos produtos.
Não há ArgoCD Image Updater instalado no cluster.

Apenas overlays de `dev` são atualizados, sempre por digest
`image@sha256:<digest>`. O ambiente `dev` não determina a branch Git: a base dos
PRs continua sendo `main`. Tag `sha-*`, commit, produto e run são registrados
no PR, seguindo a [política de imagens](../boas-praticas/16-politica-tags-imagens-docker.md).
Não há auto-merge nem promoção para `hml` ou `prod`. Revisão humana é obrigatória;
após o merge, o sync no ArgoCD continua manual.

## Validações antes da escrita

1. O dispatcher exige um objeto JSON com os campos obrigatórios, todos strings
   não vazias de até 255 caracteres e sem quebras de linha. Campos desconhecidos
   são rejeitados. `environment` assume `dev` **somente quando ausente**; valores
   como `null`, `false`, `0`, vazio, `hml` e `prod` são rejeitados.
2. O reutilizável verifica ambiente, formatos, allowlist exata de repositório,
   aplicação e imagem, e se a tag é um prefixo do SHA completo informado.
   Inputs são tratados como dados, via variáveis de ambiente, sem interpolação
   em comandos. Os caminhos são definidos por uma tabela interna; não existe
   input para informar caminho arbitrário.
3. Consulta o GHCR para verificar existência da tag e correspondência do digest.
   Uma falha impede até a geração do token de escrita do App.
4. Após checkout de `main`, exige o overlay existente e renderizável. Só então
   edita seu `kustomization.yaml`, renderiza novamente e verifica o resultado.

A edição usa PyYAML 6.0.3 como equivalente a `kustomize edit set image`: altera
somente a lista `images`, remove `newTag`, grava `digest` e preserva `newName`
quando houver alias. A operação falha se a imagem não existir nos workloads,
se houver regras ambíguas ou se outras imagens forem alteradas. A formatação
YAML pode ser normalizada e comentários podem ser removidos; demais propriedades
são preservadas. Somente o arquivo do overlay entra no commit.

A branch é estável por aplicação, ambiente e imagem, por exemplo:
`gitops/apae-geral/dev/apae-geral-backend`. Novas notificações da mesma imagem
atualizam o mesmo PR aberto. Backend e frontend usam branches separadas.
Se o digest já estiver em `main`, não é necessário novo PR.

A concorrência serializa execuções da mesma imagem, sem cancelar o job em
andamento. Envie eventos na ordem de publicação: o workflow não ordena commits
cronologicamente. PRs de imagens diferentes podem alterar o mesmo arquivo;
resolva conflitos e reexecute checks antes do merge.

## Conferência do GHCR e imagens privadas

A consulta usa HTTPS nos endpoints fixos `ghcr.io/token` e
`ghcr.io/v2/<imagem>/manifests/<tag>`, com escopo de token `repository:<imagem>:pull`.
São aceitos manifests e índices OCI, além de Docker schema 2 e manifest lists.
O SHA-256 é calculado sobre os **bytes originais** recebidos para a tag; o
cabeçalho `Docker-Content-Digest`, quando presente, também deve corresponder.

Para multiarch, compara o digest do índice/lista completo apontado pela tag,
sem selecionar uma arquitetura nem comparar apenas um manifest filho. Passe
sempre `publish.outputs.digest`, o digest final exposto pelo workflow da #35.

A consulta tenta acesso anônimo primeiro. Se o GHCR retornar `401` ou `403`,
tenta autenticação de leitura. Tag inexistente, falha HTTP, timeout, resposta
inválida ou digest divergente interrompem a execução. Há limites de tamanho e
timeout, redirects são recusados e corpos, headers de autenticação e tokens
não são registrados nos logs. Não é feito `docker login` nem gravado arquivo
local de credenciais.

Por padrão, o retry autenticado usa `github.actor` e o `GITHUB_TOKEN` do
APAE-INFRA, com `packages: read`. Para imagens privadas, conceda explicitamente
acesso de leitura ao APAE-INFRA nas configurações de Actions de cada package.
O token de instalação do App que abre PRs **não** é usado para acessar packages.

Se esse acesso não for possível, configure no APAE-INFRA ambos os secrets
opcionais abaixo. Informar apenas um é erro, mesmo se a imagem for pública.

| Secret | Uso |
| --- | --- |
| `GHCR_READ_USERNAME` | Usuário proprietário da credencial de leitura. |
| `GHCR_READ_TOKEN` | PAT classic com somente `read:packages`, de conta com acesso aos packages necessários; autorizar SSO quando exigido. |

O PAT de packages é separado tanto do App de PRs quanto do token de dispatch.
Seu alcance depende dos packages acessíveis à conta; prefira `GITHUB_TOKEN`
com concessões explícitas por package. Não conceda escrita ou exclusão de packages.

**Limite de confiança:** existência da tag e correspondência do digest não
comprovam quem produziu a imagem, se o commit declarado originou o build ou
se o pipeline era confiável. `source_repository`, `source_commit` e a tag são
declarações do remetente; a consistência entre eles não é prova de proveniência.
A assinatura/verificação com Cosign depende da #64 e não é presumida disponível.
A revisão humana do PR permanece obrigatória.

## Kustomize reproduzível

O workflow principal e o de testes usam a mesma action local
`.github/actions/setup-kustomize/action.yml`, que instala **Kustomize v5.8.1**
Linux x86_64 e verifica o SHA-256 do arquivo oficial:

```text
029a7f0f4e1932c52a0476cf02a0fd855c0bb85694b82c338fc648dcb53a819d
```

O checksum foi conferido no `checksums.txt` da release oficial. Ambos executam
em `ubuntu-24.04` e usam `kustomize build`, independentemente da versão de
`kubectl` fornecida pelo runner. Os testes conferem a versão instalada antes
de executar os casos. Uma atualização da ferramenta deve alterar a versão e
o checksum nessa action e passar novamente pela suíte e revisão do PR.

## Inputs e outputs

Todos os inputs do reutilizável são strings. No dispatch, os nomes separados
por hífen são enviados com underscore, conforme o exemplo de integração.

| Input | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- |
| `image` | Sim | — | Nome GHCR completo, sem tag/digest, presente na allowlist. |
| `image-tag` | Sim | — | `sha-` e 7 a 40 caracteres hexadecimais, prefixo de `source-commit`. |
| `image-digest` | Sim | — | Digest final: `sha256:` e 64 caracteres hexadecimais. |
| `application` | Sim | — | Identificador da aplicação da tabela abaixo. |
| `environment` | Não | `dev` | Somente `dev` é aceito. |
| `source-repository` | Sim | — | Repositório declarado no formato `IFPBEsp/nome`. |
| `source-commit` | Sim | — | SHA completo de 40 caracteres do build declarado. |

| Output | Descrição |
| --- | --- |
| `pull-request-url` | URL do PR criado/atualizado; pode ser vazio quando não há diferença. |

## Aplicações e dependência da #92

Todas as imagens abaixo têm prefixo `ghcr.io/ifpbesp/`.

| Repositório declarado | `application` | Imagens autorizadas | Overlay |
| --- | --- | --- | --- |
| `IFPBEsp/APAE` | `apae-geral` | `apae-geral-backend`, `apae-geral-frontend` | `kubernetes/overlays/dev/apae` |
| `IFPBEsp/APAE-atendimento` | `apae-atendimento` | `apae-atendimento-backend`, `apae-atendimento-frontend` | `kubernetes/overlays/dev/apae-atendimento` |
| `IFPBEsp/APAE-gestao-escolar` | `apae-gestao-escolar` | `apae-gestao-escolar-backend`, `apae-gestao-escolar-frontend` | `kubernetes/overlays/dev/apae-gestao-escolar` |
| `IFPBEsp/apae-site-comemorativo` | `site-comemorativo` | `apae-site-comemorativo` | `kubernetes/overlays/dev/apae-site-comemorativo` |

Os nomes de Gestão Escolar foram confirmados no
[workflow do produto](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/dev/.github/workflows/docker-publish.yml)
(blob `5531a48f9aa138ffaec03635b01578801fde5d4d`, consultado em 15/10/2026).
O workflow consultado publica somente `latest`. A allowlist aceita as duas
imagens, mas o fluxo só poderá ser usado após a adoção de publicação com tags
`sha-*`, digest final e notificação ao APAE-INFRA (#44). `latest` continua
proibida como input deste fluxo.

Overlays e Applications dependem da #92 e precisam existir em `main`. Esta issue
não cria overlays definitivos, não altera bases e não acessa o cluster. Os
caminhos seguem o [contrato do ArgoCD](../argocd/fluxo-argocd.md).
`management-app:unpublished` permanece fora da allowlist enquanto não houver
contrato de publicação definido.

## Credenciais, permissões e revisão humana

Use um GitHub App instalado **somente no APAE-INFRA**:

| Permissão do App de PRs | Acesso | Uso |
| --- | --- | --- |
| Contents | Read and write | Checkout e branch do PR. |
| Pull requests | Read and write | Criar/atualizar PR. |
| Metadata | Read | Permissão implícita. |

| Secret exclusivo do APAE-INFRA | Conteúdo |
| --- | --- |
| `IMAGE_UPDATER_APP_ID` | ID do App de PRs. |
| `IMAGE_UPDATER_APP_PRIVATE_KEY` | Chave PEM do App de PRs. |

O token de instalação solicita explicitamente somente esse repositório e as
permissões de escrita acima. A action revoga o token ao terminar o job; o
checkout não persiste credenciais. Actions externas são fixadas por SHA.
O App não precisa de administração, Actions, packages ou acesso ao cluster.
A permissão `packages: read` do job pertence ao `GITHUB_TOKEN`, para consulta
privada ao GHCR, e não amplia o App.

Nos produtos, mantenha `UPDATER_IMAGE_DISPATCH_TOKEN` separado das credenciais
acima. O endpoint de dispatch exige `Contents: write` no APAE-INFRA: um
fine-grained PAT deve selecionar **somente o APAE-INFRA**, ter expiração curta,
rotação e um proprietário com o menor acesso necessário. Não conceda `Pull
requests: write`. Alternativamente, use token temporário de um App remetente
separado e restrito ao mesmo repositório, com `Contents: write`.

**Risco do token de dispatch:** `Contents: write` também permite escrever
conteúdo no repositório; não existe uma permissão isolada de “apenas enviar
repository_dispatch”. O código do dispatcher não restringe o que alguém pode
fazer diretamente com essa credencial. Proteja `main`, `dev` e demais branches
sensíveis com rulesets, sem bypass para o remetente ou App de PRs. A política de
branches deve exigir revisão humana, checks obrigatórios e invalidar aprovações
após novos commits. Limite onde o secret é disponibilizado, não o use em código
de PRs não confiáveis e revogue-o se houver exposição. Essas proteções são
configurações administrativas externas ao workflow.

`source_repository` é uma declaração, não uma prova de identidade. Nem a
allowlist nem `github.event.sender` comprovam o repositório que produziu a
imagem. Somente pipelines confiáveis devem possuir a credencial de dispatch.
O workflow não habilita auto-merge e não faz push na branch de destino.

## Integração recomendada após o publish

Nos produtos (#44), use os outputs do workflow da #35. O exemplo completo abaixo
é para o backend do APAE; adapte aplicação, contexto e Dockerfile para o serviço.
Substitua `<commit-sha>` pelo SHA completo aprovado no APAE-INFRA. O dispatcher
deve estar na branch padrão para receber eventos; o código e os assets de
execução também precisam estar em `main`, fonte dos manifests e destino dos PRs.

```yaml
name: Publish backend and notify GitOps

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

  notify-infra:
    needs: publish
    runs-on: ubuntu-24.04
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

`needs: publish` impede notificações se a publicação falhar ou for ignorada.
Para cada imagem, encaminhe os outputs do respectivo job; não reconstrua digest
ou tag. A API aceitar o evento não comprova sucesso da atualização: acompanhe
o run do APAE-INFRA e o PR resultante.

## Testes e aceite operacional

Com Python, PyYAML 6.0.3, **Kustomize v5.8.1** no `PATH` e actionlint:

```bash
python3 -B -m unittest discover -s tests -v
actionlint .github/workflows/update-image-overlay-reusable.yml \
  .github/workflows/update-image-overlay-dispatch.yml \
  .github/workflows/gitops-workflows-test.yml
```

A suíte executa o código do próprio workflow. Consultas ao GHCR usam mocks,
sem credenciais reais, acesso ao registro ou criação de PRs. Casos cobertos:

- Tag inexistente, digest divergente, falhas HTTP/rede/timeout e respostas inválidas.
- OCI/Docker, manifest/índice multiarch e rejeição de digest de manifest filho.
- Imagens privadas, sucesso/falha de autenticação, escopo somente pull,
  bloqueio de redirects e ausência de credenciais nos logs.
- Payloads inválidos, valores falsos de ambiente, campos extras e quebras de linha.
- Allowlist incluindo Gestão Escolar, rejeição de `hml`/`prod` e caminhos arbitrários.
- Overlay inexistente, erro de renderização, alias, idempotência e preservação
  das imagens de outros serviços.

`gitops-workflows-test.yml` roda essa suíte em PRs, com o mesmo instalador de
Kustomize do fluxo principal e apenas `contents: read`. Não usa secrets de
escrita nem packages reais. A instalação da ferramenta e do PyYAML exige rede;
os testes de registro não dependem de serviços externos.

As evidências anteriores do PR #97 registram testes automatizados, autenticação
real do App, rejeição de `prod` e falha esperada por overlay ausente. Essas
execuções antecedem a nova validação do GHCR: os testes de `dev` com dados
fictícios agora devem parar na consulta ao registro, antes do checkout.
Para testar ausência de overlay ao vivo, forneça uma tag e digest reais válidos.

Ainda dependem da integração completa: leitura de packages privados com as
permissões reais, overlays da #92 em `main`, geração de PR após publicação real,
repetição da notificação para atualizar o mesmo PR e repetição após merge sem
novo PR. Registre os links do run de publicação, run GitOps e PR na #82. Mantenha
a issue aberta até concluir o aceite com imagem real; autenticação isolada e
mocks não substituem esse teste.

## Referências

- [Fluxo do ArgoCD](../argocd/fluxo-argocd.md)
- [Comunicação entre repositórios](../fluxo-comunicacao-repositorios.md)
- [Container Registry e autenticação](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Registry HTTP API V2 e digests](https://distribution.github.io/distribution/spec/api/)
- [Kustomize v5.8.1 e checksums oficiais](https://github.com/kubernetes-sigs/kustomize/releases/tag/kustomize/v5.8.1)
- [Eventos repository_dispatch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch)
- [Permissão do endpoint de dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
