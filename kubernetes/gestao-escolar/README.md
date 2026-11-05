# Gestão Escolar — manifests Kubernetes

A base reúne frontend (Next.js, porta 3000) e backend (Spring Boot, porta 8080).
Cada serviço contém Deployment, Service `ClusterIP` e ConfigMap, e aplica o
componente compartilhado `base/components/security`.

## Contrato com as imagens

As referências abaixo usam o commit
[`65f61f5251a56bb3971a433bc7d621ebcb02e14f` de APAE-gestao-escolar](https://github.com/IFPBEsp/APAE-gestao-escolar/tree/65f61f5251a56bb3971a433bc7d621ebcb02e14f),
consultado durante os ajustes do PR #81.

- **Usuário:** os Dockerfiles de [frontend](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/65f61f5251a56bb3971a433bc7d621ebcb02e14f/app/Dockerfile)
  e [backend](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/65f61f5251a56bb3971a433bc7d621ebcb02e14f/api/Dockerfile)
  usam imagens Distroless e `USER 65532:65532`. Os Deployments explicitam esses
  IDs por meio do componente compartilhado. O `fsGroup: 65532` permite escrita nos volumes `emptyDir`.
- **Filesystem:** o componente mantém `readOnlyRootFilesystem: true`. Ambos os
  serviços recebem `/tmp` gravável para arquivos temporários (incluindo os do
  Java/Tomcat). O frontend também recebe `/app/.next/cache` gravável. Esses
  volumes são efêmeros; não servem para persistência de dados.
- **URL pública da API:** o [cliente Axios](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/65f61f5251a56bb3971a433bc7d621ebcb02e14f/app/src/services/api.ts)
  usa `NEXT_PUBLIC_API_URL`. O [Dockerfile do frontend](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/65f61f5251a56bb3971a433bc7d621ebcb02e14f/app/Dockerfile)
  define `/gestao-escolar/api` antes de `npm run build`, e o
  [workflow de publicação](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/65f61f5251a56bb3971a433bc7d621ebcb02e14f/.github/workflows/docker-publish.yml)
  passa esse mesmo build arg. A variável foi retirada do ConfigMap porque sua
  alteração em runtime não reconfigura o bundle. Outra URL exige rebuild.
- **Probe do frontend:** `/gestao-escolar` corresponde ao `basePath` de
  [`next.config.js`](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/65f61f5251a56bb3971a433bc7d621ebcb02e14f/app/next.config.js).
- **Probe do backend:** `/gestao-escolar/actuator/health` combina o
  `server.servlet.context-path=/gestao-escolar` com o Actuator habilitado em
  [`application.properties`](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/65f61f5251a56bb3971a433bc7d621ebcb02e14f/api/src/main/resources/application.properties).
  O caminho `/actuator/health` é liberado sem autenticação em
  [`SecurityConfig.java`](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/65f61f5251a56bb3971a433bc7d621ebcb02e14f/api/src/main/java/com/apae/gestao/config/SecurityConfig.java)
  (os matchers são relativos ao contexto da aplicação).

As imagens usam a tag `dev`, conforme o padrão de APAE Geral. O workflow
[reutilizável de publicação](https://github.com/IFPBEsp/APAE-INFRA/blob/dev/.github/workflows/docker-build-publish-image.yml)
na branch `dev` publica essa tag. O kube-linter rejeita `latest`. Antes da
ativação, conferir a revisão efetivamente publicada; a tag `dev` é mutável.

## Validação dos manifests

A pipeline [k8s-lint.yml](../../.github/workflows/k8s-lint.yml) inclui
`kubernetes/gestao-escolar/base` na renderização e validação do Kustomize.
Para reproduzir localmente, a partir da raiz do repositório:

```bash
yamllint -d '{extends: relaxed, rules: {document-start: disable, line-length: disable}}' kubernetes/gestao-escolar
kubectl kustomize kubernetes/gestao-escolar/base > /tmp/gestao-escolar.yaml
kubeconform -strict -summary /tmp/gestao-escolar.yaml
kube-linter lint /tmp/gestao-escolar.yaml
```

Na validação local dos ajustes, os seis recursos da base passaram no
kubeconform em modo estrito, sem recursos ignorados, e no kube-linter.
Frontend e backend também renderizaram e passaram no kubeconform isoladamente.
A base de APAE Geral continuou renderizando e passou na validação de schema.
Esses resultados verificam a estrutura dos manifests; não são evidência de
execução dos containers nem de respostas HTTP.

## Antes de ativar as réplicas

Os Deployments permanecem com `replicas: 0` até preparar o ambiente:

- Disponibilizar e referenciar Secrets para banco, MinIO, JWT e administrador,
  conforme as variáveis obrigatórias da aplicação. Não armazenar valores
  sensíveis em ConfigMaps.
- Configurar o Ingress para encaminhar `/gestao-escolar/api` ao Service
  `gestao-escolar-backend:8080`, preservando o prefixo, e o restante de
  `/gestao-escolar` ao frontend. O rewrite do Next.js possui `BACKEND_URL`
  incorporado no build; o workflow da aplicação usa por padrão outro hostname
  (`apae-gestao-escolar-backend`). Se usar esse proxy em vez do roteamento
  direto pelo Ingress, reconstruir a imagem com o endereço do Service correto.
- Revisar o contorno existente `SPRING_FLYWAY_ENABLED: "false"` e preparar o
  schema de banco antes de iniciar o backend.
- Executar as imagens escolhidas com UID/GID `65532`, filesystem somente
  leitura e os mesmos volumes dos manifests. Exercitar os fluxos da aplicação
  e verificar ausência de erros de permissão ou tentativas de escrita fora
  dos volumes. A compatibilidade completa ainda requer esse teste em runtime.
- Confirmar respostas HTTP 2xx/3xx em `/gestao-escolar` (frontend, porta 3000)
  e `/gestao-escolar/actuator/health` (backend, porta 8080) dentro dos Pods.
  Os caminhos foram conferidos no código; o teste HTTP com as dependências
  configuradas ainda precisa ser executado no ambiente de implantação.
