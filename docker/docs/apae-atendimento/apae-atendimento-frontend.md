# Refatoração da Imagem Docker — APAE Atendimento Frontend

## Contexto

Este documento registra a análise, refatoração e validação da imagem Docker do frontend **APAE Atendimento**.

A atividade faz parte da padronização das imagens dos produtos APAE, com foco em:

- segurança;
- redução da superfície de ataque;
- redução do tamanho da imagem;
- execução non-root;
- builds reproduzíveis;
- otimização de build;
- padronização do uso de gerenciadores de pacote;
- redução do contexto Docker;
- compatibilidade com CI/CD;
- preparação para publicação no GHCR;
- preparação para execução em Kubernetes.

Além das alterações realizadas, foram coletadas métricas antes e depois da refatoração para demonstrar quantitativamente o impacto das mudanças.

---

# 1. Dockerfile original

O frontend utilizava inicialmente:

```dockerfile
FROM node:24-alpine AS base

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

RUN npm install -g pnpm@10.33.0

FROM base AS deps

COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile

FROM base AS builder

ARG NEXT_PUBLIC_API_URL

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

COPY --from=deps /app/node_modules ./node_modules
COPY .. .

RUN pnpm build

FROM node:24-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

RUN apk add --no-cache curl

COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node

EXPOSE 3000

CMD ["node", "server.js"]
```

A imagem original já possuía alguns pontos positivos:

- multi-stage build;
- separação entre instalação de dependências, build e runtime;
- uso de `pnpm install --frozen-lockfile`;
- utilização do modo `standalone` do Next.js;
- execução com usuário não-root;
- somente os artefatos necessários do Next.js copiados para o runtime.

Esses itens foram preservados e não devem ser apresentados como ganhos introduzidos pela refatoração.

---

# 2. Baseline

Antes de qualquer alteração, foi construída a imagem:

```text
atendimento-frontend:baseline
```

## 2.1 Tamanho da imagem

| Métrica | Baseline |
|---|---:|
| Disk Usage | 334 MB |
| Content Size | 80,1 MB |

O histórico da imagem mostrou como principais componentes:

```text
.next/standalone   ~68,4 MB
.next/static       ~4,27 MB
public             ~938 KB
curl               ~5,39 MB
```

---

## 2.2 Tempo de build

Foram medidos diferentes cenários:

| Cenário | Tempo |
|---|---:|
| Build limpo | 78,48 s |
| Build totalmente cacheado | 2,26 s |
| Build após alteração em código | 23,56 s |

Esses valores foram registrados como baseline para comparação com as alterações posteriores.

---

## 2.3 Usuário de runtime

A configuração da imagem indicava:

```text
User: node
```

Ao executar:

```bash
docker run --rm \
  --entrypoint sh \
  atendimento-frontend:baseline \
  -c 'id'
```

foi obtido:

```text
uid=1000(node) gid=1000(node) groups=1000(node)
```

Portanto, a imagem original já executava corretamente como usuário não-root.

---

## 2.4 Ferramentas presentes no runtime

Foram identificadas:

```text
/usr/local/bin/node
/usr/local/bin/npm
/usr/bin/curl
/sbin/apk
```

O runtime também possuía shell por utilizar Alpine Linux.

Isso significa que a imagem final continha ferramentas não necessárias para a execução do servidor Next.js.

---

# 3. Vulnerabilidades da imagem original

Foi realizado scan com Trivy.

## 3.1 Sistema operacional

Imagem baseada em Alpine 3.24.1.

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 0 |
| LOW | 12 |
| MEDIUM | 6 |
| HIGH | 2 |
| CRITICAL | 0 |
| **Total** | **20** |

---

## 3.2 Dependências Node.js

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 0 |
| LOW | 5 |
| MEDIUM | 21 |
| HIGH | 20 |
| CRITICAL | 1 |
| **Total** | **47** |

---

# 4. Avaliação do runtime

O runtime original utilizava:

```dockerfile
FROM node:24-alpine
```

Foi avaliada a substituição por:

```dockerfile
FROM gcr.io/distroless/nodejs24-debian13:nonroot
```

O objetivo foi reduzir:

- ferramentas desnecessárias;
- superfície de ataque;
- vulnerabilidades;
- tamanho da imagem final.

---

# 5. Migração para Distroless Node 24

A nova imagem de runtime passou a utilizar:

```dockerfile
FROM gcr.io/distroless/nodejs24-debian13:nonroot
```

Entre as principais características do runtime Distroless estão:

- ausência de shell;
- ausência de package manager;
- ausência de npm no runtime;
- ausência de curl;
- execução non-root;
- somente componentes necessários para execução do Node.js.

A imagem foi validada executando diretamente:

```text
server.js
```

por meio do entrypoint nativo da imagem Distroless Node.

---

# 6. Resultado com Distroless

## 6.1 Tamanho

| Métrica | Antes | Distroless | Diferença |
|---|---:|---:|---:|
| Disk Usage | 334 MB | 307 MB | -27 MB |
| Content Size | 80,1 MB | 74,6 MB | -5,5 MB |

Redução aproximada:

```text
Disk Usage:   -8,1%
Content Size: -6,9%
```

---

## 6.2 Usuário de runtime

A imagem Distroless executa com:

```text
UID 65532
```

A aplicação permanece não-root.

A alteração não representa correção de privilégio, pois a imagem original já executava como usuário `node`, mas padroniza o runtime com a variante `nonroot` do Distroless.

---

## 6.3 Vulnerabilidades do sistema operacional

Após a migração:

| Severidade | Antes | Depois |
|---|---:|---:|
| UNKNOWN | 0 | 0 |
| LOW | 12 | 7 |
| MEDIUM | 6 | 10 |
| HIGH | 2 | 0 |
| CRITICAL | 0 | 0 |

Os findings de severidade HIGH do sistema operacional foram eliminados:

```text
HIGH
2 → 0
```

Representando:

```text
100% de redução nos findings HIGH do sistema operacional.
```

---

# 7. Vulnerabilidades Node.js após Distroless

O scan das dependências Node.js também apresentou melhora.

| Severidade | Antes | Depois |
|---|---:|---:|
| UNKNOWN | 0 | 0 |
| LOW | 5 | 3 |
| MEDIUM | 21 | 13 |
| HIGH | 20 | 13 |
| CRITICAL | 1 | 0 |
| Total | 47 | 29 |

Principais resultados:

```text
HIGH
20 → 13

CRITICAL
1 → 0
```

Reduções aproximadas:

```text
HIGH:     -35%
CRITICAL: -100%
```

A redução das vulnerabilidades Node observadas na imagem final deve ser tratada como resultado do conjunto efetivamente presente no runtime Distroless/standalone, e não como atualização das dependências do produto.

---

# 8. Build após migração para Distroless

Foram executados novos benchmarks.

## Build limpo

```text
76,57 s
```

Comparado à baseline:

```text
78,48 s
```

Diferença aproximada:

```text
-2,4%
```

A diferença é pequena e deve ser tratada como variação normal do ambiente de build.

O principal ganho do Distroless está no runtime, não no tempo de compilação.

---

## Build totalmente cacheado

Baseline:

```text
2,26 s
```

Distroless:

```text
2,08 s
```

Diferença:

```text
-0,18 s
```

Também considerada pequena demais para ser atribuída diretamente à troca do runtime.

---

## Build após alteração em código

Baseline:

```text
23,56 s
```

Após alteração:

```text
16,41 s
```

Redução observada:

```text
~30,3%
```

Apesar do ganho observado, essa diferença não deve ser atribuída exclusivamente ao Distroless, já que o runtime é construído apenas após o `next build`.

O resultado deve ser registrado como benchmark observado, considerando possíveis variações de CPU, filesystem e cache interno do Next.js.

---

# 9. Substituição da instalação global do pnpm

O Dockerfile original utilizava:

```dockerfile
RUN npm install -g pnpm@10.33.0
```

Foi identificado que a imagem Node 24 já possui Corepack disponível.

Teste realizado:

```bash
docker run --rm node:24-alpine corepack --version
```

Resultado:

```text
0.35.0
```

O pnpm não estava ativado por padrão.

A configuração foi alterada para:

```dockerfile
RUN corepack enable && \
    corepack prepare pnpm@10.33.0 --activate
```

---

# 10. Benchmark do Corepack

Foi comparado o uso do Corepack com a instalação global via npm.

| Cenário | Tempo |
|---|---:|
| Build anterior | 76,57 s |
| Build com Corepack | 75,87 s |
| Build cacheado com Corepack | 1,90 s |

A diferença de performance foi pequena e não deve ser considerada um ganho significativo.

A decisão de manter Corepack foi baseada principalmente em:

- uso da ferramenta já disponível na imagem Node;
- eliminação da instalação global via npm;
- ativação explícita da versão do pnpm;
- configuração mais alinhada ao ecossistema atual do Node.js.

---

# 11. Avaliação de BuildKit cache para pnpm

Foi avaliado o uso de cache persistente do store do pnpm.

Configuração testada:

```dockerfile
RUN --mount=type=cache,id=atendimento-pnpm-benchmark,target=/pnpm/store \
    pnpm install \
      --frozen-lockfile \
      --store-dir=/pnpm/store
```

---

## 11.1 Resultado

### Store frio

```text
91,44 s
```

### Store previamente populado

```text
160,77 s
```

Em uma das execuções, a etapa:

```text
pnpm install
```

isoladamente consumiu:

```text
82,3 s
```

---

## 11.2 Decisão

O cache mount do store do pnpm foi descartado.

O benchmark não mostrou benefício em relação ao cache tradicional de layers do Docker.

Comparação:

```text
Corepack sem cache mount
~75,87 s

pnpm store frio
91,44 s

pnpm store quente
160,77 s
```

Portanto, foi mantida:

```dockerfile
RUN pnpm install --frozen-lockfile
```

com o cache natural da layer Docker baseada em:

```text
package.json
pnpm-lock.yaml
```

Essa decisão evita complexidade adicional sem benefício mensurável.

---

# 12. Estratégia de cache de dependências

O Dockerfile mantém:

```dockerfile
COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile
```

antes da cópia do código-fonte.

Isso permite que a layer de dependências seja reutilizada enquanto:

```text
package.json
pnpm-lock.yaml
```

não forem alterados.

Mudanças somente em:

```text
src/
```

não invalidam a instalação das dependências.

---

# 13. `.dockerignore` original

A configuração original era:

```dockerignore
node_modules
.next
out
coverage
.env*
.git
*.log
```

Essa abordagem utilizava uma blacklist de arquivos.

Apesar de funcional, qualquer novo arquivo criado no projeto seria incluído no contexto Docker por padrão, a menos que fosse explicitamente adicionado ao `.dockerignore`.

---

# 14. `.dockerignore` refatorado

Foi adotada uma estratégia de **allowlist**.

```dockerignore
**

!package.json
!pnpm-lock.yaml
!pnpm-workspace.yaml

!tsconfig.json
!next.config.ts
!postcss.config.mjs
!components.json

!public/
!public/**

!src/
!src/**
```

O build foi executado e validado com sucesso após a alteração.

Com essa abordagem, somente arquivos explicitamente necessários ao build são enviados ao contexto Docker.

Arquivos como:

```text
.git/
.env*
node_modules/
.next/
coverage/
logs
arquivos de IDE
documentação
arquivos temporários
```

ficam excluídos por padrão.

Isso reduz:

- contexto de build;
- risco de envio acidental de arquivos sensíveis;
- necessidade de manter uma blacklist crescente.

---

# 15. Healthcheck

Não foi adicionado `HEALTHCHECK` ao Dockerfile.

A decisão segue a arquitetura definida para os produtos APAE.

A aplicação será executada em Kubernetes e a saúde dos containers será gerenciada através de:

```text
startupProbe
readinessProbe
livenessProbe
```

O runtime Distroless também não inclui:

```text
curl
wget
shell
```

Adicionar ferramentas apenas para executar healthchecks aumentaria desnecessariamente a superfície da imagem.

Assim:

```text
Dockerfile
→ sem HEALTHCHECK

Kubernetes
→ startupProbe
→ readinessProbe
→ livenessProbe
```

---

# 16. Imagem de build

Foi mantida:

```dockerfile
FROM node:24-alpine
```

para os stages de build.

A imagem Alpine é utilizada somente para:

```text
Corepack
pnpm
instalação de dependências
Next.js build
```

e não é publicada como runtime final.

A manutenção do Alpine no builder foi considerada adequada porque:

- o build funciona corretamente;
- o stage não é utilizado em produção;
- oferece ambiente completo para instalação e compilação;
- não aumenta a superfície de ataque da imagem final.

Caso surjam futuramente incompatibilidades com bibliotecas nativas baseadas em `glibc`, poderá ser avaliado o uso de uma variante `node:24-slim`.

---

# 17. Pinning das imagens

As imagens base foram fixadas por tag e digest.

## Node builder

```text
node:24-alpine
```

Digest:

```text
sha256:e67514e5d0f6c46656005e1b693b2ec9d52e80b641307de684d4a015ba7a4eaf
```

Dockerfile:

```dockerfile
FROM node:24-alpine@sha256:e67514e5d0f6c46656005e1b693b2ec9d52e80b641307de684d4a015ba7a4eaf AS base
```

---

## Distroless runtime

```text
gcr.io/distroless/nodejs24-debian13:nonroot
```

Digest:

```text
sha256:774b7d020b24214835769e24c3544835526cd0288f0b094eae48e8b2c2429a79
```

Dockerfile:

```dockerfile
FROM gcr.io/distroless/nodejs24-debian13:nonroot@sha256:774b7d020b24214835769e24c3544835526cd0288f0b094eae48e8b2c2429a79 AS runner
```

O uso de:

```text
tag + digest
```

mantém a versão legível e garante que diferentes builds utilizem exatamente o mesmo conteúdo da imagem base.

---

# 18. Atualização futura dos digests

O uso de digests exige atualização controlada quando novas versões das imagens forem disponibilizadas.

Está prevista a configuração futura de:

```text
Dependabot
```

ou:

```text
Renovate
```

para abrir Pull Requests automaticamente quando houver novos digests.

Fluxo esperado:

```text
nova imagem base
        ↓
Dependabot/Renovate
        ↓
Pull Request
        ↓
build
        ↓
testes
        ↓
scan de segurança
        ↓
revisão
        ↓
merge
```

---

# 19. Metadados OCI

Foram adicionados labels compatíveis com o padrão OCI para melhorar a rastreabilidade das imagens publicadas no GHCR.

```dockerfile
ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Atendimento Frontend" \
      org.opencontainers.image.description="Frontend do APAE Atendimento" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE-atendimento" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF
```

Esses metadados permitem associar a imagem a:

```text
produto
repositório
versão
commit Git
licença
```

---

# 20. Dockerfile final

```dockerfile
# syntax=docker/dockerfile:1.7

FROM node:24-alpine@sha256:e67514e5d0f6c46656005e1b693b2ec9d52e80b641307de684d4a015ba7a4eaf AS base

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

RUN corepack enable && \
    corepack prepare pnpm@10.33.0 --activate


FROM base AS deps

COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile


FROM base AS builder

ARG NEXT_PUBLIC_API_URL

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN pnpm build


FROM gcr.io/distroless/nodejs24-debian13:nonroot@sha256:774b7d020b24214835769e24c3544835526cd0288f0b094eae48e8b2c2429a79 AS runner

ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Atendimento Frontend" \
      org.opencontainers.image.description="Frontend do APAE Atendimento" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE-atendimento" \
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

EXPOSE 3000

CMD ["server.js"]
```

---

# 21. `.dockerignore` final

```dockerignore
**

!package.json
!pnpm-lock.yaml
!pnpm-workspace.yaml

!tsconfig.json
!next.config.ts
!postcss.config.mjs
!components.json

!public/
!public/**

!src/
!src/**
```

---

# 22. Comparativo final

| Métrica | Antes | Depois | Resultado |
|---|---:|---:|---:|
| Disk Usage | 334 MB | 307 MB | **-8,1%** |
| Content Size | 80,1 MB | 74,6 MB | **-6,9%** |
| OS HIGH | 2 | 0 | **-100%** |
| OS CRITICAL | 0 | 0 | Mantido |
| Node HIGH | 20 | 13 | **-35%** |
| Node CRITICAL | 1 | 0 | **-100%** |
| Runtime UID | 1000 | 65532 | Non-root mantido |
| Shell no runtime | Sim | Não | Removido |
| npm no runtime | Sim | Não | Removido |
| curl no runtime | Sim | Não | Removido |
| Package manager no runtime | `apk` | Não | Removido |
| Build limpo | 78,48 s | 75,87–76,57 s | Sem ganho significativo |
| Build cacheado | 2,26 s | 1,90–2,08 s | Sem ganho significativo |
| Build após alteração em código | 23,56 s | 16,41 s | **-30,3% observado** |
| pnpm global via npm | Sim | Não | Substituído por Corepack |
| Cache mount pnpm | Não | Testado e descartado | Sem benefício |
| Contexto Docker allowlist | Não | Sim | Adicionado |
| Imagens fixadas por digest | Não | Sim | Adicionado |
| OCI labels | Não | Sim | Adicionado |

---

# 23. Principais melhorias

A refatoração resultou principalmente em:

1. redução de aproximadamente 8,1% no Disk Usage;
2. redução de aproximadamente 6,9% no Content Size;
3. eliminação dos findings HIGH do sistema operacional;
4. eliminação do único finding CRITICAL das dependências Node observado no runtime;
5. redução de 35% dos findings HIGH das dependências Node;
6. remoção de shell do runtime;
7. remoção de `apk`;
8. remoção de `curl`;
9. remoção de npm do runtime;
10. runtime baseado em Distroless Node 24;
11. manutenção da execução non-root;
12. substituição da instalação global do pnpm por Corepack;
13. manutenção de `pnpm install --frozen-lockfile`;
14. adoção de `.dockerignore` baseado em allowlist;
15. fixação das imagens base por SHA-256;
16. inclusão de metadados OCI;
17. preparação da imagem para GHCR e Kubernetes.

---

# 24. Otimizações avaliadas e descartadas

Nem toda alteração considerada apresentou benefício.

## Cache mount do store do pnpm

Resultados observados:

```text
Sem cache mount:
~75,87 s

Store frio:
91,44 s

Store quente:
160,77 s
```

A etapa `pnpm install` chegou a:

```text
82,3 s
```

isoladamente.

Por não apresentar melhoria, a configuração foi descartada.

Essa decisão evita adicionar complexidade ao Dockerfile sem ganho mensurável.

---

# 25. Pontos não alterados

Alguns aspectos já estavam adequados no Dockerfile original e foram preservados:

- multi-stage build;
- separação de dependências e builder;
- `pnpm install --frozen-lockfile`;
- Next.js standalone;
- execução non-root;
- cópia somente dos artefatos necessários;
- porta `3000`.

Esses itens não devem ser contabilizados como ganhos da refatoração.

---

# 26. Achados fora do escopo

Durante a análise do `package.json`, foi observado que o projeto possui:

```text
pnpm
```

declarado como dependência da aplicação.

Como o pnpm é uma ferramenta de gerenciamento de pacotes e já passou a ser fornecido no build através do Corepack, essa declaração pode ser revisada pelo time responsável pelo frontend.

A alteração não foi realizada nesta tarefa por pertencer ao escopo de dependências do produto.

---

# 27. Conclusão

A refatoração tornou a imagem do frontend mais enxuta, segura e previsível, mantendo o comportamento esperado da aplicação.

Os principais resultados mensurados foram:

```text
Disk Usage
334 MB → 307 MB

Content Size
80,1 MB → 74,6 MB

OS HIGH
2 → 0

Node HIGH
20 → 13

Node CRITICAL
1 → 0
```

Além dos ganhos quantitativos, o runtime final passou a possuir:

```text
Distroless Node 24
execução non-root
sem shell
sem npm
sem curl
sem package manager
Corepack
imagens fixadas por digest
OCI labels
contexto Docker baseado em allowlist
```

O cache mount do store do pnpm foi testado, medido e descartado por não apresentar benefício.

Com isso, o frontend **APAE Atendimento** passa a possuir uma imagem mais adequada para publicação no GHCR, execução em Kubernetes e integração com a futura pipeline de CI/CD.