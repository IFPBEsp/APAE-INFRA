## Implementação realizada

Foram criados os manifests Kubernetes base do **APAE Geral**, organizados por produto em:

```text
kubernetes/
└── apae-geral/
    └── base/
        ├── apae/
        │   ├── configmap.yaml
        │   ├── deployment.yaml
        │   ├── service.yaml
        │   └── kustomization.yaml
        ├── api/
        │   ├── configmap.yaml
        │   ├── deployment.yaml
        │   ├── service.yaml
        │   └── kustomization.yaml
        ├── management-app/
        │   ├── README.md
        │   ├── deployment.yaml
        │   ├── service.yaml
        │   └── kustomization.yaml
        └── kustomization.yaml
```

A organização `kubernetes/apae-geral/base/` foi adotada para separar os manifests por produto e permitir a inclusão futura de outros sistemas no `APAE-INFRA`, como Atendimento, Gestão Escolar e Site Comemorativo.

### API

O backend foi configurado utilizando a imagem:

```text
ghcr.io/ifpbesp/apae-geral-backend:dev
```

Porta interna:

```text
8080
```

Foi criado um `Service` do tipo `ClusterIP` e um `ConfigMap` para configurações não sensíveis.

Também foram adicionadas as probes:

```text
startupProbe
readinessProbe
livenessProbe
```

utilizando o endpoint:

```text
/apae-geral/actuator/health
```

Com isso, a verificação de saúde que anteriormente era realizada pelo `HEALTHCHECK` da imagem passa a ser responsabilidade do Kubernetes.

### Frontend APAE

O frontend utiliza:

```text
ghcr.io/ifpbesp/apae-geral-frontend:dev
```

Porta interna:

```text
3000
```

Foi criado um `Service` do tipo `ClusterIP` e um `ConfigMap` contendo as configurações não sensíveis necessárias para execução.

A comunicação server-side com o backend utiliza o Service Kubernetes:

```text
http://api:8080/apae-geral/api
```

Também foram configuradas:

```text
startupProbe
readinessProbe
livenessProbe
```

para o caminho:

```text
/apae-geral
```

### management-app

O `management-app` ainda não possui Dockerfile nem imagem publicada em registry.

Por esse motivo, ele foi documentado explicitamente como **não implantável no estado atual**.

O `Deployment` foi criado com:

```yaml
replicas: 0
```

evitando que o Kubernetes tente executar uma imagem inexistente.

Também foi adicionado um `README.md` documentando as dependências necessárias antes da ativação do serviço.

A porta `3000` utilizada no `Service` foi obtida da documentação atual da própria aplicação e deverá ser revalidada quando a imagem de produção for criada.

### Segurança

Os workloads implantáveis utilizam configurações explícitas de segurança, incluindo:

```yaml
runAsNonRoot: true
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
```

Os containers Distroless utilizam o usuário:

```text
65532:65532
```

Também foram definidos `requests` e `limits` iniciais de CPU e memória, que poderão ser ajustados posteriormente com base no comportamento real das aplicações.

### Fora do escopo

Conforme definido na issue, não foram adicionados:

- Secrets;
- PostgreSQL ou outros recursos stateful;
- overlays de `dev`, `hml` ou `prod`;
- Ingress/Gateway;
- manifests de MinIO;
- credenciais em texto puro.

Configurações sensíveis e dependentes de ambiente deverão ser tratadas posteriormente por Secrets e overlays.

## Validação

Cada manifest foi validado individualmente com:

```bash
kubeconform -strict -summary <arquivo>
```

Os diretórios Kustomize também foram renderizados e validados:

```bash
kubectl kustomize kubernetes/apae-geral/base/apae   | kubeconform -strict -summary

kubectl kustomize kubernetes/apae-geral/base/api   | kubeconform -strict -summary

kubectl kustomize kubernetes/apae-geral/base/management-app   | kubeconform -strict -summary
```

Por fim, todo o conjunto foi validado através do `kustomization.yaml` raiz:

```bash
kubectl kustomize kubernetes/apae-geral/base   | kubeconform -strict -summary
```

Os manifests passaram na validação local sem erros.
