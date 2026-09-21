# Política de Versionamento e Rastreabilidade de Imagens Docker

## Objetivo

Definir a convenção de identificação, publicação e uso de imagens Docker publicadas no GitHub Container Registry (GHCR) pelos produtos da APAE.

A política prioriza:

- imutabilidade real por digest;
- rastreabilidade entre imagem e commit Git;
- rollback confiável;
- auditoria do que está implantado;
- preparação para futura adoção de GitOps com ArgoCD;
- padronização centralizada por workflow reutilizável.

## Princípio principal

A identidade canônica de uma imagem Docker é o seu digest OCI:

```text
sha256:<digest>
```

Exemplo:

```text
ghcr.io/ifpbesp/apae-geral-backend@sha256:8a0ab0aa283e69dc728075f9a347d543b0c12f1bf25ae8463407f2468d3c5667
```

O digest identifica exatamente o conteúdo publicado e deve ser a referência preferencial para deployments, GitOps, auditoria e rollback.

Tags continuam sendo utilizadas para facilitar a navegação e a rastreabilidade humana, mas não substituem o digest como identidade imutável da imagem.

## Convenção de identificação

### Digest OCI

O digest é a referência principal e imutável da imagem.

Formato:

```text
sha256:<digest>
```

Exemplo:

```text
sha256:8a0ab0aa283e69dc728075f9a347d543b0c12f1bf25ae8463407f2468d3c5667
```

Deve ser utilizado preferencialmente em:

- manifests Kubernetes;
- configurações GitOps;
- ArgoCD;
- rollback;
- auditoria;
- troubleshooting;
- registro de evidências de deploy.

Exemplo:

```yaml
image: ghcr.io/ifpbesp/apae-geral-backend@sha256:8a0ab0aa283e69dc728075f9a347d543b0c12f1bf25ae8463407f2468d3c5667
```

## Tag por commit

Cada build publicado deve receber também uma tag baseada no commit Git que originou a imagem.

Formato:

```text
sha-<short-sha>
```

Onde `<short-sha>` corresponde aos 7 primeiros caracteres do commit.

Exemplo:

```text
sha-f34a7a4
```

Essa tag tem como objetivo principal melhorar a rastreabilidade humana.

Exemplo de associação:

```text
commit Git:
f34a7a45e1416338d3a8eeb6978fbe96fa381fce

tag:
sha-f34a7a4

digest:
sha256:8a0ab0aa283e69dc728075f9a347d543b0c12f1bf25ae8463407f2468d3c5667
```

A relação esperada é:

```text
commit Git
    ↓
sha-<short-sha>
    ↓
digest OCI
```

A tag `sha-<short-sha>` deve apontar para o mesmo conteúdo identificado pelo digest correspondente.

## Imutabilidade

O digest OCI é imutável por definição de conteúdo.

Uma tag, mesmo quando baseada em commit, é tecnicamente mutável no registry. Por esse motivo:

- o digest é a referência definitiva da imagem;
- tags `sha-*` devem ser tratadas como imutáveis por política;
- uma tag `sha-*` já publicada não deve ser reutilizada para apontar para outro conteúdo;
- validações de CI/CD devem evitar sobrescrita acidental de tags de commit.

## Releases com Semantic Versioning

Quando os produtos adotarem versionamento formal, uma imagem também poderá receber uma tag de release:

```text
vX.Y.Z
```

Exemplo:

```text
v1.4.0
```

Essa tag deve ser publicada somente quando o build for originado por uma tag Git correspondente.

Exemplo:

```text
git tag v1.4.0
```

A tag de release funciona como referência semântica para usuários e operadores, mas o digest continua sendo a identidade final da imagem.

Exemplo:

```text
ghcr.io/ifpbesp/apae-geral-backend:v1.4.0
```

associado a:

```text
sha256:<digest-da-imagem>
```

## Uso de `latest`

A tag `latest` não faz parte da estratégia principal de rastreabilidade.

Ela pode existir opcionalmente apenas como alias de conveniência para uso manual ou local.

Caso seja publicada:

- não deve ser utilizada em manifests Kubernetes;
- não deve ser utilizada em GitOps;
- não deve ser utilizada como referência para rollback;
- não deve ser utilizada como evidência de auditoria;
- não deve ser a única tag disponível;
- não substitui a tag `sha-<short-sha>`;
- não substitui o digest OCI.

A ausência de `latest` não prejudica o processo de publicação ou deployment.

## Gatilhos de publicação

| Evento | Digest OCI | `sha-<short-sha>` | `latest` | `vX.Y.Z` |
| --- | ---: | ---: | ---: | ---: |
| Push ou merge em `dev` | Sim | Sim | Opcional | Não |
| Tag Git `vX.Y.Z` | Sim | Sim | Não | Sim |
| Pull Request | Não | Não | Não | Não |

O SHA utilizado deve corresponder ao commit que efetivamente originou o build.

## Estratégia recomendada de publicação

Para cada build originado de `dev`, o workflow deve publicar a imagem e registrar:

```text
ghcr.io/ifpbesp/<imagem>:sha-<short-sha>
ghcr.io/ifpbesp/<imagem>@sha256:<digest>
```

Opcionalmente:

```text
ghcr.io/ifpbesp/<imagem>:latest
```

Para uma release:

```text
ghcr.io/ifpbesp/<imagem>:sha-<short-sha>
ghcr.io/ifpbesp/<imagem>:vX.Y.Z
ghcr.io/ifpbesp/<imagem>@sha256:<digest>
```

## Uso em deployments

A ordem de preferência para referências de imagem é:

```text
1. digest OCI
2. tag sha-<short-sha>
3. tag vX.Y.Z
4. latest apenas para uso manual/conveniência
```

### Preferencial

```yaml
image: ghcr.io/ifpbesp/apae-geral-backend@sha256:<digest>
```

### Aceitável quando o digest ainda não estiver sendo promovido automaticamente

```yaml
image: ghcr.io/ifpbesp/apae-geral-backend:sha-f34a7a4
```

### Não recomendado para ambientes controlados

```yaml
image: ghcr.io/ifpbesp/apae-geral-backend:latest
```

## Rollback

O rollback deve utilizar uma referência previamente registrada da imagem.

Preferencialmente:

```text
sha256:<digest-anterior>
```

Exemplo:

```yaml
image: ghcr.io/ifpbesp/apae-geral-backend@sha256:<digest-anterior>
```

A tag `sha-<short-sha>` pode ser utilizada para identificar rapidamente qual commit corresponde ao digest desejado.

## Auditoria

Para cada imagem publicada, deve ser possível responder:

```text
Qual commit originou a imagem?
Qual tag sha-* representa esse commit?
Qual digest OCI identifica exatamente o conteúdo?
Qual versão está implantada atualmente?
```

A associação mínima esperada é:

```text
commit -> sha-<short-sha> -> digest
```

Os labels OCI das imagens também devem continuar registrando metadados como:

```text
org.opencontainers.image.revision
org.opencontainers.image.version
org.opencontainers.image.source
```

## Relação com GitOps e ArgoCD

Esta política é um pré-requisito para a futura adoção do ArgoCD.

Em GitOps, a referência da imagem deve ser determinística.

A forma preferencial é:

```text
image@sha256:<digest>
```

Com isso, uma alteração de versão no Git representa explicitamente uma mudança de conteúdo da imagem.

Exemplo:

```diff
- image: ghcr.io/ifpbesp/apae-geral-backend@sha256:aaa...
+ image: ghcr.io/ifpbesp/apae-geral-backend@sha256:bbb...
```

Esse modelo permite:

- identificar exatamente o que foi alterado;
- revisar a promoção da imagem via Pull Request;
- realizar rollback através do histórico Git;
- evitar mudanças silenciosas causadas por tags mutáveis.

A instalação e configuração do ArgoCD permanecem fora do escopo desta política.

## Aplicação da política

A lógica de geração das tags e registro dos digests não deve ser reimplementada em cada repositório de aplicação.

A política será aplicada centralmente pelo workflow reutilizável de build e publicação de imagens do `APAE-INFRA`:

```text
.github/workflows/build-publish-image.yml
```

A implementação desse workflow é responsabilidade da issue:

```text
APAE-INFRA#35
```

O workflow reutilizável deverá ser responsável por:

- identificar o commit que originou o build;
- gerar `sha-<short-sha>`;
- publicar a imagem no GHCR;
- obter e expor o digest OCI resultante;
- impedir a reutilização indevida de tags `sha-*`;
- gerar `vX.Y.Z` quando o build for originado por uma tag Git de release;
- publicar `latest` somente se essa conveniência for mantida;
- preencher metadados OCI da imagem;
- disponibilizar o digest para etapas futuras de deployment ou GitOps.

## Repositórios atualmente afetados

Os produtos que já publicam imagens no GHCR deverão adotar esta política ao migrarem para o workflow reutilizável.

### APAE Geral

Repositório:

```text
IFPBEsp/APAE
```

Imagens:

```text
apae-geral-frontend
apae-geral-backend
```

### APAE Gestão Escolar

Repositório:

```text
IFPBEsp/APAE-gestao-escolar
```

Imagens:

```text
apae-gestao-escolar-frontend
apae-gestao-escolar-backend
```

A adoção deve ocorrer pela utilização do workflow reutilizável, sem duplicação da lógica de versionamento nos workflows locais.

## Responsabilidades

### Issue APAE-INFRA#43

Responsável por:

- definir a política de identificação das imagens;
- priorizar digest OCI como referência canônica;
- definir a tag `sha-<short-sha>` para rastreabilidade humana;
- definir o uso opcional de `vX.Y.Z`;
- definir `latest` como alias opcional e não confiável para deployment;
- registrar a política como pré-requisito de GitOps e ArgoCD.

### Issue APAE-INFRA#35

Responsável por:

- implementar a política no workflow reutilizável;
- gerar automaticamente a tag `sha-<short-sha>`;
- capturar e disponibilizar o digest OCI;
- publicar tags de release quando aplicável;
- impedir comportamento inconsistente entre os produtos;
- documentar como os repositórios consumidores utilizam a pipeline.

## Compartilhamento da política

Esta documentação deve ser compartilhada com:

```text
IFPBEsp/APAE
IFPBEsp/APAE-gestao-escolar
```

O objetivo é alinhar a expectativa antes da migração para o workflow reutilizável.

Os repositórios consumidores não devem reimplementar individualmente essa lógica.

## Resumo

A política definida é:

```text
digest OCI         -> identidade canônica e imutável
sha-<short-sha>    -> rastreabilidade humana entre imagem e commit
vX.Y.Z             -> referência semântica opcional para releases
latest             -> alias opcional, sem uso em deployment ou auditoria
```

Para deployments e GitOps:

```text
preferir image@sha256:<digest>
```

A tag por commit existe para facilitar a rastreabilidade humana, enquanto o digest é a referência técnica definitiva da imagem.
