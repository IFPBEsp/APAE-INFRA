# Refatoração da Imagem Docker — APAE Gestão Escolar Backend

## Contexto

Este documento registra a análise, refatoração e validação da imagem Docker do backend **APAE Gestão Escolar**.

A atividade faz parte da padronização das imagens dos produtos APAE, com foco em segurança, redução da superfície de ataque, redução do tamanho da imagem, execução non-root, builds reproduzíveis, otimização do processo de build, redução do contexto Docker, compatibilidade com CI/CD, preparação para publicação no GHCR e execução em Kubernetes.

---

## 1. Dockerfile original

```dockerfile
FROM maven:3.9-eclipse-temurin-21-alpine AS builder

WORKDIR /app

COPY pom.xml .
RUN mvn dependency:go-offline -B -q

COPY src ./src
RUN mvn clean package -DskipTests -B -q

FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

LABEL org.opencontainers.image.source=https://github.com/IFPBEsp/APAE-gestao-escolar
LABEL org.opencontainers.image.description="APAE Gestão Escolar - Backend (Spring Boot)"
LABEL org.opencontainers.image.licenses=MIT

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=builder --chown=appuser:appgroup /app/target/*.jar app.jar

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:8080/gestao-escolar/actuator/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
```

A imagem original já possuía multi-stage build, Java 21, execução non-root, labels OCI básicos e separação entre build e runtime. Esses itens não são contabilizados como ganhos introduzidos pela refatoração.

---

## 2. Baseline

Imagem utilizada:

```text
gestao-escolar-backend:baseline
```

| Métrica | Baseline |
|---|---:|
| Disk Usage | 444 MB |
| Content Size | 148 MB |
| Build limpo | 127,83 s |
| Build totalmente cacheado | 1,32 s |
| Build após alteração em código | 14,49 s |

A camada do JAR possuía aproximadamente **82 MB**.

Usuário do runtime:

```text
uid=100(appuser) gid=101(appgroup) groups=101(appgroup)
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
| LOW | 15 |
| MEDIUM | 42 |
| HIGH | 30 |
| CRITICAL | 7 |
| Total | 94 |

---

## 4. Avaliação do `dependency:go-offline`

Foi testada a remoção de:

```dockerfile
RUN mvn dependency:go-offline -B -q
```

mantendo apenas:

```dockerfile
RUN mvn package -DskipTests -B -q
```

| Cenário | Baseline | Sem `go-offline` |
|---|---:|---:|
| Build limpo | 127,83 s | 46,28 s |
| Build cacheado | 1,32 s | 0,96 s |
| Alteração no código | 14,49 s | 57,73 s |

A remoção reduziu fortemente o build limpo, mas causou regressão no build incremental.

---

## 5. Cache Maven com BuildKit

Foi adotado:

```dockerfile
RUN --mount=type=cache,id=gestao-escolar-m2,target=/root/.m2 \
    mvn package -DskipTests -B -q
```

| Cenário | Baseline | BuildKit cache |
|---|---:|---:|
| Build limpo | 127,83 s | 48,63 s |
| Build cacheado | 1,32 s | 1,66 s |
| Alteração no código | 14,49 s | 13,61 s |

O build limpo caiu aproximadamente **62%**, sem regressão no cenário incremental.

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
| Disk Usage | 444 MB | 417 MB | **-6,1%** |
| Content Size | 148 MB | 137 MB | **-7,4%** |
| OS HIGH | 3 | 0 | **-100%** |
| OS CRITICAL | 0 | 0 | Mantido |
| Java HIGH | 30 | 30 | Sem alteração |
| Java CRITICAL | 7 | 7 | Sem alteração |

No Distroless, o total de findings de sistema operacional passou de 30 para 43, portanto não se deve afirmar que o total de vulnerabilidades diminuiu. O ganho concreto foi a eliminação dos findings **HIGH** do sistema operacional e a redução da superfície de ataque.

O usuário passou a ser explicitamente:

```text
65532:65532
```

Foram removidos do runtime: shell, `apk` e `wget`.

---

## 7. Healthcheck

O `HEALTHCHECK` foi removido do Dockerfile. A saúde da aplicação será gerenciada pelo Kubernetes com:

```text
startupProbe
readinessProbe
livenessProbe
```

Adicionar `wget`, `curl` ou shell apenas para healthcheck aumentaria desnecessariamente a superfície da imagem Distroless.

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

---

## 9. Metadados OCI

```dockerfile
ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Gestão Escolar" \
      org.opencontainers.image.description="Backend do APAE Gestão Escolar" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE-gestao-escolar" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF
```

Validação realizada com:

```text
org.opencontainers.image.version=dev
org.opencontainers.image.revision=9a42d376fd18a0aa22c83534905c98fc2d927bfc
```

---

## 10. `.dockerignore`

```dockerignore
**

!pom.xml

!src/
!src/**
```

---

## 11. Dockerfile final

```dockerfile
# syntax=docker/dockerfile:1.7

FROM maven:3.9-eclipse-temurin-21-alpine@sha256:65353f527c86cb23187c8233475713e15067e8d36220d18863c379680698fe85 AS builder

WORKDIR /app

COPY pom.xml .
COPY src ./src

RUN --mount=type=cache,id=gestao-escolar-m2,target=/root/.m2 \
    mvn package -DskipTests -B -q

FROM gcr.io/distroless/java21-debian13:nonroot@sha256:bb0b3c7edc4417acdf76ea0f52bb5fae28881fe05aae6cc55af4cc4cb0200d2d AS runtime

ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Gestão Escolar" \
      org.opencontainers.image.description="Backend do APAE Gestão Escolar" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE-gestao-escolar" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF

WORKDIR /app

COPY --from=builder --chown=65532:65532 /app/target/*.jar app.jar

USER 65532:65532

EXPOSE 8080

ENTRYPOINT ["/usr/bin/java"]
CMD ["-jar", "app.jar"]
```

---

## 12. Conclusão

Principais resultados:

```text
Disk Usage:    444 MB → 417 MB
Content Size:  148 MB → 137 MB
OS HIGH:       3 → 0
Build limpo:   127,83 s → 48,63 s
Source-change: 14,49 s → 13,61 s
```

A estratégia final utiliza Maven Alpine no builder, cache BuildKit para `/root/.m2`, Distroless Java 21 nonroot no runtime, pinning por digest, labels OCI completos e `.dockerignore` em allowlist.
