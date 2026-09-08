# Refatoração da Imagem Docker — APAE Atendimento Backend

## Contexto

Este documento registra a análise, refatoração e validação da imagem Docker do backend **APAE Atendimento**.

A atividade faz parte da padronização das imagens dos produtos APAE, com foco em:

- segurança;
- redução da superfície de ataque;
- builds reproduzíveis;
- otimização de tempo de build;
- redução do tamanho da imagem;
- execução non-root;
- compatibilidade com CI/CD;
- preparação para execução em Kubernetes;
- padronização das imagens publicadas no GHCR.

Além das alterações realizadas, foram coletadas métricas antes e depois da refatoração para demonstrar quantitativamente o impacto das mudanças.

---

# 1. Dockerfile original

O backend utilizava inicialmente:

```dockerfile
FROM maven:3.9.9-eclipse-temurin-21 AS build

WORKDIR /app

COPY pom.xml .
RUN mvn dependency:go-offline -B

COPY src ./src

RUN mvn clean package -DskipTests

FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

RUN apk add --no-cache curl

COPY --from=build /app/target/*.jar app.jar

EXPOSE 8080

USER 1001

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```

A imagem já utilizava **multi-stage build**, portanto essa característica foi preservada e não deve ser contabilizada como melhoria introduzida pela refatoração.

---

# 2. Baseline

Antes de qualquer alteração, foi construída a imagem:

```text
atendimento-backend:baseline
```

## 2.1 Tamanho da imagem

| Métrica | Baseline |
|---|---:|
| Disk Usage | 476 MB |
| Content Size | 163 MB |

O JAR da aplicação representava aproximadamente:

```text
98,3 MB
```

da imagem.

---

## 2.2 Tempo de build

Foram medidos diferentes cenários.

| Cenário | Tempo |
|---|---:|
| Build sem cache | 445,04 s |
| Build completamente cacheado | ~0,32 s |
| Alteração somente em `src` | 25,42 s |

O cenário de alteração apenas no código-fonte foi utilizado como referência para builds incrementais.

---

## 2.3 Usuário de runtime

Foi executado:

```bash
docker run --rm \
  --entrypoint id \
  atendimento-backend:baseline
```

Resultado:

```text
uid=1001 gid=0(root) groups=0(root)
```

Apesar de o processo não utilizar UID `0`, o container ainda executava associado ao grupo `root`.

O motivo era a definição:

```dockerfile
USER 1001
```

sem a definição explícita de um grupo não privilegiado.

---

## 2.4 Ferramentas presentes no runtime

A imagem original possuía:

```text
Java
curl
```

Maven e `javac` não estavam presentes na imagem final, demonstrando que a separação entre build e runtime já estava funcionando corretamente.

---

# 3. Vulnerabilidades da imagem original

Foi realizado scan com Trivy.

## 3.1 Sistema operacional

Imagem baseada em Alpine.

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 0 |
| LOW | 18 |
| MEDIUM | 9 |
| HIGH | 3 |
| CRITICAL | 0 |

---

## 3.2 Dependências Java

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 0 |
| LOW | 10 |
| MEDIUM | 43 |
| HIGH | 34 |
| CRITICAL | 5 |
| **Total** | **92** |

As vulnerabilidades Java fazem parte das dependências empacotadas no JAR e, portanto, não são solucionadas apenas pela troca da imagem base.

A revisão dessas dependências foi registrada separadamente para avaliação do time responsável pelo produto.

---

# 4. Avaliação do runtime

Durante a análise foram comparadas diferentes estratégias de runtime.

Foram avaliados:

- Eclipse Temurin Alpine;
- Google Distroless Java;
- Chainguard JRE.

---

# 5. Migração para Distroless

O runtime foi alterado de:

```dockerfile
FROM eclipse-temurin:21-jre-alpine
```

para:

```dockerfile
FROM gcr.io/distroless/java21-debian13:nonroot
```

A imagem Distroless possui como características relevantes:

- ausência de shell;
- ausência de package manager;
- runtime Java mínimo;
- execução non-root;
- menor quantidade de componentes disponíveis no container.

Isso reduz a superfície de ataque da imagem e dificulta a utilização do container para execução de ferramentas não necessárias à aplicação.

---

# 6. Resultado com Distroless

## 6.1 Tamanho

| Métrica | Antes | Distroless | Diferença |
|---|---:|---:|---:|
| Disk Usage | 476 MB | 447 MB | -29 MB |
| Content Size | 163 MB | 151 MB | -12 MB |

Redução aproximada:

```text
Disk Usage:   -6,1%
Content Size: -7,4%
```

---

## 6.2 Usuário

O runtime Distroless `nonroot` executa com:

```text
UID 65532
```

Substituindo a situação anterior:

```text
UID 1001
GID 0 (root)
```

por execução explicitamente não privilegiada.

---

## 6.3 Vulnerabilidades do sistema operacional

Após a alteração:

| Severidade | Quantidade |
|---|---:|
| UNKNOWN | 3 |
| LOW | 18 |
| MEDIUM | 22 |
| HIGH | 0 |
| CRITICAL | 0 |

Embora o número total de findings do sistema operacional não tenha diminuído, os findings de maior severidade apresentaram melhora significativa.

```text
HIGH:     3 → 0
CRITICAL: 0 → 0
```

Isso representa redução de:

```text
100% dos findings HIGH do sistema operacional.
```

As vulnerabilidades Java permaneceram:

```text
LOW:      10
MEDIUM:   43
HIGH:     34
CRITICAL: 5
```

confirmando que elas pertencem às dependências da aplicação e não à imagem de runtime.

---

# 7. Comparação com Chainguard

Também foi construída uma imagem experimental utilizando Chainguard JRE.

## Resultado

| Métrica | Distroless | Chainguard |
|---|---:|---:|
| Disk Usage | 447 MB | 628 MB |
| Content Size | 151 MB | 198 MB |
| Runtime UID | 65532 | 65532 |
| OS HIGH | 0 | 0 |
| OS CRITICAL | 0 | 0 |
| Java HIGH | 34 | 34 |
| Java CRITICAL | 5 | 5 |

A imagem Chainguard apresentou:

```text
+181 MB de Disk Usage
+47 MB de Content Size
```

Equivalente aproximadamente a:

```text
+40,5% de Disk Usage
+31,1% de Content Size
```

em relação à imagem Distroless utilizada no teste.

Não foi identificado ganho de segurança relevante no scan que justificasse essa diferença.

Por isso, foi mantido:

```text
Google Distroless Java 21
```

como runtime do backend.

---

# 8. Análise do tempo de build Maven

A Dockerfile original utilizava:

```dockerfile
COPY pom.xml .

RUN mvn dependency:go-offline -B

COPY src ./src

RUN mvn clean package -DskipTests
```

A intenção dessa estratégia era permitir cache das dependências antes da compilação.

Durante o benchmark foi identificado, porém, que a etapa:

```text
mvn dependency:go-offline
```

era o principal gargalo do processo.

---

## 8.1 Medição por etapa

BuildKit apresentou:

```text
dependency:go-offline
348,6 s
```

enquanto:

```text
mvn clean package -DskipTests
18,8 s
```

O `dependency:go-offline` representava aproximadamente:

```text
93% do tempo gasto nas etapas Maven observadas nesse build.
```

Também foram observadas resoluções diferentes de artefatos entre `go-offline` e `package`, demonstrando que a preparação offline não eliminava completamente novas resoluções realizadas durante o empacotamento.

---

# 9. Substituição de `go-offline` por BuildKit cache mount

A estratégia foi alterada para:

```dockerfile
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B package -DskipTests
```

O repositório Maven passa a ser persistido através do cache do BuildKit:

```text
/root/.m2
```

sem integrar esses artefatos à imagem final.

---

# 10. Resultado da otimização do build

Foram executados novos benchmarks sem `dependency:go-offline`.

## Build com cache inicialmente frio

```text
104,00 s
```

## Segunda execução

```text
129,61 s
```

A variação entre as duas execuções demonstra influência de fatores externos como:

- rede;
- resolução Maven;
- utilização de CPU;
- metadata dos repositórios.

Mesmo considerando essa variação, ambos os resultados ficaram significativamente abaixo dos builds anteriores na faixa de 440–515 segundos.

---

## 10.1 Comparação

Um dos builds Distroless anteriores havia apresentado:

```text
515,98 s
```

Após a remoção do `go-offline`:

```text
104,00 s
```

Redução observada:

```text
~79,8%
```

Considerando a segunda execução:

```text
129,61 s
```

a redução ainda foi aproximadamente:

```text
~74,9%
```

Devido à variação de ambiente e rede, o resultado deve ser registrado como uma faixa:

```text
redução aproximada de 75–80% no benchmark observado.
```

---

# 11. Build após alteração no código-fonte

Foi realizada uma alteração em apenas um arquivo dentro de:

```text
src/
```

e um novo build foi executado utilizando o cache.

Resultado:

```text
12,83 s
```

A baseline para alteração apenas em código era:

```text
25,42 s
```

Comparação:

| Cenário | Antes | Depois |
|---|---:|---:|
| Alteração somente em `src` | 25,42 s | 12,83 s |

Redução aproximada:

```text
49,5%
```

Esse cenário é especialmente relevante por representar builds incrementais comuns durante desenvolvimento e CI.

---

# 12. Remoção de `clean`

O comando foi simplificado de:

```bash
mvn clean package -DskipTests
```

para:

```bash
mvn package -DskipTests
```

Dentro do stage de build, o filesystem utilizado começa de um estado controlado e não possui um `target/` antigo proveniente de builds locais.

A etapa `clean`, portanto, não é necessária para garantir a integridade do artefato neste fluxo.

---

# 13. `.dockerignore`

Foi adotada uma estratégia de **allowlist**, permitindo ao contexto Docker somente os arquivos realmente utilizados pelo build.

```dockerignore
**

!pom.xml
!src/
!src/**
```

Dessa forma, arquivos como:

```text
.git/
.env
.idea/
.vscode/
logs
documentação
artefatos locais
arquivos temporários
```

não são enviados ao contexto de build por padrão.

A abordagem também reduz o risco de envio acidental de arquivos sensíveis.

---

# 14. Healthcheck

Não foi adicionado `HEALTHCHECK` ao Dockerfile.

A decisão é intencional.

O produto será executado em Kubernetes, onde a saúde da aplicação deverá ser controlada através de:

```text
startupProbe
readinessProbe
livenessProbe
```

Isso permite distinguir:

```text
aplicação inicializada
aplicação disponível para receber tráfego
processo ainda saudável
```

O runtime Distroless também não inclui `curl`, `wget` ou shell, portanto implementar um healthcheck HTTP dentro da própria imagem exigiria adicionar ferramentas extras ao runtime.

Isso iria contra o objetivo de manter uma imagem mínima.

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

# 15. Execução Java

A imagem original utilizava:

```dockerfile
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```

A nova imagem utiliza execução direta:

```dockerfile
ENTRYPOINT ["/usr/bin/java"]
CMD ["-jar", "app.jar"]
```

Isso elimina a necessidade de shell e garante que o Java seja o processo principal do container.

Configurações específicas de JVM deverão ser fornecidas pelo ambiente através de:

```text
JAVA_TOOL_OPTIONS
```

e não hardcoded na imagem.

Exemplo futuro no Kubernetes:

```yaml
env:
  - name: JAVA_TOOL_OPTIONS
    value: "-XX:MaxRAMPercentage=75.0"
```

Os valores serão definidos de acordo com os recursos atribuídos ao Pod.

---

# 16. Pinning das imagens

As imagens base foram fixadas por versão e digest.

## Maven

```text
maven:3.9.9-eclipse-temurin-21-alpine
```

Digest:

```text
sha256:5a8b906c4faa11d33f6c74758f67db8eac25441e14b0729f6d50ff78992be58a
```

## Distroless

```text
gcr.io/distroless/java21-debian13:nonroot
```

Digest:

```text
sha256:bb0b3c7edc4417acdf76ea0f52bb5fae28881fe05aae6cc55af4cc4cb0200d2d
```

O uso de:

```text
tag + digest
```

permite manter a versão legível no Dockerfile enquanto garante que builds diferentes utilizem exatamente a mesma imagem base.

Isso evita mudanças silenciosas causadas pela atualização de tags no registry.

---

# 17. Atualização futura dos digests

O pinning significa que atualizações das imagens base não serão automaticamente incorporadas.

Portanto, deverá ser configurada futuramente uma ferramenta como:

```text
Dependabot
```

ou:

```text
Renovate
```

para detectar novos digests e abrir Pull Requests de atualização.

O fluxo esperado será:

```text
nova imagem base
        ↓
Dependabot/Renovate
        ↓
Pull Request
        ↓
CI
        ↓
scan de segurança
        ↓
revisão
        ↓
merge
```

---

# 18. Metadados OCI

Foram adicionados metadados utilizando labels padronizados OCI.

Labels estáticos:

```dockerfile
LABEL org.opencontainers.image.title="APAE Atendimento" \
      org.opencontainers.image.description="Backend do APAE Atendimento" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE-atendimento" \
      org.opencontainers.image.licenses="MIT"
```

Também foram adicionados:

```text
version
revision
```

através de build arguments.

```dockerfile
ARG APP_VERSION
ARG VCS_REF
```

e:

```dockerfile
org.opencontainers.image.version=$APP_VERSION
org.opencontainers.image.revision=$VCS_REF
```

Isso permitirá relacionar a imagem publicada no GHCR com:

```text
versão da aplicação
commit Git
repositório de origem
```

---

# 19. Dockerfile final

```dockerfile
# syntax=docker/dockerfile:1.7

FROM maven:3.9.9-eclipse-temurin-21-alpine@sha256:5a8b906c4faa11d33f6c74758f67db8eac25441e14b0729f6d50ff78992be58a AS build

WORKDIR /app

COPY pom.xml .
COPY src ./src

RUN --mount=type=cache,target=/root/.m2 \
    mvn -B package -DskipTests


FROM gcr.io/distroless/java21-debian13:nonroot@sha256:bb0b3c7edc4417acdf76ea0f52bb5fae28881fe05aae6cc55af4cc4cb0200d2d AS runtime

ARG APP_VERSION
ARG VCS_REF

LABEL org.opencontainers.image.title="APAE Atendimento" \
      org.opencontainers.image.description="Backend do APAE Atendimento" \
      org.opencontainers.image.source="https://github.com/IFPBEsp/APAE-atendimento" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF

WORKDIR /app

COPY --from=build --chown=65532:65532 \
    /app/target/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["/usr/bin/java"]
CMD ["-jar", "app.jar"]
```

---

# 20. `.dockerignore` final

```dockerignore
**

!pom.xml
!src/
!src/**
```

---

# 21. Comparativo final

| Métrica | Antes | Depois | Resultado |
|---|---:|---:|---:|
| Disk Usage | 476 MB | 447 MB | **-6,1%** |
| Content Size | 163 MB | 151 MB | **-7,4%** |
| OS HIGH | 3 | 0 | **-100%** |
| OS CRITICAL | 0 | 0 | Mantido |
| Java HIGH | 34 | 34 | Sem alteração |
| Java CRITICAL | 5 | 5 | Sem alteração |
| Runtime UID | 1001 | 65532 | Non-root |
| Runtime GID | root | non-root | **Corrigido** |
| Shell no runtime | Sim | Não | Removido |
| `curl` no runtime | Sim | Não | Removido |
| Package manager no runtime | `apk` | Não | Removido |
| Build após alteração em `src` | 25,42 s | 12,83 s | **-49,5%** |
| Build limpo observado | ~440–516 s | ~104–130 s | **~75–80% menor** |
| Imagens base imutáveis | Não | Sim | Digest SHA-256 |
| OCI labels | Não | Sim | Adicionado |

---

# 22. Principais melhorias

A refatoração resultou principalmente em:

1. redução do tamanho da imagem;
2. eliminação dos findings HIGH do sistema operacional observados no baseline;
3. runtime efetivamente non-root;
4. remoção de shell e package manager;
5. remoção de ferramentas desnecessárias como `curl`;
6. redução significativa do tempo de build Maven;
7. utilização de cache persistente do BuildKit para `.m2`;
8. redução de aproximadamente 49,5% no build após alteração de código;
9. contexto Docker baseado em allowlist;
10. builds mais reproduzíveis através de digest SHA-256;
11. rastreabilidade através de metadados OCI;
12. preparação da imagem para publicação no GHCR e execução em Kubernetes.

---

# 23. Pontos não alterados

Algumas características já estavam corretas no Dockerfile original e foram preservadas:

- multi-stage build;
- separação entre ambiente Maven e runtime;
- somente o JAR sendo enviado ao stage final;
- porta `8080` declarada.

Esses itens não devem ser apresentados como ganhos introduzidos pela refatoração.

---

# 24. Achados fora do escopo

Durante a análise foram identificadas possíveis melhorias nas dependências Java da aplicação.

Entre elas:

```text
OkHttp 4.11.0
AWS SDK S3
```

Essas alterações não foram realizadas nesta atividade porque pertencem ao domínio funcional do backend.

Os achados foram documentados separadamente e deverão ser avaliados pelo time responsável pelo produto.

---

# 25. Conclusão

A refatoração manteve o comportamento esperado da aplicação enquanto tornou a imagem mais adequada para um ambiente de produção baseado em containers e Kubernetes.

Os principais resultados mensurados foram:

```text
Disk Usage
476 MB → 447 MB

Content Size
163 MB → 151 MB

OS HIGH
3 → 0

Build incremental
25,42 s → 12,83 s

Build limpo observado
~440–516 s → ~104–130 s
```

Além dos ganhos quantitativos, a nova imagem possui:

```text
runtime Distroless
execução non-root
sem shell
sem package manager
BuildKit cache
imagens fixadas por digest
OCI labels
contexto Docker mínimo
```

Com isso, o backend **APAE Atendimento** passa a possuir uma imagem mais segura, previsível, rastreável e adequada à futura pipeline de CI/CD e ao ambiente Kubernetes.