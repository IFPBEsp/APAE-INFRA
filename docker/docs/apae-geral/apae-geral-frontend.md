# Refatoração da Imagem Docker — APAE Geral Frontend

## Contexto

Este documento registra a análise, refatoração e validação da imagem Docker do frontend **APAE Geral**.

A atividade faz parte da padronização das imagens dos produtos APAE, com foco em segurança, redução da superfície de ataque, redução do tamanho da imagem, execução non-root, builds reproduzíveis, simplificação do processo de build, redução do contexto Docker, compatibilidade com CI/CD, preparação para publicação no GHCR e execução em Kubernetes.

---

## 1. Dockerfile original

```dockerfile
# syntax=docker/dockerfile:1.7

# dependências
FROM node:20-alpine AS deps
WORKDIR /app

RUN apk add --no-cache libc6-compat

COPY package.json ./
COPY package-lock.json* ./

RUN if [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm install --no-audit --no-fund; \
    fi

# build
FROM node:20-alpine AS builder
WORKDIR /app

ARG NEXT_PUBLIC_API_URL=/apae-geral/api
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

# runtime
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN apk add --no-cache wget \
 && addgroup -S -g 1001 appgroup \
 && adduser -S -u 1001 -G appgroup appuser

COPY --from=builder --chown=appuser:appgroup /app/public ./public
COPY --from=builder --chown=appuser:appgroup /app/.next/standalone ./
COPY --from=builder --chown=appuser:appgroup /app/.next/static ./.next/static

USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:3000/apae-geral >/dev/null 2>&1 || exit 1

CMD ["node", "server.js"]
```

A imagem original já possuía multi-stage build, Next.js standalone e execução non-root. Esses itens não são contabilizados como ganhos introduzidos pela refatoração.

---

## 2. Baseline

Imagem utilizada:

```text
apae-frontend:baseline
```

| Métrica | Baseline |
|---|---:|
| Disk Usage | 262 MB |
| Content Size | 63,7 MB |
| Build limpo | 366,91 s |
| Build totalmente cacheado | 3,90 s |
| Build após alteração em código | 26,92 s |

Usuário do runtime:

```text
uid=1001(appuser) gid=1001(appgroup) groups=1001(appgroup)
```

Ferramentas identificadas no runtime:

```text
/usr/local/bin/node
/usr/local/bin/npm
/usr/local/bin/npx
/usr/bin/wget
/sbin/apk
```

Principais camadas da aplicação:

```text
.next/standalone  ~47,1 MB
.next/static      ~4,06 MB
public            ~225 KB
```

---

## 3. Vulnerabilidades da imagem original

### Sistema operacional — Alpine 3.23.4

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 0 |
| LOW | 32 |
| MEDIUM | 14 |
| HIGH | 4 |
| CRITICAL | 0 |
| Total | 50 |

### Dependências Node.js

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 0 |
| LOW | 4 |
| MEDIUM | 15 |
| HIGH | 31 |
| CRITICAL | 1 |
| Total | 51 |

---

## 4. Simplificação dos stages de build

O Dockerfile original possuía stages separados de `deps` e `builder`.

A refatoração consolidou a instalação das dependências e o build em um único stage:

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
COPY package-lock.json* ./

RUN if [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm install --no-audit --no-fund; \
    fi

COPY . .

RUN npm run build
```

A ordem dos `COPY` continua preservando o cache da instalação das dependências enquanto `package.json` não for alterado.

O stage separado de `deps` e a instalação de `libc6-compat` deixaram de ser necessários.

---

## 5. Ausência de `package-lock.json`

Durante a refatoração foi identificado que o frontend não possui `package-lock.json` versionado.

Por esse motivo, a tentativa de utilizar somente:

```dockerfile
RUN npm ci
```

falhou.

Foi mantida compatibilidade com o estado atual do projeto através de:

```dockerfile
RUN if [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm install --no-audit --no-fund; \
    fi
```

A ausência de lockfile reduz a reprodutibilidade da instalação das dependências. A criação e o versionamento de um `package-lock.json` devem ser tratados em atividade separada da refatoração Docker.

---

## 6. Migração do runtime para Distroless

O runtime original:

```dockerfile
FROM node:20-alpine
```

foi substituído por:

```dockerfile
FROM gcr.io/distroless/nodejs20-debian13:nonroot
```

O builder permaneceu em:

```text
node:20-alpine
```

Como o projeto já utilizava:

```ts
output: "standalone"
```

o runtime continua recebendo apenas:

```text
public
.next/standalone
.next/static
```

Não há necessidade de copiar `node_modules` completo para a imagem final.

---

## 7. Resultado do build

| Cenário | Baseline | Refatorado |
|---|---:|---:|
| Build limpo | 366,91 s | 208,25 s |
| Build cacheado | 3,90 s | 5,14 s |
| Alteração no código | 26,92 s | 26,66 s |

O build limpo caiu aproximadamente **43,2%**.

O cenário de alteração em código permaneceu praticamente estável:

```text
26,92 s → 26,66 s
```

O build totalmente cacheado variou de 3,90 s para 5,14 s, diferença de aproximadamente 1,24 s em termos absolutos.

---

## 8. Resultado de tamanho e vulnerabilidades

### Tamanho

| Métrica | Antes | Depois | Resultado |
|---|---:|---:|---:|
| Disk Usage | 262 MB | 243 MB | **-7,3%** |
| Content Size | 63,7 MB | 60,4 MB | **-5,2%** |

### Sistema operacional

O runtime final utilizou:

```text
Debian 13.4
```

| Severidade | Antes | Depois |
|---|---:|---:|
| UNKNOWN | 0 | 1 |
| LOW | 32 | 24 |
| MEDIUM | 14 | 20 |
| HIGH | 4 | 2 |
| CRITICAL | 0 | 0 |
| Total | 50 | 47 |

O ganho concreto foi a redução dos findings **HIGH** do sistema operacional:

```text
4 → 2
```

### Dependências Node.js

| Severidade | Antes | Depois |
|---|---:|---:|
| UNKNOWN | 0 | 0 |
| LOW | 4 | 2 |
| MEDIUM | 15 | 9 |
| HIGH | 31 | 12 |
| CRITICAL | 1 | 0 |
| Total | 51 | 23 |

Principais reduções:

```text
Node HIGH:     31 → 12  ≈ -61,3%
Node CRITICAL: 1 → 0    -100%
```

---

## 9. Redução da superfície de ataque

O runtime original possuía:

```text
node
npm
npx
wget
apk
shell
```

Na imagem final foram removidos do runtime:

```text
npm
npx
wget
apk
shell
```

O usuário passou a ser explicitamente:

```text
65532:65532
```

Como a imagem Distroless Node já define o runtime Node.js como entrypoint, o comando final passou de:

```dockerfile
CMD ["node", "server.js"]
```

para:

```dockerfile
CMD ["server.js"]
```

---

## 10. Healthcheck

O `HEALTHCHECK` foi removido do Dockerfile. A saúde da aplicação será gerenciada pelo Kubernetes com:

```text
startupProbe
readinessProbe
livenessProbe
```

Adicionar `wget`, `curl` ou shell apenas para healthcheck aumentaria desnecessariamente a superfície da imagem Distroless.

---

## 11. Pinning das imagens

Builder:

```text
node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293
```

Runtime:

```text
gcr.io/distroless/nodejs20-debian13:nonroot@sha256:c8da1b6cccb5c6cc4b8826c67353f31c5f7b2719c5517b1312d191b337d8bd99
```

Foi utilizado o digest do índice multi-arquitetura.

---

## 12. Metadados OCI e rastreabilidade no GHCR

```dockerfile
ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Geral Frontend" \
      org.opencontainers.image.description="Frontend do sistema APAE" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF
```

O workflow de publicação no GHCR foi ajustado para fornecer os argumentos utilizados pelos labels OCI durante o build:

```yaml
build-args: |
  NEXT_PUBLIC_API_URL=/apae-geral/api
  APP_VERSION=${{ steps.meta.outputs.version }}
  VCS_REF=${{ github.sha }}
```

Dessa forma, `org.opencontainers.image.version` passa a receber a versão produzida pelo `docker/metadata-action`, enquanto `org.opencontainers.image.revision` recebe o SHA completo do commit responsável pela imagem.

O mesmo mecanismo foi validado na imagem publicada do backend, confirmando o preenchimento de:

```text
org.opencontainers.image.version=dev
org.opencontainers.image.revision=f34a7a45e1416338d3a8eeb6978fbe96fa381fce
```

Com isso, as imagens publicadas pelo workflow passam a manter rastreabilidade entre artefato, versão e código-fonte.

---

## 13. `.dockerignore`

```dockerignore
**

!package.json
!package-lock.json
!next.config.ts
!tsconfig.json
!postcss.config.mjs
!components.json
!eslint.config.mjs

!public/
!public/**

!src/
!src/**
```

O contexto Docker passa a conter apenas os arquivos necessários para instalação das dependências e build da aplicação.

---

## 14. Dockerfile final

```dockerfile
# syntax=docker/dockerfile:1.7

FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS builder

WORKDIR /app

COPY package.json ./
COPY package-lock.json* ./

RUN if [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm install --no-audit --no-fund; \
    fi

COPY . .

ARG NEXT_PUBLIC_API_URL=/apae-geral/api

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

FROM gcr.io/distroless/nodejs20-debian13:nonroot@sha256:c8da1b6cccb5c6cc4b8826c67353f31c5f7b2719c5517b1312d191b337d8bd99 AS runner

ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Geral Frontend" \
      org.opencontainers.image.description="Frontend do sistema APAE" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

COPY --from=builder --chown=65532:65532 /app/public ./public
COPY --from=builder --chown=65532:65532 /app/.next/standalone ./
COPY --from=builder --chown=65532:65532 /app/.next/static ./.next/static

USER 65532:65532

EXPOSE 3000

CMD ["server.js"]
```

---

## 15. Conclusão

Principais resultados:

```text
Disk Usage:     262 MB → 243 MB
Content Size:   63,7 MB → 60,4 MB
OS HIGH:        4 → 2
Node HIGH:      31 → 12
Node CRITICAL:  1 → 0
Build limpo:    366,91 s → 208,25 s
Source-change:  26,92 s → 26,66 s
```

A estratégia final utiliza Node.js 20 Alpine no builder, Next.js standalone, Distroless Node.js 20 nonroot no runtime, pinning por digest, labels OCI completos e `.dockerignore` em allowlist.

O workflow de publicação no GHCR também foi ajustado para preencher `APP_VERSION` e `VCS_REF`, garantindo rastreabilidade dos metadados OCI das imagens publicadas.

A ausência de `package-lock.json` deve ser tratada separadamente para melhorar a reprodutibilidade das dependências do frontend.
