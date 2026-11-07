# SBOM e atestação de proveniência das imagens Docker

## Objetivo

Este documento descreve como o workflow reutilizável de build e publicação gera, anexa e verifica duas atestações para cada imagem publicada no GHCR:

- **SBOM** (Software Bill of Materials) no formato SPDX JSON, que responde *o que existe dentro da imagem*: pacotes do sistema operacional e bibliotecas da aplicação;
- **proveniência SLSA** (`https://slsa.dev/provenance/v1`), que responde *como a imagem foi construída*: repositório, commit, referência Git, workflow e execução.

A assinatura com Cosign, descrita em [Assinatura e verificação de imagens Docker com Cosign](./cosign-assinatura-imagens.md), continua respondendo *quem publicou a imagem*. As três informações se complementam e são vinculadas ao mesmo digest.

## Visão geral do fluxo

As atestações são geradas no job `publish` do workflow `.github/workflows/docker-build-publish-image.yml`, sobre o digest final do manifest candidato e antes da assinatura Cosign e da promoção das tags:

```text
Create candidate manifest
  ↓
Verify candidate image
  ↓
Attest image build provenance      (actions/attest → SLSA v1)
  ↓
Verify image build provenance      (gh attestation verify)
  ↓
Generate image SBOM                (anchore/sbom-action → Syft, SPDX JSON)
  ↓
Validate image SBOM                (spdxVersion e pacotes presentes)
  ↓
Attest image SBOM                  (actions/attest → SPDX)
  ↓
Verify image SBOM attestation      (gh attestation verify)
  ↓
Sign candidate image with Cosign
  ↓
Verify Cosign signature
  ↓
Promote verified image to final tags
```

O sujeito das duas atestações é sempre a referência imutável:

```text
ghcr.io/<owner>/<image>@sha256:<digest>
```

Como a promoção usa `--prefer-index=false` e confere que o digest promovido é igual ao digest assinado, as tags finais (`sha-<short-sha>`, `latest`) apontam para o mesmo digest que possui SBOM, proveniência e assinatura.

## Ferramentas utilizadas

| Etapa | Ferramenta | Versão fixada |
| --- | --- | --- |
| Geração do SBOM | `anchore/sbom-action` (Syft) | `v0.24.3` por commit SHA; Syft `v1.54.1` |
| Atestação de proveniência e SBOM | `actions/attest` | `v4.2.2` por commit SHA |
| Verificação no pipeline | `gh attestation verify` | GitHub CLI do runner |

As atestações são assinadas com Sigstore usando a identidade OIDC do GitHub Actions (sem chaves de longa duração), registradas na API de attestations do GitHub e enviadas ao GHCR como artefatos OCI vinculados ao digest (`push-to-registry: true`).

O SBOM também é publicado como artefato da execução, com o nome `sbom-<image-name>.spdx.json`, para consulta rápida sem acesso ao registry.

## Permissões

Nenhuma permissão nova foi adicionada. O job `publish` já declarava:

```yaml
permissions:
  contents: read
  packages: write
  id-token: write
  attestations: write
```

- `id-token: write`: obtém o token OIDC usado para assinar as atestações (e a imagem, via Cosign);
- `attestations: write`: grava as atestações na API de attestations do GitHub;
- `packages: write`: envia as atestações ao GHCR junto da imagem;
- `contents: read`: permissão base de leitura do repositório, já existente.

O upload do SBOM como artefato da execução não exige permissão adicional.

O caller precisa conceder as mesmas permissões, pois os jobs do workflow reutilizável não podem ampliar as permissões do workflow que os chama. Os callers dos produtos já concedem `contents: read`, `packages: write`, `id-token: write` e `attestations: write`, conforme [Publicação de imagens a partir da main dos produtos](../workflows/publicacao-main-produtos.md).

## Comportamento em caso de falha

Todas as etapas de atestação fazem parte do caminho obrigatório do job `publish` e nenhuma usa `continue-on-error`. Se qualquer uma falhar, o job falha e as tags finais não são criadas ou atualizadas.

O workflow falha quando:

- o Syft não consegue ler a imagem ou gerar o SBOM;
- o arquivo SBOM está vazio, não possui `spdxVersion` válido ou não lista nenhum pacote;
- a atestação de proveniência ou do SBOM não pode ser assinada, registrada ou enviada ao GHCR;
- `gh attestation verify` não encontra a atestação esperada no GHCR ou a encontra com repositório, workflow assinante, referência Git, commit ou tipo de predicado diferentes do esperado.

Como no fluxo do Cosign, uma falha pode deixar a tag `candidate-<run-id>-<run-attempt>` e eventuais atestações parciais no GHCR. Esses artefatos não devem ser consumidos: a imagem só é considerada aprovada quando possui as tags finais e todas as verificações abaixo passam.

## Como consultar e verificar as atestações

Os comandos abaixo exigem o [GitHub CLI](https://cli.github.com/) autenticado (`gh auth login`) com acesso de leitura aos pacotes da organização. Para imagens privadas, faça também login no GHCR (`echo "$TOKEN" | docker login ghcr.io -u <usuario> --password-stdin`).

Defina as variáveis de acordo com a imagem consultada:

```bash
IMAGE="ghcr.io/ifpbesp/apae-geral-backend"
DIGEST="sha256:<digest>"
SOURCE_REPOSITORY="IFPBEsp/APAE"
SIGNER_WORKFLOW="IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml"
```

`SOURCE_REPOSITORY` é o repositório de produto que publicou a imagem, conforme a tabela de [produtos e imagens](../workflows/publicacao-main-produtos.md#produtos-e-imagens). Não use `IFPBEsp/APAE-INFRA` apenas porque ele hospeda o workflow reutilizável.

Para descobrir o digest a partir de uma tag:

```bash
docker buildx imagetools inspect "${IMAGE}:sha-<short-sha>" --format '{{json .Manifest}}' | jq -r .digest
```

### Verificar a proveniência

```bash
gh attestation verify "oci://${IMAGE}@${DIGEST}" \
  --bundle-from-oci \
  --repo "$SOURCE_REPOSITORY" \
  --signer-workflow "$SIGNER_WORKFLOW" \
  --source-ref "refs/heads/main" \
  --predicate-type "https://slsa.dev/provenance/v1"
```

Para conferir também o commit de origem, acrescente `--source-digest <commit-sha>`.

Para ler os dados de build (repositório, commit, workflow, execução):

```bash
gh attestation verify "oci://${IMAGE}@${DIGEST}" \
  --bundle-from-oci \
  --repo "$SOURCE_REPOSITORY" \
  --signer-workflow "$SIGNER_WORKFLOW" \
  --source-ref "refs/heads/main" \
  --predicate-type "https://slsa.dev/provenance/v1" \
  --format json \
  --jq '.[0].verificationResult.statement.predicate | {
      workflow: .buildDefinition.externalParameters.workflow,
      commit: .buildDefinition.resolvedDependencies[0].digest.gitCommit,
      runner: .runDetails.builder.id,
      run: .runDetails.metadata.invocationId
    }'
```

### Verificar e baixar o SBOM

O Syft gera SBOMs SPDX 2.3, cujo tipo de predicado é `https://spdx.dev/Document/v2.3`:

```bash
gh attestation verify "oci://${IMAGE}@${DIGEST}" \
  --bundle-from-oci \
  --repo "$SOURCE_REPOSITORY" \
  --signer-workflow "$SIGNER_WORKFLOW" \
  --source-ref "refs/heads/main" \
  --predicate-type "https://spdx.dev/Document/v2.3" \
  --format json \
  --jq '.[0].verificationResult.statement.predicate' > sbom.spdx.json
```

O arquivo só é gravado quando a verificação passa, portanto o SBOM obtido dessa forma é o mesmo que foi assinado pelo workflow autorizado para aquele digest.

Se uma versão futura do Syft passar a gerar outra versão do SPDX, o tipo de predicado acompanha o campo `spdxVersion` do documento. O resumo da execução de publicação mostra o tipo exato utilizado.

Alternativamente, o SBOM pode ser baixado como artefato `sbom-<image-name>.spdx.json` na página da execução. Esse arquivo é útil para inspeção, mas não substitui a verificação acima, pois artefatos de execução não são vinculados criptograficamente ao digest.

### Onde mais encontrar as atestações

`gh attestation verify` sempre filtra por tipo de predicado (o padrão é `https://slsa.dev/provenance/v1`), por isso cada atestação é verificada com seu próprio `--predicate-type`.

As atestações também aparecem na aba **Actions → Attestations** do repositório de produto e no resumo da execução de publicação, seção **Attestations**, que traz os links das duas atestações.

## Uso do SBOM na resposta a vulnerabilidades

Quando uma nova vulnerabilidade for divulgada, o SBOM verificado permite descobrir se uma imagem publicada contém o componente afetado sem reconstruí-la.

Procurar um pacote pelo nome:

```bash
jq -r '.packages[]
  | select(.name | test("log4j"; "i"))
  | "\(.name) \(.versionInfo)"' sbom.spdx.json
```

Procurar pelo identificador `purl`:

```bash
jq -r '.packages[].externalRefs[]?
  | select(.referenceType == "purl")
  | .referenceLocator' sbom.spdx.json | grep -i "pkg:maven/org.apache.logging"
```

Executar uma varredura de vulnerabilidades sobre o SBOM, sem baixar a imagem:

```bash
trivy sbom sbom.spdx.json
```

## Limitações conhecidas

- **Plataformas múltiplas:** quando o caller publica mais de uma plataforma, o digest final é um índice OCI. O Syft gera o SBOM da plataforma do runner (`linux/amd64`). Hoje todos os callers publicam apenas `linux/amd64`; se outras plataformas forem adotadas, será necessário gerar um SBOM por plataforma.
- **Precisão do SBOM:** o SBOM reflete o que o Syft consegue identificar nas camadas da imagem. Binários copiados manualmente sem metadados de pacote podem não aparecer.
- **Bloqueio no deploy:** as atestações são verificadas no pipeline de publicação e a proveniência também é verificada pelo receptor que atualiza os overlays ([update-image-overlay](../workflows/update-image-overlay.md)). O cluster ainda não bloqueia imagens sem SBOM ou proveniência; essa política pode ser adotada no futuro com uma admission policy compatível com Sigstore.

## Validação em uma imagem real

Para registrar a validação desta funcionalidade em uma publicação real:

1. Executar o workflow de publicação de um produto (por exemplo, `IFPBEsp/APAE`) apontando para a versão do workflow reutilizável que contém estas etapas.
2. Confirmar no job `Promote approved image` que as etapas `Generate image SBOM`, `Validate image SBOM`, `Attest image SBOM` e `Verify image SBOM attestation` foram concluídas.
3. Executar localmente os comandos de [verificação da proveniência](#verificar-a-proveniência) e de [verificação do SBOM](#verificar-e-baixar-o-sbom) sobre o digest publicado.
4. Registrar neste documento o link da execução, o digest validado e o resultado dos comandos.

Assim como no teste do Cosign, ao apontar o caller para uma branch de feature do `APAE-INFRA`, o `--signer-workflow` continua válido, pois não inclui a referência da branch; a `--source-ref` deve corresponder à branch do produto usada no teste.
