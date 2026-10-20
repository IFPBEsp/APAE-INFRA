# Pipeline reutilizável de build, scan e publicação de imagens Docker

## Objetivo

Esta documentação descreve o workflow reutilizável criado na issue `#35` do repositório `APAE-INFRA` para padronizar o build, a análise de vulnerabilidades, a publicação e a assinatura de imagens Docker no GitHub Container Registry (GHCR).

O workflow foi projetado para ser consumido pelos demais repositórios da organização por meio de `workflow_call`.

Arquivo principal:

```text
.github/workflows/docker-build-publish-image.yml
```

## Escopo

O workflow centraliza as seguintes responsabilidades:

- build de imagens Docker com Buildx;
- suporte a uma ou mais plataformas;
- publicação inicial da imagem por digest;
- scan de vulnerabilidades com Trivy;
- bloqueio da promoção quando forem encontradas vulnerabilidades acima do limite configurado;
- criação das tags finais somente após aprovação do security gate;
- publicação da referência imutável da imagem;
- assinatura keyless do manifest candidato com Cosign e Sigstore;
- verificação da assinatura utilizando identidade OIDC e issuer esperados;
- cache de build com GitHub Actions Cache;
- geração de tags finais conforme a política de versionamento;
- exposição de outputs para workflows consumidores.

A correção de vulnerabilidades encontradas nas aplicações consumidoras não faz parte do escopo deste workflow.

## Arquitetura do fluxo

O fluxo implementado segue esta sequência:

```text
checkout
   ↓
normalização do nome da imagem
   ↓
preparação da plataforma e metadados
   ↓
Docker Buildx
   ↓
login no GHCR
   ↓
build da imagem
   ↓
push por digest
   ↓
scan da referência exata image@sha256:...
   ↓
security gate
   ↓
persistência dos digests aprovados
   ↓
criação do manifest candidato
   ↓
digest OCI final
   ↓
assinatura keyless com Cosign
   ↓
verificação da assinatura
   ↓
promoção para as tags finais
```

A imagem é enviada ao registry antes do scan utilizando apenas seu digest, sem receber as tags finais de publicação.

As tags oficiais são criadas apenas após todas as plataformas configuradas passarem pelo scan e a assinatura do digest final ser verificada.

Antes da promoção, o digest OCI final é assinado e validado com Cosign utilizando identidade OIDC do GitHub Actions.

A assinatura e a verificação são realizadas sobre a referência imutável:

```text
ghcr.io/<owner>/<image>@sha256:<digest>
```

Os detalhes de identidade, issuer, assinatura keyless e verificação estão documentados em:

[Assinatura e verificação de imagens Docker com Cosign](./cosign-assinatura-imagens.md)

## Identidade da imagem

A identidade canônica utilizada para deploy, auditoria e rollback é o digest OCI:

```text
ghcr.io/<owner>/<image>@sha256:<digest>
```

Tags são tratadas como referências humanas e de conveniência.

A política relacionada às tags e ao uso de digest é documentada separadamente em:

[Política de tags de imagens Docker](../boas-praticas/16-politica-tags-imagens-docker.md)

### Tags geradas

O workflow gera:

- `sha-<short-sha>`: gerada para o commit que originou o build;
- `latest`: publicada quando o consumidor executa em `dev`, após verificar a assinatura;
- `dev`: publicada junto com `latest`, após verificar a assinatura, para compatibilidade com os manifests Kubernetes que ainda consomem essa tag.

A tag `vX.Y.Z` não é gerada por este workflow. A publicação de uma release semântica deve reutilizar a imagem já existente e será tratada em um workflow específico de release.

O uso de `latest` ou `dev` para deploy, rollback ou auditoria não é recomendado, sendo a referência canônica o digest OCI imutável.

## Inputs

O workflow recebe os seguintes parâmetros através de `workflow_call`:

| Input | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- |
| `context` | sim | - | Contexto utilizado no build Docker |
| `dockerfile` | sim | - | Caminho do Dockerfile |
| `image-name` | sim | - | Nome da imagem no GHCR, sem registry e owner |
| `build-args` | não | vazio | Build args adicionais, um por linha |
| `platforms` | não | `["linux/amd64"]` | Lista JSON de plataformas |
| `target` | não | vazio | Stage alvo do Dockerfile |
| `scan-severity` | não | `HIGH,CRITICAL` | Severidades que bloqueiam a promoção |

## Outputs

O workflow disponibiliza:

| Output | Descrição |
| --- | --- |
| `image` | Nome completo da imagem no GHCR |
| `digest` | Digest OCI final da imagem promovida |
| `immutable-reference` | Referência imutável `image@sha256:digest` |
| `sha-tag` | Tag baseada no commit |

Esses outputs permitem que outros workflows utilizem diretamente a referência imutável produzida pelo pipeline.

## Build por plataforma

O job `build-and-scan` utiliza uma matrix baseada no input `platforms`.

Exemplo:

```yaml
platforms: '["linux/amd64", "linux/arm64"]'
```

Cada plataforma:

1. é construída separadamente;
2. é publicada por digest;
3. é analisada individualmente pelo Trivy;
4. tem seu digest persistido como artifact nomeado `digest-<image-name>-<platform>` somente se o scan for aprovado.

O isolamento do nome do artifact por `image-name` impede conflitos de upload e colisões no GitHub Actions v4 quando múltiplos jobs do mesmo workflow chamam o reusable em paralelo (por exemplo, `publish-backend` e `publish-frontend`).

Para plataformas diferentes de `linux/amd64`, o workflow configura QEMU automaticamente.

## Publicação por digest

O build utiliza `docker/build-push-action` com:

```yaml
outputs: >-
  type=image,
  name=<imagem>,
  push-by-digest=true,
  name-canonical=true,
  push=true
```

Isso permite publicar o artefato no GHCR sem criar antecipadamente as tags finais.

O digest produzido pelo Buildx é utilizado como referência da etapa de segurança.

## Scan de vulnerabilidades

O scan é executado com Trivy sobre a referência completa da imagem:

```text
ghcr.io/<owner>/<image>@sha256:<digest>
```

Isso garante que o artefato analisado seja exatamente o mesmo que foi produzido pelo build.

Configuração principal:

```yaml
scan-type: image
scanners: vuln
format: table
exit-code: "1"
ignore-unfixed: true
vuln-type: "os,library"
severity: HIGH,CRITICAL
```

O limite pode ser alterado pelo caller através do input `scan-severity`.

### Security gate

Quando o Trivy encontra vulnerabilidades dentro das severidades configuradas:

```text
build-and-scan = failed
```

Como o job de promoção possui:

```yaml
needs: build-and-scan
```

a promoção não é executada.

Consequentemente:

- os digests não são promovidos;
- nenhuma tag final é criada;
- a imagem final não é assinada;
- o fluxo termina com falha.

## Promoção da imagem

Após todas as plataformas passarem pelo scan, o job `publish` baixa os artifacts contendo os digests aprovados utilizando o filtro `digest-<image-name>-*`.

Esse padrão de download isolado por serviço garante que apenas os digests pertencentes à imagem em promoção sejam combinados, evitando a contaminação cruzada de manifests entre diferentes componentes executados no mesmo run.

A promoção utiliza:

```bash
docker buildx imagetools create
```

Os digests individuais são usados para montar o manifest candidato com a tag `candidate-<run-id>-<run-attempt>`, exclusiva da execução e tentativa para aquela imagem. Essa tag é auxiliar e não representa uma imagem aprovada para consumo.

Para builds multi-platform, o digest final corresponde ao OCI Image Index criado durante essa etapa.

Esse digest final é assinado e verificado com Cosign. Somente então as tags geradas pelo `docker/metadata-action` são aplicadas a ele, usando `--prefer-index=false` para preservar o manifest. O workflow confere que o digest promovido é o mesmo digest assinado antes de exportar os outputs.

Se a assinatura ou sua verificação falhar, as tags finais não são criadas ou atualizadas. Os digests do build e a tag candidata podem permanecer no GHCR; sua remoção deve seguir a política de retenção do registry.

O job `build-and-scan` não executa quando o consumidor é disparado por `pull_request`. Como o job `publish` depende dele, o workflow não publica imagens ou assinaturas nesse evento.

## Segurança

### Permissões mínimas

As permissões são definidas por job para seguir o princípio de menor privilégio.

O job `build-and-scan` utiliza:

```yaml
permissions:
  contents: read
  packages: write
```

Essas permissões são necessárias para realizar checkout do código e publicar a imagem por digest no GHCR.

O job `publish` utiliza:

```yaml
permissions:
  packages: write
  id-token: write
```

`packages: write` permite promover e publicar a imagem no GHCR.

`id-token: write` permite solicitar a identidade OIDC utilizada pela assinatura keyless com Cosign e Sigstore.

A autenticação no GHCR é realizada com o `GITHUB_TOKEN`.

Não é necessário utilizar PAT ou chave privada de assinatura de longa duração.

### Assinatura e verificação

O manifest candidato é assinado utilizando Cosign no modo keyless antes da promoção para as tags finais.

A assinatura é realizada sobre:

```text
ghcr.io/<owner>/<image>@sha256:<digest>
```

A verificação valida a assinatura, a identidade do workflow autorizado, o issuer OIDC e o repositório consumidor esperado.

A referência adotada para os callers é `IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@main`. A verificação exige exatamente:

```text
certificate-identity: https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@refs/heads/main
certificate-oidc-issuer: https://token.actions.githubusercontent.com
certificate-github-workflow-repository: ${{ github.repository }}
```

O contexto `${{ github.repository }}` identifica o repositório que chamou o workflow reutilizável. Essa restrição impede aceitar assinaturas de outros repositórios que usem o mesmo workflow público com a mesma identidade e issuer.

Os detalhes dessa política estão documentados em:

[Assinatura e verificação de imagens Docker com Cosign](./cosign-assinatura-imagens.md)

### Labels OCI e rastreabilidade

O reusable workflow preenche automaticamente os build-args e labels OCI necessários para rastreabilidade:

- `APP_VERSION`: preenchido automaticamente com `sha-<short-sha>`;
- `VCS_REF`: preenchido automaticamente com o commit SHA (`${{ github.sha }}`);
- `org.opencontainers.image.source`: URL canônica do repositório de origem;
- `org.opencontainers.image.revision`: commit SHA completo;
- `org.opencontainers.image.version`: tag `sha-<short-sha>`.

Os Dockerfiles que declaram `ARG APP_VERSION` e `ARG VCS_REF` em seus `LABEL` recebem esses valores automaticamente, sem necessidade de configuração redundante no caller.

Caso a aplicação demande build args adicionais (ex.: URLs de backend, flags de compilação) ou valores customizados, estes podem ser fornecidos via input `build-args`:

```yaml
build-args: |
  BACKEND_URL=http://api.exemplo.com
```

### Actions pinadas

As actions utilizadas pelo workflow são referenciadas por commit SHA, reduzindo o risco de alterações inesperadas em tags mutáveis.

### Normalização do nome da imagem

O owner do repositório e o nome da imagem são convertidos para lowercase antes da publicação no GHCR.

### Validação de digest

Antes de persistir ou promover um digest, o workflow valida o formato esperado:

```text
sha256:<64 caracteres hexadecimais>
```

## Cache

O workflow utiliza GitHub Actions Cache através do BuildKit.

O escopo é separado por imagem e plataforma:

```text
<image-name>-<platform>
```

Exemplo:

```text
apae-geral-backend-linux-amd64
```

Isso evita compartilhar cache de forma indevida entre imagens ou arquiteturas diferentes.

## Exemplo de caller

```yaml
name: Publish backend image

on:
  push:
    branches:
      - dev

permissions:
  contents: read
  packages: write
  id-token: write

jobs:
  publish-backend:
    uses: IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@main
    with:
      context: ./apps/api
      dockerfile: ./apps/api/Dockerfile
      image-name: apae-geral-backend
      platforms: '["linux/amd64"]'
      scan-severity: HIGH,CRITICAL
```

A permissão `id-token: write` deve ser concedida pelo caller para permitir a assinatura keyless com Cosign.

Embora o reusable workflow restrinja essa permissão ao job `publish`, o caller precisa disponibilizá-la como limite superior da execução.

O gatilho `push` em `dev` refere-se à branch do repositório consumidor. A chamada com `@main` seleciona a referência do workflow reutilizável no `APAE-INFRA`, correspondente à identidade exigida pela verificação Cosign.

Argumentos como `APP_VERSION` e `VCS_REF` são preenchidos automaticamente pelo reutilizável.

Os gatilhos são definidos no consumidor; o workflow reutilizável recebe a execução via `workflow_call`. As tags `latest` e `dev` são publicadas automaticamente quando a execução ocorre em `dev`, após verificar a assinatura. A publicação de tags semânticas pertence ao workflow específico de release e não exige adicionar um gatilho de tags a este caller.

Caso a chamada seja alterada para uma branch de feature, versão ou commit SHA aprovado, a identidade exigida na verificação Cosign também deverá corresponder à referência adotada.

## Validação realizada

O workflow foi validado utilizando o backend do repositório `IFPBEsp/APAE` como consumidor real.

Durante a validação, foram confirmados:

- chamada cross-repository via `workflow_call`;
- checkout do repositório consumidor;
- build da imagem;
- autenticação e publicação no GHCR;
- publicação por digest;
- scan da referência imutável;
- bloqueio da promoção após findings de segurança;
- assinatura keyless com Cosign;
- verificação da assinatura com identidade OIDC e issuer esperados.

O teste encontrou:

```text
Base Debian: 0 vulnerabilidades detectadas
Dependências Java: 29 vulnerabilidades
HIGH: 21
CRITICAL: 8
```

Como o limite utilizado foi `HIGH,CRITICAL`, o job de promoção foi corretamente bloqueado.

Esse comportamento confirmou o funcionamento do security gate.

Para validar especificamente a integração com Cosign, foi realizada uma execução controlada com configuração temporária do caller para permitir que o fluxo avançasse até a etapa de assinatura.

Nessa validação, foram confirmados:

- promoção da imagem para o digest OCI final;
- assinatura keyless com Cosign;
- uso do GitHub Actions OIDC;
- verificação da assinatura;
- validação do issuer esperado;
- validação da identidade do reusable workflow;
- assinatura vinculada ao digest OCI final.

A política padrão de bloqueio por vulnerabilidades permanece `HIGH,CRITICAL`.

## Ajustes identificados durante a validação

Durante o teste em um repositório consumidor real, foram necessários dois ajustes relacionados ao Trivy.

### Atualização do Trivy

A versão inicialmente utilizada pela action apresentava falha durante a instalação no runner.

O workflow foi atualizado para utilizar uma versão mais recente da action e fixar explicitamente a versão do Trivy.

### Referência completa da imagem

Inicialmente o scan recebia apenas:

```text
sha256:<digest>
```

Nesse formato, o Trivy não conseguia identificar o registry e tentava localizar a imagem como uma referência local ou no Docker Hub.

A referência foi corrigida para:

```text
ghcr.io/<owner>/<image>@sha256:<digest>
```

Após essa alteração, o Trivy conseguiu obter e analisar corretamente a imagem publicada no GHCR.

## Adoção pelos repositórios

Antes de migrar um repositório para o reusable workflow, recomenda-se:

1. validar o Dockerfile localmente;
2. validar o workflow caller com `actionlint`;
3. garantir que o caller forneça `id-token: write` para a assinatura keyless;
4. executar um primeiro build real;
5. analisar os findings do Trivy;
6. abrir issues específicas para vulnerabilidades pré-existentes;
7. somente então substituir pipelines legados quando aplicável.

Aplicações com vulnerabilidades `HIGH` ou `CRITICAL` serão bloqueadas pela configuração padrão.

A correção dessas vulnerabilidades deve ocorrer no repositório responsável pela aplicação.

## Responsabilidades

### APAE-INFRA

Responsável por:

- manutenção do reusable workflow;
- política de publicação;
- integração com GHCR;
- security gate;
- integração com Cosign e Sigstore;
- política de identidade utilizada na verificação das assinaturas;
- atualização das actions utilizadas pelo pipeline;
- documentação do comportamento do pipeline.

### Repositórios consumidores

Responsáveis por:

- Dockerfile da aplicação;
- build args específicos;
- escolha das plataformas necessárias;
- atualização das dependências da aplicação;
- correção ou avaliação das vulnerabilidades identificadas;
- concessão das permissões necessárias ao reusable workflow;
- definição de quando adotar o workflow como pipeline definitivo.

## Resultado

A issue `#35` estabelece uma base comum e reutilizável para publicação de imagens Docker na organização, posteriormente estendida com assinatura e verificação de imagens utilizando Cosign.

O fluxo resultante garante que:

```text
código
  ↓
imagem construída
  ↓
digest publicado
  ↓
imagem analisada
  ↓
security gate aprovado
  ↓
manifest candidato criado
  ↓
digest OCI final
  ↓
imagem assinada com Cosign
  ↓
assinatura verificada
  ↓
tags promovidas
  ↓
artefato disponível para consumo
```

A referência por digest permanece como identidade canônica do artefato, enquanto as tags são utilizadas como referências auxiliares para rastreabilidade humana e releases.

A assinatura Cosign adiciona uma camada de verificação da origem do artefato, permitindo confirmar que a imagem foi assinada pelo workflow autorizado através da identidade OIDC esperada.

Os detalhes da política de assinatura estão disponíveis em:

[Assinatura e verificação de imagens Docker com Cosign](./cosign-assinatura-imagens.md)
