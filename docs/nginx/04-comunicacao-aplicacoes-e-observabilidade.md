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

Não deverá ser utilizado um `client_max_body_size` arbitrariamente elevado apenas para evitar problemas.

A estratégia recomendada é:

```text
NGINX Edge
→ limite global razoável da plataforma

Gateway/aplicação
→ restrições específicas do produto
```

Isso preserva o NGINX externo como componente genérico.

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
