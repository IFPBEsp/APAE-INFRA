# Pipeline reutilizável de build, scan e publicação de imagens Docker

## Objetivo

Esta documentação descreve o workflow reutilizável criado na issue `#35` do repositório `APAE-INFRA` para padronizar o build, a análise de vulnerabilidades e a publicação de imagens Docker no GitHub Container Registry (GHCR).

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
- assinatura keyless da imagem promovida com Cosign e Sigstore;
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
promoção
   ↓
criação das tags finais
   ↓
digest OCI final
   ↓
assinatura keyless com Cosign
   ↓
verificação da assinatura
```

A imagem é enviada ao registry antes do scan utilizando apenas seu digest, sem receber as tags finais de publicação.

As tags oficiais são criadas apenas após todas as plataformas configuradas passarem pelo scan.

Após a promoção, o digest OCI final é assinado e validado com Cosign utilizando a identidade OIDC do GitHub Actions.

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

```text
docs/boas-praticas/16-politica-tags-imagens-docker.md
```

### Tags geradas

O workflow gera:

- `sha-<short-sha>`: gerada para o commit que originou o build;
- `latest`: publicada automaticamente em todo push na branch `dev`.

A tag `vX.Y.Z` não é gerada por este workflow. A publicação de uma release semântica deve reutilizar a imagem já existente e será tratada em um workflow específico de release.

O uso de `latest` para deploy, rollback ou auditoria não é recomendado.

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
4. tem seu digest persistido como artifact somente se o scan for aprovado.

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
- o fluxo termina com falha.

## Promoção da imagem

Após todas as plataformas passarem pelo scan, o job `publish` baixa os artifacts contendo os digests aprovados.

A promoção utiliza:

```bash
docker buildx imagetools create
```

Os digests individuais são usados para montar a imagem final e aplicar as tags geradas pelo `docker/metadata-action`.

Para builds multi-platform, o digest final corresponde ao OCI Image Index criado durante essa etapa.

## Segurança

### Permissões mínimas

Atualmente, as permissões do workflow são definidas de forma global:

```yaml
permissions:
  contents: read
  packages: write
```

Essas permissões são utilizadas pelos jobs do pipeline. `contents:` read permite o checkout e a leitura do código-fonte, enquanto `packages:` write permite publicar as imagens no GitHub Container Registry (GHCR).

A definição das permissões individualmente por job será adotada na evolução do pipeline com a integração do Cosign, permitindo aplicar o princípio de menor privilégio de forma mais granular.

### Assinatura e verificação

A imagem promovida é assinada utilizando Cosign no modo keyless.

A assinatura é realizada sobre:

```text
ghcr.io/<owner>/<image>@sha256:<digest>
```

A verificação valida a assinatura, a identidade do workflow autorizado e o issuer OIDC esperado.

Os detalhes dessa política estão documentados em:

[Assinatura e verificação de imagens Docker com Cosign](./cosign-assinatura-imagens.md)

### Labels OCI

Os metadados OCI específicos de cada imagem são definidos pelos próprios Dockerfiles padronizados.

O reusable workflow disponibiliza `build-args` para que os callers forneçam os valores necessários, por exemplo:

```yaml
build-args: |
  APP_VERSION=${{ github.sha }}
  VCS_REF=${{ github.sha }}
```

Dessa forma, os `LABEL` definidos nos Dockerfiles permanecem como fonte dos metadados da aplicação, evitando que um conjunto genérico de labels seja aplicado indistintamente a imagens diferentes.

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
    uses: IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@<ref>
    with:
      context: ./apps/api
      dockerfile: ./apps/api/Dockerfile
      image-name: apae-geral-backend
      platforms: '["linux/amd64"]'
      scan-severity: HIGH,CRITICAL
      build-args: |
        APP_VERSION=${{ github.sha }}
        VCS_REF=${{ github.sha }}
```

A permissão `id-token: write` deve ser concedida pelo caller para permitir a assinatura keyless com Cosign.

Embora o reusable workflow restrinja essa permissão ao job `publish`, o caller precisa disponibilizá-la como limite superior da execução.

O `latest` é publicado automaticamente quando a execução ocorre em `dev`.

Durante desenvolvimento e validação, `<ref>` pode apontar para uma branch de feature.

Após estabilização, os repositórios consumidores devem utilizar uma referência estável, preferencialmente uma versão ou commit SHA aprovado.

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
- atualização das actions utilizadas pelo pipeline;
- documentação do comportamento do pipeline.

### Repositórios consumidores

Responsáveis por:

- Dockerfile da aplicação;
- build args específicos;
- escolha das plataformas necessárias;
- atualização das dependências da aplicação;
- correção ou avaliação das vulnerabilidades identificadas;
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
tags promovidas
  ↓
digest OCI final
  ↓
imagem assinada com Cosign
  ↓
assinatura verificada
  ↓
artefato disponível para consumo
```

A referência por digest permanece como identidade canônica do artefato, enquanto as tags são utilizadas como referências auxiliares para rastreabilidade humana e releases.

A assinatura Cosign adiciona uma camada de verificação da origem do artefato, permitindo confirmar que a imagem foi assinada pelo workflow autorizado através da identidade OIDC esperada.

Os detalhes da política de assinatura estão disponíveis em:

[Assinatura e verificação de imagens Docker com Cosign](./cosign-assinatura-imagens.md)
