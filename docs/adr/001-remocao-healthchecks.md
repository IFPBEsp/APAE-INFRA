# ADR — Remoção de HEALTHCHECK das imagens Distroless

## Status

Aceito

## Contexto

As imagens Docker do backend e frontend do APAE estão sendo migradas para runtimes Distroless.

Essas imagens não possuem ferramentas como:

- shell;
- `wget`;
- `curl`;
- gerenciador de pacotes.

Os `HEALTHCHECK` existentes dependiam dessas ferramentas para realizar requisições HTTP contra os serviços.

No backend, o endpoint de saúde já existe:

```text
/apae-geral/actuator/health
```

A arquitetura de produção prevista para os serviços utiliza Kubernetes/K3s, onde a verificação de saúde será realizada através de:

```text
startupProbe
readinessProbe
livenessProbe
```

As probes HTTP são executadas pelo kubelet e não dependem de ferramentas instaladas dentro do container.

No momento desta decisão, os manifests Kubernetes contendo essas probes ainda não estão implementados.

Issue relacionada:

```text
APAE-INFRA#37 — Criar manifests Kubernetes base para os serviços do repositório APAE
```

## Decisão

Remover os `HEALTHCHECK` dos Dockerfiles das imagens Distroless e transferir a responsabilidade de verificação de saúde para Kubernetes/K3s.

Não serão adicionados `wget`, `curl`, shell ou ferramentas equivalentes às imagens apenas para suportar healthchecks Docker.

Até que os manifests Kubernetes e suas probes sejam implementados, os containers continuarão funcionando normalmente, porém haverá uma lacuna temporária na verificação automatizada de saúde da aplicação.

Nesse período, o runtime Docker continuará detectando apenas o estado do processo principal do container (`running`/`exited`), sem realizar uma verificação HTTP de saúde da aplicação.

## Consequências

### Positivas

- menor superfície de ataque;
- runtime Distroless permanece mínimo;
- elimina ferramentas desnecessárias em produção;
- centraliza a política de saúde no orquestrador;
- evita duplicação entre Docker `HEALTHCHECK` e Kubernetes probes.

### Negativas

Enquanto a issue `APAE-INFRA#37` não for concluída:

- não haverá verificação HTTP automática de saúde no nível do container;
- um processo pode permanecer em execução mesmo que a aplicação esteja degradada;
- readiness e liveness ainda não serão avaliadas automaticamente.

Essa lacuna é considerada temporária e será encerrada com a implementação das probes Kubernetes.

## Implementação futura

Os manifests Kubernetes deverão utilizar, conforme aplicável:

```text
startupProbe
readinessProbe
livenessProbe
```

Para o backend, o endpoint previsto é:

```text
/apae-geral/actuator/health
```

A configuração das probes será tratada na issue:

```text
APAE-INFRA#37
```

## Alternativas consideradas

### Manter HEALTHCHECK no Dockerfile

Exigiria adicionar `wget`, `curl` ou outra ferramenta ao runtime Distroless.

Rejeitado por aumentar a superfície da imagem apenas para healthcheck.

### Utilizar imagem não-Distroless

Permitiria manter o healthcheck atual, mas perderia os benefícios de redução de superfície de ataque obtidos com Distroless.

Rejeitado.

### Remover HEALTHCHECK e utilizar probes Kubernetes

Escolhido por estar alinhado à arquitetura de produção prevista para o projeto.
