# Parte 4 — Comunicação, aplicações e observabilidade

> Este documento faz parte do estudo de arquitetura de NGINX e proxy reverso para os serviços APAE.

A arquitetura selecionada utiliza **Gateway API com NGINX Gateway Fabric exposto diretamente** no cluster k3s single-node. A camada de entrada HTTP/HTTPS e suas políticas serão implementadas no data plane do Gateway Fabric, conforme os recursos suportados pela versão adotada. O NGINX externo à estrutura Kubernetes foi avaliado, mas não integra a arquitetura selecionada.

## 18. Comunicação interna

Nem todo tráfego precisa atravessar o Gateway. Requisições entre serviços do cluster devem preferir DNS e Services Kubernetes, sem exposição pública desnecessária.

Exemplos:

```text
Frontend server-side
      ↓
Backend (Service ClusterIP)
```

```text
Backend
   ↓
PostgreSQL (Service interno)
```

```text
Backend
   ↓
MinIO (Service interno)
```

Chamadas executadas no navegador precisam utilizar endereços acessíveis ao cliente; nomes DNS internos do Kubernetes não são, por padrão, acessíveis fora do cluster. No APAE Geral, `/apae-geral/api/*` pertence aos Route Handlers do Next.js: o Gateway encaminha esse prefixo ao frontend, que pode consumir o backend pelo Service interno.

---

## 19. Serviços que não devem ser publicados

Como regra geral, os seguintes serviços não devem receber `HTTPRoute` pública sem requisito explícito e avaliação de segurança:

- PostgreSQL, Redis e bancos auxiliares;
- interfaces administrativas do MinIO;
- métricas internas e endpoints administrativos;
- serviços auxiliares sem necessidade de acesso externo.

A existência de um `Service` Kubernetes não implica acesso público.

> **Apenas serviços explicitamente autorizados por recursos de roteamento público devem ser acessíveis pela entrada HTTP/HTTPS.**

Controles de rede e autenticação continuam necessários: a ausência de `HTTPRoute` não substitui NetworkPolicies ou restrições de acesso aos serviços internos.

---

## 20. Uploads

O estudo identifica funcionalidades com uploads de até aproximadamente **50 MB**, incluindo o APAE Atendimento. O backend do APAE Geral também declara `max-request-size: 50MB`.

Na arquitetura selecionada, o caminho lógico é:

```text
Cliente
   ↓ HTTPS
NGINX Gateway Fabric
   ↓
Service ClusterIP
   ↓
Aplicação
```

### Estratégia de limites para uploads

O Gateway Fabric deverá aceitar tamanhos compatíveis com os limites permitidos pelas aplicações. Um limite padrão de NGINX pode ser inferior a 50 MB; portanto, não devemos presumir que a configuração inicial atenderá a uploads maiores.

A implementação deverá:

- configurar explicitamente o limite de corpo de requisição no Gateway Fabric por mecanismo suportado pela **versão e pelo schema instalados** (por exemplo, política apropriada, quando disponível);
- manter o limite do Gateway igual ou superior ao limite efetivo exigido por cada aplicação, considerando overhead de `multipart/form-data`;
- preservar limites específicos de produto no backend, sem elevar globalmente o limite além do necessário;
- testar respostas `413 Content Too Large` e demais falhas de upload.

Não será adotada uma configuração `client_max_body_size` no NGINX do host, pois a arquitetura selecionada não possui proxy HTTP externo. A diretiva NGINX equivalente, se necessária, deverá ser aplicada por configuração **suportada pelo NGINX Gateway Fabric**, sem edição manual do data plane gerado.

### Validação

Executar testes com:

- requisições pequenas, inferiores a 1 MB;
- arquivos próximos do limite aceito pela aplicação;
- arquivos acima do limite permitido;
- uploads multipart, observando o overhead e as unidades de tamanho;
- comportamento da aplicação e códigos HTTP, especialmente `413`.

---

## 21. Timeouts

Os timeouts deverão ser coerentes entre cliente, Gateway Fabric, Service e aplicação:

```text
Cliente → NGINX Gateway Fabric → Service → Aplicação
```

Avaliar os timeouts de conexão, leitura e envio conforme as capacidades do Gateway Fabric e as políticas disponíveis na versão selecionada. Não assumir que as diretivas tradicionais `proxy_connect_timeout`, `proxy_send_timeout` e `proxy_read_timeout` serão configuradas diretamente nos recursos Gateway API.

Exceções devem ser justificadas por requisitos de uploads, downloads, relatórios, importações ou operações longas. Testar também timeouts de clientes e aplicações.

---

## 22. WebSocket

Não será configurado tratamento especial de WebSocket globalmente sem necessidade identificada.

Quando um produto utilizar WebSocket, validar o suporte do Gateway Fabric a upgrade de conexão, HTTP/1.1 ou outros protocolos aplicáveis, além de timeouts e comportamento da aplicação.

A necessidade e os testes devem ser registrados por produto.

---

## 23. Rate limiting

O Gateway Fabric poderá aplicar proteção genérica contra abuso **se a versão e os recursos adotados suportarem a política necessária**.

Regras de negócio para endpoints como `/login`, `/password-reset` e `/auth` continuam sob responsabilidade da aplicação ou de políticas específicas revisadas, não de uma configuração global genérica.

Separação proposta:

```text
NGINX Gateway Fabric → proteção de entrada suportada
Aplicação             → controles de autenticação e regras de negócio
```

Antes de habilitar limites, validar a preservação do IP de origem e o tratamento de proxies confiáveis, para evitar bloquear múltiplos usuários como se fossem um único cliente após SNAT.

---

## 24. Headers de segurança

A entrada HTTP/HTTPS poderá aplicar uma baseline compatível com os frontends, conforme recursos suportados pelo Gateway Fabric ou pelas aplicações.

Avaliar, entre outros:

- `X-Content-Type-Options`;
- `Strict-Transport-Security`;
- `Content-Security-Policy`;
- `Permissions-Policy`;
- `frame-ancestors` via CSP.

Políticas que dependem do comportamento de cada aplicação devem ser definidas e testadas com os respectivos produtos. Não aplicar uma lista de headers indiscriminadamente nem duplicar cabeçalhos contraditórios entre Gateway e aplicação.

---

## 25. HSTS

O HSTS poderá ser habilitado somente após o HTTPS estar funcional e estabilizado em produção.

As opções `includeSubDomains` e `preload` não serão ativadas automaticamente: exigem avaliação dos demais subdomínios, dos efeitos de persistência no navegador e da capacidade de manter HTTPS continuamente.

---

## 26. Informações do servidor

Deverá ser avaliada a redução da exposição de informações de versão do servidor pelo data plane do Gateway Fabric, **utilizando apenas mecanismos de configuração suportados**.

A diretiva tradicional `server_tokens off;` é uma possibilidade do NGINX, mas sua aplicação no Gateway Fabric depende da versão e das opções expostas pelo controller. Não editar manualmente arquivos gerados pelo controller.

Essa medida complementa, mas não substitui atualizações, correções de vulnerabilidades, hardening e privilégio mínimo.

---

## 27. Observabilidade

O **NGINX Gateway Fabric** será o primeiro ponto de observação HTTP/HTTPS dentro da arquitetura selecionada.

Devem ser considerados:

- access logs e error logs;
- volume de requisições, códigos 4xx/5xx e latência;
- bytes enviados e recebidos;
- host, path e Service de destino quando disponíveis;
- IP real do cliente, após validação do caminho de rede;
- indicadores de erro e disponibilidade do Gateway e do data plane.

Fluxo conceitual de logs:

```text
NGINX Gateway Fabric
        ↓
Pipeline de logs do cluster
        ↓
       Loki
        ↓
      Grafana
```

Métricas poderão ser coletadas por Prometheus conforme a integração instalada; logs e métricas são fluxos distintos e devem ser configurados separadamente.

Evitar registrar tokens, cabeçalhos `Authorization`, cookies sensíveis, credenciais e parâmetros confidenciais. Configurar retenção, controle de acesso e minimização dos dados coletados.

---

## 28. Request ID

Deverá ser avaliada a criação ou propagação de um identificador por requisição, preservado entre Gateway e aplicações:

```text
Cliente
   ↓
NGINX Gateway Fabric
   ↓ X-Request-ID (validado ou gerado)
Service
   ↓
Aplicação
```

O identificador deve ser consistente e não pode ser confiado indiscriminadamente quando fornecido pelo cliente. Sua propagação facilitará correlacionar logs do Gateway e das aplicações.

---

## 29. Saúde do Gateway

A saúde da entrada pública deverá ser monitorada por verificações do controller, do data plane e dos recursos Gateway API.

Avaliar:

- readiness e disponibilidade do data plane;
- condições de `Gateway` e `HTTPRoute`, como aceitação e resolução de referências;
- integridade dos Services e endpoints de destino;
- métricas do NGINX Gateway Fabric;
- teste HTTP/HTTPS externo representativo de uma rota pública.

Como o ambiente inicial é k3s single-node, mecanismos complexos de failover não serão presumidos. O plano de recuperação deverá considerar indisponibilidade da própria VPS e do cluster.

---
