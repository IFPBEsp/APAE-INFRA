# Refatoração da Imagem Docker — APAE Geral Backend

## Contexto

Este documento registra a análise, refatoração e validação da imagem Docker do backend **APAE Geral**.

A atividade faz parte da padronização das imagens dos produtos APAE, com foco em segurança, redução da superfície de ataque, redução do tamanho da imagem, execução non-root, builds reproduzíveis, otimização do processo de build, redução do contexto Docker, compatibilidade com CI/CD, preparação para publicação no GHCR e execução em Kubernetes.

---

## 1. Dockerfile original

```dockerfile
# syntax=docker/dockerfile:1.7

# build
FROM maven:3.9-eclipse-temurin-21-alpine AS builder
WORKDIR /workspace

COPY pom.xml ./
RUN mvn -B -q dependency:go-offline

COPY src ./src
RUN mvn -B -q clean package -Dmaven.test.skip=true \
 && cp target/*.jar /workspace/app.jar

# runtime
FROM eclipse-temurin:21-jre-alpine AS runner
WORKDIR /app

RUN apk add --no-cache wget \
 && addgroup -S -g 1001 appgroup \
 && adduser  -S -u 1001 -G appgroup appuser

COPY --from=builder --chown=appuser:appgroup /workspace/app.jar ./app.jar

ENV API_PORT=8080
ENV JAVA_OPTS=""

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/apae-geral/actuator/health 2>/dev/null \
      | grep -q '"status":"UP"' || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
```

A imagem original já possuía multi-stage build, Java 21 e execução non-root. Esses itens não são contabilizados como ganhos introduzidos pela refatoração.

---

## 2. Baseline

Imagem utilizada:

```text
apae-backend:baseline
```

| Métrica | Baseline |
|---|---:|
| Disk Usage | 452 MB |
| Content Size | 151 MB |
| Build limpo | 224,04 s |
| Build totalmente cacheado | 3,79 s |
| Build após alteração em código | 14,62 s |

A camada do JAR possuía aproximadamente **85,5 MB**.

Usuário do runtime:

```text
uid=1001(appuser) gid=1001(appgroup) groups=1001(appgroup)
```

Ferramentas identificadas no runtime:

```text
/opt/java/openjdk/bin/java
/usr/bin/wget
/sbin/apk
```

---

## 3. Vulnerabilidades da imagem original

### Sistema operacional — Alpine 3.24.1

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 0 |
| LOW | 18 |
| MEDIUM | 9 |
| HIGH | 3 |
| CRITICAL | 0 |
| Total | 30 |

### Dependências Java

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 0 |
| LOW | 10 |
| MEDIUM | 25 |
| HIGH | 21 |
| CRITICAL | 5 |
| Total | 61 |

---

## 4. Avaliação do `dependency:go-offline`

Foi testada a remoção de:

```dockerfile
RUN mvn -B -q dependency:go-offline
```

e adotado o build direto com cache Maven do BuildKit:

```dockerfile
RUN --mount=type=cache,id=apae-backend-m2,target=/root/.m2 \
    mvn -B -q package -Dmaven.test.skip=true
```

| Cenário | Baseline | BuildKit cache |
|---|---:|---:|
| Build limpo | 224,04 s | 78,01 s |
| Build cacheado | 3,79 s | 2,46 s |
| Alteração no código | 14,62 s | 6,82 s |

O build limpo caiu aproximadamente **65,2%**, o build cacheado caiu aproximadamente **35,1%** e o cenário de alteração em código caiu aproximadamente **53,4%**.

A remoção de `dependency:go-offline` não causou regressão no build incremental quando combinada ao cache persistente de `/root/.m2`.

---

## 5. Cache Maven com BuildKit

Foi adotado:

```dockerfile
RUN --mount=type=cache,id=apae-backend-m2,target=/root/.m2 \
    mvn -B -q package -Dmaven.test.skip=true \
    && cp target/*.jar /workspace/app.jar
```

O cache BuildKit preserva os artefatos Maven entre builds, evitando downloads repetidos e tornando desnecessária a etapa separada de `dependency:go-offline`.

A remoção de `clean` também foi mantida, pois o stage de build é descartável e não reutiliza um diretório `target` persistente.

---

## 6. Migração do runtime para Distroless

O runtime original:

```dockerfile
FROM eclipse-temurin:21-jre-alpine
```

foi substituído por:

```dockerfile
FROM gcr.io/distroless/java21-debian13:nonroot
```

### Resultado

| Métrica | Antes | Depois | Resultado |
|---|---:|---:|---:|
| Disk Usage | 452 MB | 423 MB | **-6,4%** |
| Content Size | 151 MB | 140 MB | **-7,3%** |
| OS HIGH | 3 | 1 | **-66,7%** |
| OS CRITICAL | 0 | 0 | Mantido |
| Java HIGH | 21 | 21 | Sem alteração |
| Java CRITICAL | 5 | 5 | Sem alteração |

No Distroless, o total de findings de sistema operacional passou de 30 para 47, portanto não se deve afirmar que o total de vulnerabilidades diminuiu. O ganho concreto foi a redução dos findings **HIGH** do sistema operacional e a redução da superfície de ataque.

O usuário passou a ser explicitamente:

```text
65532:65532
```

Foram removidos do runtime: shell, `apk` e `wget`.

---

## 7. Vulnerabilidades da imagem final

### Sistema operacional — Debian 13.6

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 2 |
| LOW | 18 |
| MEDIUM | 26 |
| HIGH | 1 |
| CRITICAL | 0 |
| Total | 47 |

### Dependências Java

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 0 |
| LOW | 10 |
| MEDIUM | 25 |
| HIGH | 21 |
| CRITICAL | 5 |
| Total | 61 |

Os findings Java permaneceram inalterados, indicando que pertencem às dependências da aplicação empacotadas no JAR e não à imagem base.

---

## 8. Pinning das imagens

Builder:

```text
maven:3.9-eclipse-temurin-21-alpine@sha256:65353f527c86cb23187c8233475713e15067e8d36220d18863c379680698fe85
```

Runtime:

```text
gcr.io/distroless/java21-debian13:nonroot@sha256:bb0b3c7edc4417acdf76ea0f52bb5fae28881fe05aae6cc55af4cc4cb0200d2d
```

Foi utilizado o digest do índice multi-arquitetura.

---

## 9. Metadados OCI e rastreabilidade no GHCR

```dockerfile
ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Geral Backend" \
      org.opencontainers.image.description="Backend do sistema APAE" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF
```

O workflow de publicação no GHCR foi ajustado para fornecer esses argumentos durante o build:

```yaml
build-args: |
  APP_VERSION=${{ steps.meta.outputs.version }}
  VCS_REF=${{ github.sha }}
```

A imagem publicada foi validada com `docker inspect`.

Resultado observado:

```text
org.opencontainers.image.version=dev
org.opencontainers.image.revision=f34a7a45e1416338d3a8eeb6978fbe96fa381fce
```

Isso garante rastreabilidade entre a imagem publicada no GHCR e o commit que a originou.

---

## 10. `.dockerignore`

```dockerignore
**

!pom.xml

!src/
!src/**
```

O contexto Docker do backend passa a conter apenas o `pom.xml` e o código-fonte necessário para o build.

---

## 11. Herança do `ENTRYPOINT` da imagem Distroless

A imagem base:

```text
gcr.io/distroless/java21-debian13:nonroot
```

já define:

```text
ENTRYPOINT ["/usr/bin/java", "-jar"]
```

Por isso, não é necessário redefinir o `ENTRYPOINT` no Dockerfile da aplicação.

A configuração foi simplificada para:

```dockerfile
CMD ["/app/app.jar"]
```

A composição final do container foi validada com:

```bash
docker inspect apae-backend:final \
  --format 'Entrypoint={{json .Config.Entrypoint}} Cmd={{json .Config.Cmd}}'
```

Resultado:

```text
Entrypoint=["/usr/bin/java","-jar"] Cmd=["/app/app.jar"]
```

A execução efetiva permanece:

```text
/usr/bin/java -jar /app/app.jar
```

---

## 12. Dockerfile final

```dockerfile
# syntax=docker/dockerfile:1.7

FROM maven:3.9-eclipse-temurin-21-alpine@sha256:65353f527c86cb23187c8233475713e15067e8d36220d18863c379680698fe85 AS builder

WORKDIR /workspace

COPY pom.xml .
COPY src ./src

RUN --mount=type=cache,id=apae-backend-m2,target=/root/.m2 \
    mvn -B -q package -Dmaven.test.skip=true \
    && cp target/*.jar /workspace/app.jar

FROM gcr.io/distroless/java21-debian13:nonroot@sha256:bb0b3c7edc4417acdf76ea0f52bb5fae28881fe05aae6cc55af4cc4cb0200d2d AS runner

ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Geral Backend" \
      org.opencontainers.image.description="Backend do sistema APAE" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF

WORKDIR /app

COPY --from=builder --chown=65532:65532 /workspace/app.jar ./app.jar

ENV API_PORT=8080

USER 65532:65532

EXPOSE 8080

CMD ["/app/app.jar"]
```

---

## 13. Conclusão

Principais resultados:

```text
Disk Usage:    452 MB → 423 MB
Content Size:  151 MB → 140 MB
OS HIGH:       3 → 1
Build limpo:   224,04 s → 78,01 s
Source-change: 14,62 s → 6,82 s
```

A estratégia final utiliza Maven Alpine no builder, cache BuildKit para `/root/.m2`, Distroless Java 21 nonroot no runtime, pinning por digest, labels OCI completos, rastreabilidade validada no GHCR e `.dockerignore` em allowlist.

O comando final do backend herda o `ENTRYPOINT ["/usr/bin/java", "-jar"]` da própria imagem Distroless e define apenas:

```dockerfile
CMD ["/app/app.jar"]
```
