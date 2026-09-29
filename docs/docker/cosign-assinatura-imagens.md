# Assinatura e verificação de imagens Docker com Cosign

## Objetivo

Este documento descreve a estratégia adotada para assinatura e verificação de imagens Docker publicadas no GitHub Container Registry (GHCR) por meio do workflow reutilizável da organização.

A implementação utiliza **Cosign** e **Sigstore** com assinatura **keyless**, baseada na identidade OIDC fornecida pelo GitHub Actions.

O objetivo é garantir que as imagens publicadas possam ser verificadas quanto à:

- integridade do artefato;
- identidade do workflow que realizou a assinatura;
- origem da identidade OIDC;
- vinculação da assinatura ao digest exato da imagem.

## Visão geral do fluxo

A assinatura ocorre somente depois que a imagem passa pelo build, scan de vulnerabilidades e promoção.

```text
código
  ↓
build da imagem
  ↓
push por digest
  ↓
scan com Trivy
  ↓
security gate
  ↓
promoção dos digests aprovados
  ↓
digest OCI final
  ↓
assinatura keyless com Cosign
  ↓
verificação da assinatura
```

A referência assinada é sempre imutável:

```text
ghcr.io/<owner>/<image>@sha256:<digest>
```

Tags como `latest`, `sha-<short-sha>` ou `vX.Y.Z` não são utilizadas como identidade criptográfica da assinatura.

## Por que usar Cosign

O digest OCI identifica de forma imutável o conteúdo da imagem.

Exemplo:

```text
ghcr.io/ifpbesp/apae-geral-backend@sha256:...
```

Isso permite garantir que o artefato consumido é exatamente o mesmo artefato produzido pelo pipeline.

Entretanto, o digest sozinho não informa qual workflow autorizado produziu ou publicou a imagem.

A assinatura com Cosign adiciona uma camada de confiança, permitindo verificar:

- que a assinatura é válida;
- que o certificado utilizado é confiável;
- que a assinatura está associada ao digest esperado;
- que a identidade apresentada pertence ao workflow autorizado;
- que o issuer OIDC é o esperado.

## Assinatura keyless

A implementação utiliza o modo **keyless** do Cosign.

Nesse modelo, não é necessário armazenar uma chave privada permanente no GitHub.

Durante a execução:

1. o Cosign gera uma chave efêmera;
2. o GitHub Actions disponibiliza uma identidade OIDC;
3. o Sigstore emite um certificado de curta duração;
4. o digest OCI final é assinado;
5. a assinatura e os materiais de verificação são associados ao artefato no registry;
6. a assinatura é verificada antes de o workflow ser concluído com sucesso.

Não são necessários segredos como:

```text
COSIGN_PRIVATE_KEY
COSIGN_PASSWORD
```

## Workflow responsável

A assinatura é executada pelo workflow reutilizável:

```text
.github/workflows/docker-build-publish-image.yml
```

O job responsável pela assinatura é o job de publicação e promoção da imagem.

A sequência relevante é:

```text
Promote digests to final tags
  ↓
Verify promoted image
  ↓
Sign promoted image with Cosign
  ↓
Verify Cosign signature
```

## Permissões necessárias

As permissões são definidas por job para aplicar o princípio de menor privilégio.

### Job de build e scan

```yaml
permissions:
  contents: read
  packages: write
```

Essas permissões permitem:

- checkout do código do repositório consumidor;
- autenticação no GHCR;
- publicação da imagem por digest;
- execução do scan sobre a imagem publicada.

### Job de publicação e assinatura

```yaml
permissions:
  packages: write
  id-token: write
```

`packages: write` permite publicar e promover artefatos no GHCR.

`id-token: write` permite que o GitHub Actions solicite o token OIDC utilizado pelo fluxo keyless do Cosign.

## Assinatura da imagem

A assinatura é realizada sobre a referência imutável formada pelo nome da imagem e pelo digest OCI final.

Exemplo:

```bash
cosign sign --yes "${IMAGE}@${DIGEST}"
```

Exemplo de referência:

```text
ghcr.io/ifpbesp/apae-geral-backend@sha256:a8e30f0971bc2e81cd5e3f868866b3e860788c08bd038d3392fa1d84d7e902d1
```

A assinatura ocorre somente após a promoção dos digests aprovados.

Se a assinatura falhar, o job também falha.

Não é utilizado `continue-on-error` na etapa de assinatura.

## Identidade confiável

Durante a validação da implementação, o certificado emitido pelo fluxo keyless apresentou como identidade:

```text
https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@refs/heads/64-ci-adicionar-assinatura-de-imagens-docker-com-cosign
```

O issuer OIDC esperado é:

```text
https://token.actions.githubusercontent.com
```

Essa identidade corresponde ao workflow reutilizável responsável pela assinatura.

O workflow de verificação restringe explicitamente esses valores.

Exemplo:

```bash
cosign verify "${IMAGE}@${DIGEST}" \
  --certificate-identity="https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@refs/heads/64-ci-adicionar-assinatura-de-imagens-docker-com-cosign" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com"
```

> Após a estabilização da implementação, a identidade deve apontar para a referência estável adotada pelo `APAE-INFRA`, como uma branch estável, tag ou outra referência definida pela política da organização.

## Verificação da assinatura

A verificação deve sempre utilizar a referência imutável da imagem.

Formato:

```text
ghcr.io/<owner>/<image>@sha256:<digest>
```

Exemplo:

```bash
cosign verify \
  --certificate-identity="https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@refs/heads/dev" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/ifpbesp/<imagem>@sha256:<digest>
```

A validação não deve apenas confirmar que existe alguma assinatura válida.

Ela deve verificar também:

- a identidade esperada;
- o issuer OIDC esperado;
- o digest exato do artefato.

## Expressões permissivas

Durante a investigação inicial, foram utilizadas temporariamente expressões permissivas:

```text
--certificate-identity-regexp='.*'
--certificate-oidc-issuer-regexp='.*'
```

Essas opções foram utilizadas apenas para descobrir a identidade emitida no certificado.

Elas não devem ser utilizadas na política definitiva de verificação, pois aceitariam qualquer identidade ou issuer compatível com uma assinatura válida.

## Comportamento em caso de falha

As etapas de assinatura e verificação fazem parte do caminho obrigatório do pipeline.

Se o comando:

```bash
cosign sign
```

falhar, o job de publicação falha.

Se o comando:

```bash
cosign verify
```

não confirmar a assinatura, identidade ou issuer esperados, o job também falha.

Consequentemente, a publicação não é considerada concluída com sucesso sem uma assinatura válida e verificável.

## Validação realizada

A integração foi validada utilizando uma imagem real do backend do repositório `IFPBEsp/APAE`.

Imagem validada:

```text
ghcr.io/ifpbesp/apae-geral-backend@sha256:a8e30f0971bc2e81cd5e3f868866b3e860788c08bd038d3392fa1d84d7e902d1
```

Durante a execução, foram concluídas com sucesso as etapas:

```text
Install Cosign
Sign promoted image with Cosign
Verify Cosign signature
```

A verificação confirmou:

```text
The cosign claims were validated
Existence of the claims in the transparency log was verified offline
The code-signing certificate was verified using trusted certificate authority certificates
```

O teste confirmou:

- assinatura de uma imagem real publicada no GHCR;
- assinatura vinculada ao digest OCI final;
- geração de chave efêmera;
- uso de identidade OIDC do GitHub Actions;
- ausência de chave privada persistente;
- validação do certificado emitido pelo Sigstore;
- validação das evidências no transparency log;
- restrição da identidade ao workflow reutilizável autorizado;
- execução com permissões mínimas por job.

## Verificação antes do consumo

Antes de utilizar uma imagem em deploy, auditoria ou promoção entre ambientes, recomenda-se validar a assinatura por digest.

Exemplo:

```bash
cosign verify \
  --certificate-identity="https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@refs/heads/dev" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/ifpbesp/<imagem>@sha256:<digest>
```

A imagem deve ser considerada confiável somente quando:

- a assinatura for válida;
- o digest corresponder ao artefato esperado;
- a identidade corresponder ao workflow autorizado;
- o issuer corresponder ao GitHub Actions.

## Relação entre digest e assinatura

O digest e a assinatura possuem responsabilidades diferentes.

O digest:

```text
sha256:<digest>
```

garante a identidade imutável do conteúdo.

A assinatura Cosign adiciona a informação de confiança sobre quem produziu ou autorizou aquele artefato.

De forma simplificada:

```text
digest
  ↓
"este é exatamente este artefato"

assinatura
  ↓
"este artefato foi assinado pela identidade autorizada"
```

Por isso, o consumo seguro deve utilizar os dois conceitos em conjunto.

## Estratégia futura para GitOps

A assinatura implementada no pipeline prepara o ambiente para uma futura validação automática durante o deploy.

Fluxo esperado:

```text
manifest GitOps
  ↓
imagem referenciada por digest
  ↓
admission policy
  ↓
verificação Cosign/Sigstore
  ↓
identity + issuer válidos?
  ├── sim → deploy permitido
  └── não → deploy bloqueado
```

A política futura deverá validar, no mínimo:

- uso de referência por digest;
- assinatura Cosign válida;
- issuer OIDC:

```text
https://token.actions.githubusercontent.com
```

- identidade correspondente ao workflow reutilizável autorizado do `APAE-INFRA`.

Ferramentas de admission policy compatíveis com Sigstore/Cosign podem ser avaliadas em uma issue futura.

A implementação dessa política no cluster não faz parte do escopo atual.

## Evolução recomendada

Após a integração inicial, recomenda-se evoluir a solução com:

- adoção de uma referência estável para a identidade do workflow;
- documentação da política oficial de confiança da organização;
- validação automática no processo GitOps;
- admission policy no cluster;
- uso obrigatório de referências `image@digest` nos manifests de deploy.

## Resumo

O fluxo implementado passa a garantir:

```text
código
  ↓
imagem construída
  ↓
imagem analisada
  ↓
security gate aprovado
  ↓
digest OCI final
  ↓
imagem assinada com Cosign
  ↓
identidade OIDC validada
  ↓
artefato pronto para consumo confiável
```

A referência por digest continua sendo a identidade canônica do artefato.

A assinatura Cosign adiciona a prova criptográfica de que o artefato foi produzido e assinado pelo workflow autorizado.
