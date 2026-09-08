# Refatoração da Imagem Docker — APAE Gestão Escolar Frontend

## Contexto

Este documento registra a análise, refatoração e validação da imagem Docker do frontend **APAE Gestão Escolar**.

A atividade faz parte da padronização das imagens dos produtos APAE, com foco em segurança, redução da superfície de ataque, redução do tamanho da imagem, execução non-root, builds reproduzíveis, redução do contexto Docker, compatibilidade com CI/CD, preparação para publicação no GHCR e execução em Kubernetes.

---

## 1. Dockerfile original

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --frozen-lockfile

COPY .. .

ARG NEXT_PUBLIC_API_URL=/gestao-escolar/api
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

ARG BACKEND_URL=http://localhost:8080
ENV BACKEND_URL=$BACKEND_URL

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

LABEL org.opencontainers.image.source=https://github.com/IFPBEsp/APAE-gestao-escolar
LABEL org.opencontainers.image.description="APAE Gestão Escolar - Frontend (Next.js)"
LABEL org.opencontainers.image.licenses=MIT

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=builder --chown=appuser:appgroup /app/.next/standalone ./
COPY --from=builder --chown=appuser:appgroup /app/.next/static ./.next/static/
COPY --from=builder --chown=appuser:appgroup /app/public ./public/

USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD wget -qO- http://localhost:3000/gestao-escolar || exit 1

CMD ["node", "server.js"]
```

A imagem original já possuía multi-stage build, Next.js standalone, execução non-root, separação entre builder e runtime e labels OCI básicos.

---

## 2. Baseline

Imagem:

```text
gestao-escolar-frontend:baseline
```

| Métrica | Baseline |
|---|---:|
| Build limpo | 34,69 s |
| Build totalmente cacheado | 0,52 s |
| Disk Usage | 316 MB |
| Content Size | 76,5 MB |

Principais layers da aplicação:

```text
.next/standalone  ~89,3 MB
.next/static      ~4,78 MB
public            ~1,89 MB
```

Usuário:

```text
uid=100(appuser) gid=101(appgroup)
```

Ferramentas presentes no runtime:

```text
node
npm
npx
wget
apk
shell
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
| LOW | 5 |
| MEDIUM | 19 |
| HIGH | 31 |
| CRITICAL | 1 |
| Total | 56 |

---

## 4. Migração do runtime para Distroless

O runtime original:

```dockerfile
FROM node:20-alpine
```

foi substituído por:

```dockerfile
FROM gcr.io/distroless/nodejs20-debian13:nonroot
```

O builder permaneceu em `node:20-alpine`, pois precisa de npm, shell e tooling para build, mas não é distribuído em produção.

---

## 5. Resultado com Distroless

| Métrica | Antes | Depois | Resultado |
|---|---:|---:|---:|
| Disk Usage | 316 MB | 302 MB | **-4,4%** |
| Content Size | 76,5 MB | 74,6 MB | **-2,5%** |
| OS HIGH | 4 | 2 | **-50%** |
| OS CRITICAL | 0 | 0 | Mantido |
| Node HIGH | 31 | 13 | **-58,1%** |
| Node CRITICAL | 1 | 0 | **-100%** |

Usuário final:

```text
65532:65532
```

A execução non-root foi mantida.

Foram removidos do runtime:

```text
npm
npx
wget
apk
shell
```

---

## 6. Build

O build limpo original foi:

```text
34,69 s
```

Durante o teste com Distroless foi observado:

```text
53,40 s
```

Essa diferença não foi atribuída ao runtime Distroless, pois o runtime é construído após o `npm run build` e a execução envolveu reconstrução/download de layers.

Após alteração em código, foi observado:

```text
23,36 s
```

Não foi identificado gargalo que justificasse adicionar cache mount específico para npm. Foi mantido o cache tradicional de layers Docker.

---

## 7. Healthcheck

O healthcheck original:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD wget -qO- http://localhost:3000/gestao-escolar || exit 1
```

foi removido.

A saúde da aplicação será gerenciada pelo Kubernetes através de:

```text
startupProbe
readinessProbe
livenessProbe
```

---

## 8. Pinning das imagens

Builder:

```text
node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293
```

Runtime:

```text
gcr.io/distroless/nodejs20-debian13:nonroot@sha256:c8da1b6cccb5c6cc4b8826c67353f31c5f7b2719c5517b1312d191b337d8bd99
```

---

## 9. Metadados OCI

```dockerfile
ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Gestão Escolar Frontend" \
      org.opencontainers.image.description="Frontend do APAE Gestão Escolar" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE-gestao-escolar" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF
```

---

## 10. `.dockerignore`

```dockerignore
**

!package.json
!package-lock.json

!next.config.js
!postcss.config.js
!tailwind.config.js
!components.json
!tsconfig.json

!public/
!public/**

!src/
!src/**
```

---

## 11. Dockerfile final

```dockerfile
# syntax=docker/dockerfile:1.7

FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL=/gestao-escolar/api
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

ARG BACKEND_URL=http://localhost:8080
ENV BACKEND_URL=$BACKEND_URL

RUN npm run build

FROM gcr.io/distroless/nodejs20-debian13:nonroot@sha256:c8da1b6cccb5c6cc4b8826c67353f31c5f7b2719c5517b1312d191b337d8bd99 AS runner

ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Gestão Escolar Frontend" \
      org.opencontainers.image.description="Frontend do APAE Gestão Escolar" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE-gestao-escolar" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

COPY --from=builder --chown=65532:65532 /app/.next/standalone ./
COPY --from=builder --chown=65532:65532 /app/.next/static ./.next/static/
COPY --from=builder --chown=65532:65532 /app/public ./public/

USER 65532:65532

EXPOSE 3000

CMD ["server.js"]
```

---

## 12. Conclusão

Principais resultados:

```text
Disk Usage:   316 MB → 302 MB
Content Size: 76,5 MB → 74,6 MB
OS HIGH:      4 → 2
Node HIGH:    31 → 13
Node CRITICAL: 1 → 0
```

A estratégia final utiliza Node 20 Alpine no builder, Distroless Node.js 20 nonroot no runtime, pinning por digest, labels OCI completos e `.dockerignore` em allowlist.
