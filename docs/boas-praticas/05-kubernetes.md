# 5. Kubernetes

[← Voltar ao índice](README.md)

Os manifests Kubernetes devem seguir um padrão consistente e declarar explicitamente os recursos necessários para execução das aplicações.

A organização definida pelo repositório deve ser respeitada:

```text
kubernetes/
├── base/
└── overlays/
    ├── dev/
    ├── hml/
    └── prod/
```

As configurações comuns devem permanecer em `base`, enquanto diferenças específicas de cada ambiente devem permanecer nos respectivos `overlays`.

---

## 5.1 Requests e Limits

Workloads devem declarar `requests` e `limits` de CPU e memória sempre que aplicável.

Exemplo:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

`requests` representam os recursos considerados necessários para o agendamento do Pod.

`limits` estabelecem limites máximos de utilização.

Os valores devem ser definidos e posteriormente ajustados com base no comportamento real das aplicações.

---

## 5.2 Health checks

Aplicações devem utilizar probes quando forem capazes de fornecer endpoints ou mecanismos adequados de verificação.

### Readiness Probe

Indica quando a aplicação está pronta para receber tráfego.

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8080
```

### Liveness Probe

Permite identificar aplicações que deixaram de funcionar corretamente.

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
```

Os valores de timeout, período e quantidade de falhas devem ser definidos de acordo com o comportamento de cada aplicação.

### Startup Probe

Aplicações que possuem inicialização lenta devem considerar o uso de uma `startupProbe`.

A `startupProbe` verifica se a aplicação concluiu corretamente seu processo de inicialização antes que as demais verificações de saúde passem a atuar.

Exemplo:

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
```

Enquanto a `startupProbe` não indicar sucesso, as verificações de `liveness` e `readiness` não interferem na inicialização da aplicação.

Isso é especialmente útil para aplicações que:

* Possuem tempo de inicialização elevado;
* Executam carregamentos ou configurações durante o startup;
* Dependem de componentes que podem levar algum tempo para ficarem disponíveis;
* Poderiam ser reiniciadas prematuramente por uma `livenessProbe`.

Os valores de `failureThreshold`, `periodSeconds` e demais parâmetros devem ser definidos considerando o tempo esperado de inicialização de cada aplicação.

O objetivo não é simplesmente aumentar os tempos das probes, mas permitir que cada tipo de verificação represente corretamente uma fase do ciclo de vida da aplicação.

As três probes possuem responsabilidades diferentes e não devem ser utilizadas de forma intercambiável:

| Probe            | Responsabilidade                                                 |
| ---------------- | ---------------------------------------------------------------- |
| `startupProbe`   | Determinar se a aplicação terminou de inicializar                |
| `readinessProbe` | Determinar se a aplicação está pronta para receber tráfego       |
| `livenessProbe`  | Determinar se a aplicação continua saudável durante sua execução |

De forma resumida:

```text
Startup Probe
→ A aplicação terminou de iniciar?

Readiness Probe
→ A aplicação está pronta para receber tráfego?

Liveness Probe
→ A aplicação continua funcionando corretamente?
```

A configuração incorreta das probes pode causar comportamentos indesejados, como reinicializações desnecessárias ou envio de tráfego para aplicações que ainda não estão prontas.

Por esse motivo, os valores utilizados não devem ser copiados indiscriminadamente entre aplicações. Cada workload deve ser configurado considerando seu comportamento real.

---

## 5.3 Namespaces

Os recursos devem ser separados logicamente utilizando namespaces de acordo com a estratégia definida pelo projeto.

Exemplos:

```text
apae
atendimento
gestao-escolar
site-comemorativo
```

A separação por ambiente também deve respeitar a organização adotada para `dev`, `hml` e `prod`.

Recursos de aplicações diferentes não devem ser colocados arbitrariamente no namespace `default`.

---

## 5.4 Namespace default

Workloads das aplicações não devem ser implantados no namespace `default`, salvo quando existir uma justificativa técnica específica.

O uso de namespaces próprios facilita:

* Organização;
* Controle de acesso;
* Monitoramento;
* Identificação dos recursos;
* Aplicação de políticas específicas.

---

## 5.5 Security Context

Quando compatível com a aplicação, os Pods e containers devem possuir configurações de segurança explícitas.

Exemplo:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
```

Quando possível, capacidades Linux desnecessárias também devem ser removidas:

```yaml
securityContext:
  capabilities:
    drop:
      - ALL
```

Essas configurações reduzem o impacto de uma eventual vulnerabilidade dentro do container.

---

## 5.6 ConfigMaps e Secrets

Utilizar `ConfigMap` para configurações não sensíveis.

Exemplos:

* URLs públicas;
* Flags de configuração;
* Nomes de ambiente;
* Parâmetros não confidenciais.

Utilizar mecanismos apropriados de Secret para informações sensíveis.

Exemplos:

* Tokens;
* Senhas;
* Chaves de API;
* Credenciais de bancos.

Segredos não devem ser armazenados em texto puro no Git.

---
