# Refatoração da Imagem Docker — APAE Site Comemorativo

## Contexto

Este documento registra a análise, os experimentos e a refatoração da imagem Docker do **APAE Site Comemorativo**.

O objetivo foi padronizar a imagem para o fluxo de CI/CD e Kubernetes, reduzir tamanho e superfície de ataque, manter execução non-root e documentar os ganhos com evidências mensuráveis.

A abordagem utilizada foi incremental: primeiro foi levantada uma baseline, depois foram testadas mudanças isoladas e, por fim, foi validada a arquitetura final.

---

## 1. Dockerfile original

O projeto utilizava inicialmente:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app

RUN apk add --no-cache libc6-compat openssl python3 make g++
RUN npm install -g pnpm@10.33.4

COPY package.json pnpm-lock.yaml ./
COPY prisma ./prisma

RUN pnpm install --frozen-lockfile --shamefully-hoist

COPY . .

ARG NEXT_PUBLIC_URL_APAE
ARG NEXT_PUBLIC_BASE_PATH
ENV NEXT_PUBLIC_URL_APAE=$NEXT_PUBLIC_URL_APAE
ENV NEXT_PUBLIC_BASE_PATH=$NEXT_PUBLIC_BASE_PATH

ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:20-alpine AS runner
WORKDIR /app

RUN apk add --no-cache openssl
RUN npm install -g pnpm@10.33.4

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/node_modules ./node_modules

COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:nodejs /app/pnpm-lock.yaml ./pnpm-lock.yaml
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/prisma ./prisma
COPY --from=builder --chown=nextjs:nodejs /app/next.config.ts ./next.config.ts

USER nextjs
EXPOSE 3000

CMD ["pnpm", "start"]
```

A imagem original já possuía:

- multi-stage build;
- Node.js 20;
- execução non-root;
- separação de builder e runtime.

Esses itens não são contabilizados como ganhos introduzidos pela refatoração.

---

## 2. Baseline

Imagem:

```text
apae-site-comemorativo:baseline
```

### 2.1 Tempo de build

| Cenário | Tempo |
|---|---:|
| Build limpo | 132,61 s |
| Build totalmente cacheado | 0,69 s |
| Build após alteração em código | 61,01 s |

### 2.2 Tamanho

| Métrica | Baseline |
|---|---:|
| Disk Usage | 2,26 GB |
| Content Size | 360 MB |

As maiores camadas eram:

```text
node_modules  ~1,18 GB
.next         ~526 MB
public        ~20,8 MB
```

O principal gargalo de tamanho era, portanto, a cópia completa de `node_modules` e da árvore `.next` para o runtime.

### 2.3 Usuário

```text
uid=1001(nextjs) gid=65533(nogroup)
```

A imagem já executava como usuário não-root.

### 2.4 Ferramentas disponíveis no runtime

```text
node
npm
npx
pnpm
openssl
apk
shell
```

---

## 3. Vulnerabilidades da baseline

### Dependências Node.js

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 0 |
| LOW | 8 |
| MEDIUM | 54 |
| HIGH | 82 |
| CRITICAL | 3 |
| Total | 147 |

---

## 4. Migração para Next.js Standalone

O `next.config.ts` original não utilizava `output: "standalone"`.

Foi alterado para:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: { unoptimized: true },
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || "/site-comemorativo",
};

export default nextConfig;
```

A partir disso, o runtime passou a receber somente:

```text
public
.next/standalone
.next/static
```

Em vez de copiar `node_modules` inteiro, `.next` inteira e arquivos auxiliares para produção.

---

## 5. Resultado do Standalone com Alpine

Imagem:

```text
apae-site-comemorativo:standalone
```

### 5.1 Tamanho

| Métrica | Baseline | Standalone Alpine | Resultado |
|---|---:|---:|---:|
| Disk Usage | 2,26 GB | 383 MB | **-83,1%** |
| Content Size | 360 MB | 110 MB | **-69,4%** |

As principais camadas passaram a ser:

```text
.next/standalone  ~105 MB
.next/static      ~3,02 MB
public            ~20,8 MB
```

A camada de `node_modules` de aproximadamente 1,18 GB desapareceu do runtime.

### 5.2 Build limpo

```text
132,61 s → 77,58 s
```

Redução observada de aproximadamente **41,5%**.

### 5.3 Findings Node.js

| Severidade | Baseline | Standalone Alpine |
|---|---:|---:|
| LOW | 8 | 4 |
| MEDIUM | 54 | 20 |
| HIGH | 82 | 36 |
| CRITICAL | 3 | 1 |
| Total | 147 | 61 |

---

## 6. Teste com runtime Distroless

O runtime Alpine foi substituído por:

```dockerfile
FROM gcr.io/distroless/nodejs20-debian13:nonroot
```

### Resultado

| Métrica | Standalone Alpine | Standalone Distroless |
|---|---:|---:|
| Disk Usage | 383 MB | 369 MB |
| Content Size | 110 MB | 108 MB |
| OS HIGH | 4 | 2 |
| Node HIGH | 36 | 17 |
| Node CRITICAL | 1 | 0 |

A execução non-root passou a utilizar:

```text
65532:65532
```

---

## 7. Incompatibilidade Prisma: musl × glibc

O primeiro teste utilizou builder Alpine e runtime Distroless Debian.

Essa combinação apresentou falha funcional no Prisma:

```text
Prisma Client could not locate the Query Engine for runtime "debian-openssl-3.0.x".

This happened because Prisma Client was generated for
"linux-musl-openssl-3.0.x".
```

A causa foi a diferença de libc:

```text
Alpine → musl libc
Debian → glibc
```

O Prisma foi gerado no builder Alpine para musl, mas o runtime Distroless Debian necessitava de engine para Debian/glibc.

---

## 8. Correção: builder Debian Slim

Para alinhar build e runtime, o builder foi alterado para:

```dockerfile
FROM node:20-bookworm-slim
```

A arquitetura passou a ser:

```text
Node 20 Bookworm Slim
Debian + glibc
        ↓
Prisma gerado para Debian/glibc
        ↓
Distroless Node 20 Debian
Debian + glibc
```

Essa opção reduz diferenças entre build e runtime. Como o builder é descartado no multi-stage, o tamanho dessa etapa não aumenta diretamente a imagem final.

---

## 9. Validação funcional do Prisma

Com builder Debian + runtime Distroless, o Next.js iniciou corretamente:

```text
✓ Starting...
✓ Ready
```

A aplicação também passou a inicializar o Prisma e executar queries reais:

```text
prisma.testimonial.findMany()
prisma.commemorativeDate.findMany()
```

O erro posterior foi apenas de conectividade com o PostgreSQL:

```text
Can't reach database server
```

Isso comprova que a Query Engine correta foi encontrada e que o problema `linux-musl` × `debian-openssl` deixou de ocorrer.

---

## 10. Benchmark da arquitetura final

Imagem:

```text
apae-site-comemorativo:debian-distroless
```

### 10.1 Build

| Cenário | Baseline | Final |
|---|---:|---:|
| Build limpo | 132,61 s | 108,91 s |
| Build cacheado | 0,69 s | 3,64 s |
| Alteração no código | 61,01 s | 59,31 s |

### 10.2 Tamanho

| Métrica | Baseline | Final | Resultado |
|---|---:|---:|---:|
| Disk Usage | 2,26 GB | 369 MB | **≈ -83,7%** |
| Content Size | 360 MB | 108 MB | **-70%** |

### 10.3 Vulnerabilidades Node.js

| Severidade | Baseline | Final |
|---|---:|---:|
| LOW | 8 | 2 |
| MEDIUM | 54 | 14 |
| HIGH | 82 | 17 |
| CRITICAL | 3 | 0 |
| Total | 147 | 33 |

Resultados principais:

```text
HIGH
82 → 17
≈ -79,3%

CRITICAL
3 → 0
-100%
```

### 10.4 Sistema operacional final

Base:

```text
Debian 13.4
```

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 2 |
| LOW | 24 |
| MEDIUM | 19 |
| HIGH | 2 |
| CRITICAL | 0 |
| Total | 47 |

---

## 11. Redução da superfície de ataque

O runtime original possuía:

```text
node
npm
npx
pnpm
openssl
apk
shell
```

Com Distroless, o runtime deixa de expor ferramentas administrativas e de desenvolvimento como:

```text
npm
npx
pnpm
apk
shell
```

---

## 12. Pinning por digest

### Builder

```text
node:20-bookworm-slim
sha256:2cf067cfed83d5ea958367df9f966191a942351a2df77d6f0193e162b5febfc0
```

### Runtime

```text
gcr.io/distroless/nodejs20-debian13:nonroot
sha256:c8da1b6cccb5c6cc4b8826c67353f31c5f7b2719c5517b1312d191b337d8bd99
```

---

## 13. Labels OCI

```dockerfile
ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Site Comemorativo" \
      org.opencontainers.image.description="Site comemorativo dos 30 anos da APAE" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/apae-site-comemorativo" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF
```

---

## 14. `.dockerignore`

Foi adotada uma estratégia de allowlist para limitar o contexto de build somente ao necessário:

```dockerignore
**

!package.json
!pnpm-lock.yaml

!next.config.ts
!tsconfig.json
!eslint.config.mjs

!prisma/
!prisma/**

!public/
!public/**

!src/
!src/**

!app/
!app/**

!components/
!components/**

!lib/
!lib/**

!styles/
!styles/**

!postcss.config.*
!tailwind.config.*
```

O build final foi validado após a mudança.

---

## 15. Dockerfile final

```dockerfile
# syntax=docker/dockerfile:1.7

FROM node:20-bookworm-slim@sha256:2cf067cfed83d5ea958367df9f966191a942351a2df77d6f0193e162b5febfc0 AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    openssl \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10.33.4

COPY package.json pnpm-lock.yaml ./
COPY prisma ./prisma

RUN pnpm install --frozen-lockfile --shamefully-hoist

COPY . .

ARG NEXT_PUBLIC_URL_APAE
ARG NEXT_PUBLIC_BASE_PATH

ENV NEXT_PUBLIC_URL_APAE=$NEXT_PUBLIC_URL_APAE
ENV NEXT_PUBLIC_BASE_PATH=$NEXT_PUBLIC_BASE_PATH
ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm build

FROM gcr.io/distroless/nodejs20-debian13:nonroot@sha256:c8da1b6cccb5c6cc4b8826c67353f31c5f7b2719c5517b1312d191b337d8bd99 AS runner

ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Site Comemorativo" \
      org.opencontainers.image.description="Site comemorativo dos 30 anos da APAE" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/apae-site-comemorativo" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

COPY --from=builder --chown=65532:65532 /app/public ./public
COPY --from=builder --chown=65532:65532 /app/.next/standalone ./
COPY --from=builder --chown=65532:65532 /app/.next/static ./.next/static

USER 65532:65532

EXPOSE 3000

CMD ["server.js"]
```

---

## 16. Comparativo final

| Métrica | Antes | Depois | Resultado |
|---|---:|---:|---:|
| Disk Usage | 2,26 GB | 369 MB | **≈ -83,7%** |
| Content Size | 360 MB | 108 MB | **-70%** |
| Node HIGH | 82 | 17 | **≈ -79,3%** |
| Node CRITICAL | 3 | 0 | **-100%** |
| Build limpo | 132,61 s | 108,91 s | **≈ -17,9%** |
| Source-change | 61,01 s | 59,31 s | **≈ -2,8%** |
| Runtime non-root | Sim | Sim | Mantido |
| `node_modules` completo no runtime | Sim | Não | Removido |
| pnpm no runtime | Sim | Não | Removido |
| npm/npx no runtime | Sim | Não | Removido |
| `apk` no runtime | Sim | Não | Removido |
| shell no runtime | Sim | Não | Removido |
| Next standalone | Não | Sim | Adicionado |
| Builder/runtime com libc compatível | Não | Sim | Corrigido |
| Pinning por digest | Não | Sim | Adicionado |
| Labels OCI completos | Não | Sim | Adicionado |

---

## 17. Conclusão

A refatoração do **APAE Site Comemorativo** apresentou um ganho expressivo de tamanho e segurança.

O principal resultado veio da adoção do Next.js standalone:

```text
Disk Usage
2,26 GB → 369 MB

Content Size
360 MB → 108 MB
```

A migração para Distroless complementou o ganho com menor superfície de ataque e redução de findings de alta severidade:

```text
Node HIGH
82 → 17

Node CRITICAL
3 → 0
```

Durante a validação, também foi identificada uma incompatibilidade real entre builder Alpine/musl e runtime Debian/glibc no Prisma.

A solução final adotou:

```text
Builder:
Node 20 Bookworm Slim
Debian + glibc

Build:
Next.js standalone
Prisma gerado em ambiente compatível

Runtime:
Distroless Node.js 20 Debian
non-root
sem shell
sem pnpm/npm/npx
sem apk
```

A imagem final está preparada para integração com CI/CD, publicação em registry e execução em Kubernetes.
