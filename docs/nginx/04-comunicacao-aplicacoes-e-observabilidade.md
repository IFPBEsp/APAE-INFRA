# Parte 4 — Comunicação, aplicações e observabilidade

> Este documento faz parte do estudo de arquitetura de NGINX e proxy reverso para os serviços APAE.

## 18. Comunicação interna

Nem todo tráfego precisa atravessar o Gateway.

Exemplo:

```text
frontend server-side
      ↓
backend ClusterIP
```

ou:

```text
backend
   ↓
PostgreSQL
```

ou:

```text
backend
   ↓
MinIO
```

A comunicação interna deverá utilizar DNS e Services Kubernetes sempre que aplicável.

---

## 19. Serviços que não devem ser publicados

Como regra geral, não devem receber `HTTPRoute` público sem necessidade explícita:

- PostgreSQL;
- Redis;
- bancos auxiliares;
- MinIO administrativo;
- métricas internas;
- endpoints administrativos;
- serviços auxiliares.

A existência de um `Service` Kubernetes não significa que o serviço é público.

> **Somente serviços explicitamente associados a rotas públicas devem ser acessíveis através da borda.**

---

## 20. Uploads

O APAE Atendimento possui configuração de backend para uploads de até aproximadamente:

```text
50 MB
```

A cadeia completa precisa aceitar valores compatíveis:

```text
Cliente
   ↓
NGINX Edge
   ↓
Gateway
   ↓
Aplicação
```

### Estratégia de limites para uploads

A cadeia completa de proxies deverá aceitar limites compatíveis com as necessidades das aplicações.

O NGINX Edge e o NGINX Gateway Fabric possuem, por padrão, limite de aproximadamente 1 MB para o corpo das requisições.

Esse valor não atende aos requisitos atuais da APAE, pois existem funcionalidades que permitem uploads de até 50 MB.

O backend do APAE Geral também define:

```yaml
max-request-size: 50MB
```

Portanto, as duas camadas de proxy deverão ter seus limites configurados explicitamente para evitar respostas HTTP 413 Request Entity Too Large.

#### NGINX Edge

O limite global deverá ser de, no mínimo, 50 MB:

```nginx
client_max_body_size 50m;
```

Esse valor deverá ser aplicado no contexto adequado (http, server ou location), conforme a configuração final do proxy.

#### NGINX Gateway Fabric

O Gateway também deverá permitir requisições de pelo menos 50 MB.

O ajuste deverá utilizar a configuração suportada pelo NGINX Gateway Fabric, como uma `ClientSettingsPolicy`, observando a versão e o schema instalados.

#### Aplicações

As aplicações poderão estabelecer limites específicos inferiores ao limite global, conforme seus requisitos.

A estratégia adotada será:

```text
Cliente
↓
NGINX Edge → limite global: mínimo 50 MB
↓
NGINX Gateway Fabric → limite: mínimo 50 MB
↓
Aplicação → limite específico do produto
```

Os limites das camadas intermediárias não deverão ser inferiores ao tamanho máximo permitido pela aplicação.

#### Validação

Durante a implementação, deverão ser realizados testes de upload para verificar:

- requisições pequenas, inferiores a 1 MB;
- uploads próximos de 50 MB;
- uploads que ultrapassem o limite permitido;
- comportamento das respostas HTTP, especialmente `413`;
- consistência entre NGINX Edge, Gateway e backend.

Os valores finais deverão considerar também possíveis diferenças de interpretação das unidades de tamanho e o overhead de requisições multipart.

---

## 21. Timeouts

Os timeouts deverão ser coerentes entre:

```text
cliente
 ↓
NGINX
 ↓
Gateway
 ↓
backend
```

Devem ser avaliados:

```text
proxy_connect_timeout
proxy_send_timeout
proxy_read_timeout
```

A política deverá utilizar valores seguros por padrão e permitir exceções apenas quando justificadas por requisitos reais, como:

- upload;
- download;
- geração de relatórios;
- importações;
- operações assíncronas ou longas.

---

## 22. WebSocket

Não deverá ser habilitada configuração especial de WebSocket globalmente sem necessidade.

Caso alguma aplicação necessite WebSocket, deverão ser avaliados:

```text
Upgrade
Connection
HTTP version
timeouts
```

em todas as camadas do caminho.

A necessidade deverá ser confirmada por aplicação.

---

## 23. Rate limiting

O NGINX externo poderá aplicar proteção genérica contra abuso.

Entretanto, regras específicas de negócio como:

```text
/login
/password-reset
/auth
```

não devem ser movidas automaticamente para a borda.

Separação recomendada:

```text
NGINX Edge
→ proteção genérica da plataforma

Gateway/aplicação
→ regras específicas do produto
```

Isso evita transformar o NGINX externo em um conjunto de exceções específicas por aplicação.

---

## 24. Headers de segurança

A borda poderá aplicar uma baseline mínima de headers.

Exemplos a avaliar:

```text
X-Content-Type-Options
Strict-Transport-Security
```

Políticas fortemente dependentes da aplicação, como:

```text
Content-Security-Policy
Permissions-Policy
frame-ancestors
```

devem ser definidas com cuidado para evitar quebra dos frontends.

Não deverá ser utilizada uma lista genérica de hardening sem validação funcional.

---

## 25. HSTS

HSTS poderá ser habilitado após a estabilização do HTTPS em produção.

Configurações como:

```text
includeSubDomains
preload
```

não deverão ser ativadas automaticamente.

Essas opções exigem que todos os subdomínios relevantes estejam preparados para operar permanentemente em HTTPS.

---

## 26. Informações do servidor

Será avaliado:

```nginx
server_tokens off;
```

para reduzir exposição desnecessária de informações.

Essa medida não substitui:

- atualização de pacotes;
- patches;
- firewall;
- hardening;
- princípio de menor privilégio.

---

## 27. Observabilidade

O NGINX externo representa o primeiro ponto de observação de todo o tráfego HTTP/HTTPS.

Deverão ser coletados:

- access logs;
- error logs;
- status HTTP;
- latência;
- quantidade de bytes;
- host;
- path;
- IP de origem;
- upstream status;
- erros 4xx;
- erros 5xx.

Arquitetura futura:

```text
NGINX
   ↓
Loki
   ↓
Grafana
```

A observabilidade deverá evitar registrar:

- tokens;
- Authorization headers;
- cookies sensíveis;
- parâmetros confidenciais.

---

## 28. Request ID

É recomendada a propagação de um identificador de requisição.

Fluxo:

```text
Cliente
   ↓
NGINX
   ↓
X-Request-ID
   ↓
Gateway
   ↓
Backend
```

Isso permite correlacionar:

```text
edge logs
gateway logs
application logs
```

durante troubleshooting.

---

## 29. Saúde do Gateway

A saúde do Gateway deverá ser observável.

Devem ser considerados:

- readiness do data plane;
- status dos Gateways;
- status dos HTTPRoutes;
- health do Service;
- métricas do NGINX Gateway Fabric.

A borda não deverá implementar lógica de failover complexa sem necessidade real, principalmente no cenário inicial single-node.

---
