# Atualização de imagens nos overlays GitOps

## Arquitetura e decisões

A integração recomendada da issue #82 é `repository_dispatch`. Depois de um
publish bem-sucedido, o produto envia `gitops-image-published` ao APAE-INFRA.
O dispatcher valida o payload e chama internamente
`update-image-overlay-reusable.yml`, que valida as combinações autorizadas,
consulta o GHCR e propõe um PR para `main`.

O reutilizável exige execução no próprio `IFPBEsp/APAE-INFRA`: chamadas vindas
de outro repositório são rejeitadas. A chave privada do App de PRs fica
**exclusivamente no environment `gitops-image-updater` do APAE-INFRA**,
restrito à branch `dev`, sem distribuição aos produtos ou acesso por PRs.
Não há ArgoCD Image Updater instalado no cluster.

Apenas overlays de `dev` (homologação) são atualizados, sempre por digest
`image@sha256:<digest>`. O ambiente `dev` não determina a branch Git: a base dos
PRs continua sendo `main`. Tag `sha-*`, commit, produto e run são registrados
no PR, seguindo a [política de imagens](../boas-praticas/16-politica-tags-imagens-docker.md).
Não há auto-merge nem promoção para `hml` ou `prod`. Revisão humana é obrigatória;
após o merge, o sync no ArgoCD continua manual.

O PR #97 implementa somente o receptor GitOps. A #106 implementará a integração
dos produtos após publicação na `main`, a comprovação de proveniência e a
promoção da combinação de digests validada de `dev` para `prod`, sem novo build.
O receptor atual rejeita `hml` e `prod`; não será criado um ambiente `hml`.

**Dependência de sincronização:** o PR #120 declara `automated`, `prune` e
`selfHeal` nas Applications `dev`. Isso diverge do sync manual requerido para
homologação neste fluxo. A política deve ser alinhada com #92/#106 antes da
ativação operacional; este PR não modifica as Applications ou o bootstrap.

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

Os checkouts são separados: a raiz contém a automação na revisão da execução
(`github.sha`, compartilhada pelo dispatcher e sua chamada local ao reutilizável),
obtida com `GITHUB_TOKEN` de leitura e sem persistir credenciais. A `main` é
obtida em `infra/`, com o token do App e também sem persistir credenciais.
A action local do Kustomize é carregada da raiz; ela não precisa existir na `main`.
Resolução e edição dos overlays usam `working-directory: infra`. A criação do PR
usa `path: infra`, com `add-paths` relativo a esse checkout e limitado ao
`kustomization.yaml` autorizado. Os caminhos lógicos da tabela abaixo não mudam.

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
| `IFPBEsp/APAE` | `apae-geral` | `apae-geral-backend`, `apae-geral-frontend` | `kubernetes/apae-geral/overlays/dev` |
| `IFPBEsp/APAE-atendimento` | `apae-atendimento` | `apae-atendimento-backend`, `apae-atendimento-frontend` | `kubernetes/apae-atendimento/overlays/dev` |
| `IFPBEsp/APAE-gestao-escolar` | `apae-gestao-escolar` | `apae-gestao-escolar-backend`, `apae-gestao-escolar-frontend` | `Pendente de #38/#92; sem caminho definido` |
| `IFPBEsp/apae-site-comemorativo` | `site-comemorativo` | `apae-site-comemorativo` | `kubernetes/site-comemorativo/overlays/dev` |

Os três caminhos implementados foram conferidos no [PR #120](https://github.com/IFPBEsp/APAE-INFRA/pull/120)
(commit `0de829b6f8e11cfe391a077cfc7f30126311e953`). Gestão Escolar ainda não
possui base/overlay definido nesse PR e depende da #38 e da #92. Suas imagens
continuam na allowlist do contrato, mas a resolução do overlay falha
explicitamente até que o caminho seja definido e revisado; não há fallback.

Os nomes de Gestão Escolar foram confirmados no
[workflow do produto](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/dev/.github/workflows/docker-publish.yml)
(blob `5c4f627d797d60083bfa971fc6813f8a270bbd4f`, consultado em 02/11/2026).
O produto já publica backend e frontend pelo `docker-build-publish-image.yml`
da #35, com tags `sha-*` e digest final. Falta adicionar a notificação ao
APAE-INFRA nos produtos, integração já contemplada na
[#106](https://github.com/IFPBEsp/APAE-INFRA/issues/106). A #44 foi encerrada e
não cobre essa integração.
`latest` continua proibida como input deste fluxo.

Overlays e Applications dependem da #92 e precisam existir em `main`. Esta issue
não cria overlays definitivos, não altera bases e não acessa o cluster. Os
caminhos seguem o [contrato do ArgoCD](../argocd/fluxo-argocd.md).
`management-app:unpublished` permanece fora da allowlist enquanto não houver
contrato de publicação definido.

## Digest e proveniência: limites e integração com a #106

A conferência do GHCR comprova que a tag consultada aponta para os bytes do
manifest/índice cujo digest foi informado. Ela não comprova que a imagem foi
construída por um workflow autorizado ou por um commit da `main` do produto.
`source_repository` e `source_commit` são declarações recebidas no payload,
não evidências criptográficas de origem.

Na #106, inserir a verificação de proveniência após `Verify published image in
GHCR` (`registry`) e antes de `Generate GitHub App token` (`app-token`). O checkout
intermediário da automação usa apenas o `GITHUB_TOKEN` de leitura. A nova
verificação deverá falhar antes de gerar o token de escrita, obter os manifests
com ele ou criar branches/PRs. Esse ponto está indicado no YAML; não existe
uma etapa fictícia de aprovação de proveniência no receptor atual.

A escolha e validação operacional do mecanismo (por exemplo, Cosign ou GitHub
Attestations) pertencem à #106 e ainda não foram realizadas por este PR.

## Credenciais, permissões e revisão humana

Use um GitHub App instalado **somente no APAE-INFRA**:

| Permissão do App de PRs | Acesso | Uso |
| --- | --- | --- |
| Contents | Read and write | Checkout e branch do PR. |
| Pull requests | Read and write | Criar/atualizar PR. |
| Metadata | Read | Permissão implícita. |

| Secret do environment `gitops-image-updater` no APAE-INFRA | Conteúdo |
| --- | --- |
| `IMAGE_UPDATER_APP_ID` | ID do App de PRs. |
| `IMAGE_UPDATER_APP_PRIVATE_KEY` | Chave PEM do App de PRs. |

Antes de habilitar o fluxo, configure em **Settings → Environments** o
environment `gitops-image-updater`. Em **Deployment branches and tags**, use
**Selected branches and tags** e permita somente a branch `dev`, sem regras
para tags. O `repository_dispatch` executa na branch padrão `dev`; isso não
altera a base `main` dos PRs de manifests. Chamadas pela branch de um PR não
devem conseguir acessar esse environment.

Recadastre os dois secrets acima no environment e remova as cópias de
**Repository secrets** e qualquer concessão equivalente por **Organization
secrets**. Somente declarar `environment` no YAML não protege cópias que
continuem disponíveis em outros escopos. O GitHub não permite recuperar os
valores existentes: use os valores originais ou substitua a chave do App.
Não envie valores de secrets em issues, comentários ou logs.

O job do reutilizável declara o environment fixo e lê suas credenciais
diretamente de `secrets`; as declarações opcionais em `workflow_call` documentam
os nomes para validação estática, sem exigir envio pelo caller. O dispatcher
não repassa essas credenciais. As regras do environment e a migração dos secrets
são configurações administrativas, externas ao código deste PR.
Confira manualmente no GitHub a regra exata de branch `dev` (sem tags), os dois
nomes em **Environment secrets**, a ausência de cópias acessíveis em outros
escopos e a instalação do App somente no APAE-INFRA com as permissões abaixo.
Os testes locais não validam essas configurações nem o conteúdo dos secrets.

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

Nos produtos, a adoção do dispatch deve ser acompanhada pela
[#106](https://github.com/IFPBEsp/APAE-INFRA/issues/106); use os outputs do
workflow da #35. O exemplo completo abaixo
é para o backend do APAE; adapte aplicação, contexto e Dockerfile para o serviço.
Substitua `<commit-sha>` pelo SHA completo aprovado no APAE-INFRA. O dispatcher
deve estar na branch padrão para receber eventos. O código e a action local
precisam existir na revisão executada pelo dispatcher; somente os manifests
precisam estar em `main`, destino dos PRs.

```yaml
name: Publish backend and notify GitOps

on:
  push:
    branches: [main]

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
- Resolução dos três caminhos definidos no PR #120 e falha explícita para
  Gestão Escolar enquanto seu overlay não estiver definido (#38/#92).
- Token do App restrito ao APAE-INFRA, com escrita apenas em contents e PRs,
  gerado depois da consulta ao GHCR.
- Overlay inexistente, erro de renderização, alias, idempotência e preservação
  das imagens de outros serviços.
- Isolamento dos checkouts, acesso à action local sem ela existir na `main` e
  caminhos da atualização e do PR limitados ao overlay em `infra/`.

`gitops-workflows-test.yml` roda essa suíte em PRs, com o mesmo instalador de
Kustomize do fluxo principal e apenas `contents: read`. Não usa secrets de
escrita nem packages reais. A instalação da ferramenta e do PyYAML exige rede;
os testes de registro não dependem de serviços externos.

As evidências anteriores do PR #97 registram testes automatizados, autenticação
real do App, rejeição de `prod` e falha esperada por overlay ausente. Essas
execuções antecedem a nova validação do GHCR: os testes de `dev` com dados
fictícios agora devem parar na consulta ao registro, antes do checkout.
Para testar ausência de overlay ao vivo, forneça uma tag e digest reais válidos.

A #82 permanece aberta até concluir os testes operacionais com imagens reais.
Ainda dependem da integração completa: leitura de packages privados com as
permissões reais, overlays da #92/PR #120 em `main`, base/overlay de Gestão Escolar (#38),
alinhamento da política de sync manual e integração dos produtos pela #106,
geração de PR após publicação real,
repetição da notificação para atualizar o mesmo PR e repetição após merge sem
novo PR. Registre os links do run de publicação, run GitOps e PR na #82. Mantenha
a issue aberta até concluir o aceite com imagem real; autenticação isolada e
mocks não substituem esse teste.

O PR #97 deve manter apenas uma referência informativa à #82, sem vínculo de
fechamento em **Development** e sem palavras-chave de fechamento na descrição.
Remova o vínculo antes do merge em `dev`, para que a #82 permaneça aberta
durante o aceite operacional.

## Referências

- [Fluxo do ArgoCD](../argocd/fluxo-argocd.md)
- [Comunicação entre repositórios](../fluxo-comunicacao-repositorios.md)
- [Container Registry e autenticação](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Registry HTTP API V2 e digests](https://distribution.github.io/distribution/spec/api/)
- [Kustomize v5.8.1 e checksums oficiais](https://github.com/kubernetes-sigs/kustomize/releases/tag/kustomize/v5.8.1)
- [Eventos repository_dispatch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch)
- [Permissão do endpoint de dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
