# Atualização de imagens nos overlays GitOps

## Arquitetura e decisões

Após publicar imagens a partir da `main`, o produto envia um
`repository_dispatch` ao APAE-INFRA. O Site envia `gitops-image-published`
com uma imagem. Geral, Atendimento e Gestão Escolar enviam
`gitops-release-published` com o frontend e o backend da mesma execução.
O dispatcher chama `update-image-overlay-reusable.yml`, que valida os digests
e propõe um PR para `main` com o overlay de homologação e o registro candidato.

O reutilizável só executa no próprio `IFPBEsp/APAE-INFRA`, na branch padrão
(`dev` atualmente). A chave do App de PRs fica no environment
`gitops-image-updater`, com acesso limitado à branch `dev`. O ArgoCD acompanha
os manifests da `main` e o sync é manual. O [fluxo de releases](releases-gitops.md)
descreve a aprovação e a promoção dos mesmos digests para produção.

## Validações antes da escrita

1. O dispatcher valida o formato de cada evento e rejeita campos extras.
   No evento do Site, `environment` assume `dev` somente quando ausente;
   valores como `null`, `false`, `0`, vazio, `hml` e `prod` são rejeitados.
   No evento combinado, os dois componentes são obrigatórios.
2. O reutilizável verifica ambiente, formatos, allowlist exata de repositório,
   aplicação e imagem, e se a tag é um prefixo do SHA completo informado.
   Inputs são tratados como dados, via variáveis de ambiente, sem interpolação
   em comandos. Os caminhos são definidos por uma tabela interna; não existe
   input para informar caminho arbitrário.
3. Confere se o commit informado é o HEAD atual da `main` do produto.
4. Consulta o GHCR para verificar existência da tag e correspondência do digest
   e autentica a proveniência com GitHub Attestations para o repositório,
   workflow de publicação, ref `refs/heads/main` e commit declarados. Também
   verifica a assinatura Cosign. Para uma release combinada, os dois digests
   devem pertencer à mesma execução autenticada. Uma falha impede a geração
   do token de escrita do App.
5. Após checkout de `main`, exige o overlay existente e renderizável. Só então
   edita seu `kustomization.yaml`, renderiza novamente e verifica o resultado.
6. Antes de abrir ou atualizar o PR, confere novamente o HEAD da `main` do
   produto e rejeita a atualização se o commit já estiver desatualizado.

Os checkouts são separados: a raiz contém a automação na revisão da execução
(`github.sha`, compartilhada pelo dispatcher e sua chamada local ao reutilizável),
obtida com `GITHUB_TOKEN` de leitura e sem persistir credenciais. A `main` é
obtida em `infra/`, com o token do App e também sem persistir credenciais.
A action local do Kustomize é carregada da raiz; ela não precisa existir na `main`.
Resolução e edição dos overlays usam `working-directory: infra`. A criação do PR
usa `path: infra`, com `add-paths` relativo a esse checkout e limitado ao
overlay autorizado e ao registro candidato correspondente.

A edição usa PyYAML 6.0.3 como equivalente a `kustomize edit set image`: altera
somente a lista `images`, remove `newTag`, grava `digest` e preserva `newName`
quando houver alias. A operação falha se a imagem não existir nos workloads,
se houver regras ambíguas ou se outras imagens forem alteradas. A formatação
YAML pode ser normalizada e comentários podem ser removidos; demais propriedades
são preservadas. O commit inclui o overlay e o registro do candidato.

Cada aplicação tem uma branch estável para o PR de homologação. A concorrência
serializa as execuções para a mesma aplicação sem cancelar a que está em
andamento. A validação do HEAD da `main` do produto rejeita eventos atrasados.

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
não são registrados nos logs. A etapa posterior de proveniência usa
`docker/login-action` para autenticar a leitura de attestations no GHCR.

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

**Limite de confiança:** a consulta da tag e do digest, isoladamente, não
comprova quem produziu a imagem. Por isso, antes de gerar o token do App, o
receptor também autentica a proveniência descrita abaixo. A revisão humana
do PR permanece obrigatória.

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

Todos os inputs do reutilizável são strings. Veja os payloads e exemplos de
integração em [Publicação pela main dos produtos](publicacao-main-produtos.md).

| Input | Descrição |
| --- | --- |
| `application`, `source-repository`, `source-commit` | Identificam a aplicação, o repositório e o SHA completo de origem. |
| `environment` | Opcional, com padrão `dev`. Somente `dev` é aceito. |
| `image`, `image-tag`, `image-digest` | Obrigatórios no evento de imagem única do Site. |
| `release-json` | Obrigatório para Geral, Atendimento e Gestão Escolar. Contém frontend e backend e exclui os inputs de imagem única. |

O output `pull-request-url` contém a URL do PR criado ou atualizado. Fica vazio
quando não há diferença.

| Aplicação | Overlay de homologação |
| --- | --- |
| `apae-geral` | `kubernetes/apae-geral/overlays/dev` |
| `apae-atendimento` | `kubernetes/apae-atendimento/overlays/dev` |
| `apae-gestao-escolar` | `kubernetes/gestao-escolar/overlays/dev` |
| `site-comemorativo` | `kubernetes/site-comemorativo/overlays/dev` |

## Digest e proveniência

Após a consulta ao GHCR e antes de gerar o token de escrita do App, a etapa
`Verify image build provenance` executa `gh attestation verify` sobre o digest
OCI. A verificação exige o repositório do produto, o workflow reutilizável
`IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml`, a ref
`refs/heads/main` e o commit completo informado. Falhas interrompem o job antes
do acesso de escrita aos manifests.

O commit também precisa corresponder ao HEAD atual da `main` do produto na
recepção e imediatamente antes da abertura ou atualização do PR. Antes do merge
humano, confirme se a `main` do produto não avançou desde a abertura do PR.
A validação operacional com imagens reais continua necessária na #82/#106.

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
checkout não persiste credenciais. As demais actions externas são fixadas por SHA; `docker/login-action` usa `@v3`.
O App não precisa de administração, Actions, packages ou acesso ao cluster.
A permissão `packages: read` do job pertence ao `GITHUB_TOKEN`, para consulta
privada ao GHCR, e não amplia o App.

Nos produtos, use o App de dispatch separado no environment `gitops-dispatch`.
O App emite tokens temporários com `Contents: write` somente no APAE-INFRA.
Veja os nomes das variáveis e dos secrets no [guia de publicação](publicacao-main-produtos.md).

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

## Integração após a publicação

Os callers dos produtos estão no [Site #72](https://github.com/IFPBEsp/apae-site-comemorativo/pull/72),
[Geral #1097](https://github.com/IFPBEsp/APAE/pull/1097),
[Atendimento #488](https://github.com/IFPBEsp/APAE-atendimento/pull/488) e
[Gestão Escolar #496](https://github.com/IFPBEsp/APAE-gestao-escolar/pull/496).
Para ativar o fluxo, o receptor deve estar em `dev` e os overlays em `main`.

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
- Resolução dos quatro caminhos autorizados e rejeição de overlays ausentes.
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
permissões reais, integração dos produtos pela #106, geração de PR após publicação real,
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
