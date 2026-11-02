# Assinatura e verificação de imagens Docker com Cosign

## Objetivo

Este documento descreve a estratégia adotada para assinatura e verificação de imagens Docker publicadas no GitHub Container Registry (GHCR) por meio do workflow reutilizável da organização.

A implementação utiliza **Cosign** e **Sigstore** com assinatura **keyless**, baseada na identidade OIDC fornecida pelo GitHub Actions.

O objetivo é garantir que as imagens publicadas possam ser verificadas quanto à:

- integridade do artefato;
- identidade do workflow que realizou a assinatura;
- origem da identidade OIDC;
- repositório consumidor que originou a execução;
- vinculação da assinatura ao digest exato da imagem.

## Visão geral do fluxo

A assinatura ocorre depois do build, scan de vulnerabilidades e criação do manifest candidato. As tags finais são publicadas somente após a verificação da assinatura.

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
criação do manifest candidato com os digests aprovados
  ↓
digest OCI final
  ↓
assinatura keyless com Cosign
  ↓
verificação da assinatura
  ↓
promoção para as tags finais
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
Create candidate manifest
  ↓
Verify candidate image
  ↓
Sign candidate image with Cosign
  ↓
Verify Cosign signature
  ↓
Promote verified image to final tags
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

O workflow consumidor também precisa conceder `id-token: write` no bloco de permissões do workflow ou do job que chama o reutilizável. As permissões dos jobs reutilizáveis não podem ampliar as concedidas pelo caller. O exemplo completo está em [Exemplo de caller](./pipeline-docker-ghcr.md#exemplo-de-caller).

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

A assinatura ocorre sobre o digest do manifest candidato, antes da promoção para as tags finais.

Se a assinatura falhar, o job também falha.

Não é utilizado `continue-on-error` na etapa de assinatura.

## Identidade confiável

A referência adotada nesta implementação para os callers é `@main`. A identidade exata exigida na verificação é:

```text
https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@refs/heads/main
```

O issuer OIDC esperado é:

```text
https://token.actions.githubusercontent.com
```

Essa identidade corresponde ao workflow reutilizável responsável pela assinatura.

Essa identidade, sozinha, não identifica o repositório consumidor: como o workflow reutilizável é público, outros repositórios também podem chamá-lo e obter uma assinatura com a mesma identidade e issuer.

Por isso, a verificação também exige `--certificate-github-workflow-repository`, que confere o repositório de origem registrado no certificado. No workflow reutilizável, o valor esperado é `${{ github.repository }}`, correspondente ao repositório que fez a chamada.

Exemplo:

```bash
cosign verify "${IMAGE}@${DIGEST}" \
  --certificate-identity="https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@refs/heads/main" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  --certificate-github-workflow-repository="${{ github.repository }}"
```

O consumidor deve chamar `IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@main` para corresponder à identidade exigida. Essa referência identifica o workflow reutilizável; a branch ou tag que dispara o consumidor pode ser diferente.

Os callers existentes com `@dev` devem receber `id-token: write` antes da integração do Cosign. A troca para `@main` só deve ocorrer após a promoção do workflow para essa branch, em uma janela coordenada sem execuções dos callers durante a transição. A ordem completa está em [Migração dos callers existentes para Cosign](./pipeline-docker-ghcr.md#migração-dos-callers-existentes-para-cosign).

Se a chamada passar a usar uma tag ou commit SHA, a identidade exigida na verificação também deverá ser atualizada para corresponder à nova referência.

## Verificação da assinatura

A verificação deve sempre utilizar a referência imutável da imagem.

Formato:

```text
ghcr.io/<owner>/<image>@sha256:<digest>
```

Exemplo:

```bash
cosign verify \
  --certificate-identity="https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@refs/heads/main" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  --certificate-github-workflow-repository="IFPBEsp/APAE" \
  ghcr.io/ifpbesp/<imagem>@sha256:<digest>
```

Nos exemplos de verificação manual, `IFPBEsp/APAE` é o repositório consumidor esperado. Substitua esse valor pelo repositório autorizado a produzir a imagem verificada; não use `IFPBEsp/APAE-INFRA` apenas por ele hospedar o workflow reutilizável.

A validação não deve apenas confirmar que existe alguma assinatura válida.

Ela deve verificar também:

- a identidade esperada;
- o issuer OIDC esperado;
- o repositório consumidor esperado;
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

não confirmar a assinatura, identidade, issuer ou repositório consumidor esperados, o job também falha.

Consequentemente, as tags finais não são criadas ou atualizadas quando a assinatura ou sua verificação falha.

Depois de criada, a tag `candidate-<run-id>-<run-attempt>` permanece no GHCR, inclusive nas execuções bem-sucedidas. Não há limpeza automática configurada para essas tags ou para os digests do build; sua remoção exige uma ação manual ou uma automação futura. A presença desses artefatos no registry não deve ser usada como sinal de aprovação para consumo.

Uma falha em `cosign sign` pode deixar o candidato sem assinatura. Esse artefato não deve ser consumido sem uma assinatura válida para o digest, a identidade, o issuer e o repositório consumidor exigidos.

O GHCR não bloqueia o pull desses artefatos por causa da falha do workflow. O bloqueio no deploy depende de uma etapa obrigatória de verificação ou de uma admission policy; essa integração ainda não está implementada nesta issue.

## Validação realizada

O fluxo atual foi validado em 20/10/2026 utilizando o backend do repositório `IFPBEsp/APAE` como consumidor real.

- [Execução completa, concluída com sucesso](https://github.com/IFPBEsp/APAE/actions/runs/39421278748).
- [Job de assinatura, verificação e promoção](https://github.com/IFPBEsp/APAE/actions/runs/39421278748/job/118623497832).
- Commit do workflow reutilizável testado: `aa5fa43`.
- Commit do consumidor: `aa2f449a10f368071f49a767d279f004c0059552`, na branch de teste `codex/pr75-cosign-validation`.

Imagem validada:

```text
ghcr.io/ifpbesp/apae-geral-backend@sha256:8cf384edad6f79f0c0fe673abde35113898405bffc7da52a61de45e62894e916
```

Durante a execução, foram concluídas com sucesso, nesta ordem, as etapas:

```text
Install Cosign
Create candidate manifest
Verify candidate image
Sign candidate image with Cosign
Verify Cosign signature
Promote verified image to final tags
Export workflow outputs
Publish workflow summary
```

Para testar o código antes da integração, o caller apontou para `@64-ci-adicionar-assinatura-de-imagens-docker-com-cosign`, e a identidade exigida foi temporariamente ajustada para essa mesma referência:

```bash
cosign verify "${IMAGE}@${DIGEST}" \
  --certificate-identity="https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@refs/heads/64-ci-adicionar-assinatura-de-imagens-docker-com-cosign" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  --certificate-github-workflow-repository="IFPBEsp/APAE"
```

A identidade definitiva do workflow foi restaurada para `@refs/heads/main` após o teste. Os callers definitivos devem usar `@main`.

A verificação confirmou:

```text
The cosign claims were validated
Existence of the claims in the transparency log was verified offline
The code-signing certificate was verified using trusted certificate authority certificates
```

Os logs confirmam a assinatura e a verificação do candidato antes da promoção, com restrição de identidade, issuer e repositório consumidor. A promoção utilizou `--prefer-index=false`, e a comparação obrigatória confirmou que a tag final `sha-aa2f449` aponta para o mesmo digest assinado.

O caller de teste usou temporariamente `scan-severity: UNKNOWN` para permitir a validação do Cosign apesar das vulnerabilidades conhecidas no backend. O padrão do reutilizável permanece `HIGH,CRITICAL`. Como o consumidor executou em uma branch de teste, as tags `latest` e `dev` não foram atualizadas.

Essa execução substitui a evidência anterior do fluxo que assinava a imagem depois da promoção.

## Verificação antes do consumo

Antes de utilizar uma imagem em deploy, auditoria ou promoção entre ambientes, recomenda-se validar a assinatura por digest.

Exemplo:

```bash
cosign verify \
  --certificate-identity="https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@refs/heads/main" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  --certificate-github-workflow-repository="IFPBEsp/APAE" \
  ghcr.io/ifpbesp/<imagem>@sha256:<digest>
```

A imagem deve ser considerada confiável somente quando:

- a assinatura for válida;
- o digest corresponder ao artefato esperado;
- a identidade corresponder ao workflow autorizado;
- o issuer corresponder ao GitHub Actions;
- o repositório no certificado corresponder ao consumidor esperado.

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
identity + issuer + repositório válidos?
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

- identidade correspondente ao workflow reutilizável autorizado do `APAE-INFRA`;
- repositório consumidor esperado para cada imagem, equivalente à restrição `--certificate-github-workflow-repository="IFPBEsp/APAE"` do Cosign. Esse valor deve ser definido pela política de confiança, pois identidade e issuer sozinhos também aceitariam assinaturas de outros repositórios que chamem o mesmo workflow público.

Ferramentas de admission policy compatíveis com Sigstore/Cosign podem ser avaliadas em uma issue futura.

A implementação dessa política no cluster não faz parte do escopo atual.

## Evolução recomendada

Após a integração inicial, recomenda-se evoluir a solução com:

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
