# Parte 3 — TLS, segurança de borda e acesso externo

> Este documento faz parte do estudo de arquitetura de NGINX e proxy reverso para os serviços APAE.

## 9. TLS

A arquitetura inicial adotará:

```text
Cliente
   ↓ HTTPS
NGINX externo
   ↓ HTTP
Gateway
```

Ou seja:

> **A terminação TLS ocorrerá inicialmente no NGINX externo.**

Benefícios:

- configuração inicial mais simples;
- apenas uma camada de certificados;
- evita duplicar trust e rotação dentro da mesma VPS;
- mantém o NGINX com responsabilidade real de edge proxy.

O tráfego:

```text
NGINX → Gateway
```

será inicialmente HTTP por ocorrer dentro da infraestrutura local.

TLS interno poderá ser estudado posteriormente caso surja requisito de segurança ou compliance que o justifique.

---

## 10. Certificados

A emissão e renovação dos certificados deverá ocorrer na camada externa.

Uma alternativa inicial é:

```text
Let's Encrypt
      ↓
Certbot
      ↓
NGINX
```

O mecanismo definitivo de instalação e gerenciamento será detalhado na futura documentação de gerenciamento da VPS.

Requisitos mínimos:

- renovação automatizada;
- proteção das chaves privadas;
- validação de configuração antes de reload;
- evitar alterações manuais como processo normal.

---

## 11. HTTP para HTTPS

A borda deverá redirecionar tráfego HTTP para HTTPS.

Fluxo:

```text
HTTP :80
   ↓
301/308
   ↓
HTTPS :443
```

A política deverá ser aplicada globalmente, exceto quando algum mecanismo técnico de validação de certificado exigir tratamento específico.

---

## 12. Headers de proxy

O NGINX externo deverá preservar o contexto da requisição original.

Baseline:

```nginx
proxy_set_header Host              $host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host  $host;
```

Esses headers permitem que as camadas internas conheçam:

- host solicitado;
- protocolo original;
- IP do cliente;
- cadeia de proxies.

---

## 13. Trusted proxies e IP real

Headers como:

```text
X-Forwarded-For
```

não deverão ser confiados quando enviados diretamente por clientes externos.

O NGINX Gateway Fabric deverá confiar no IP original apenas quando a requisição vier do proxy externo conhecido.

Fluxo:

```text
Cliente
   ↓
NGINX Edge
   ↓
X-Forwarded-For
   ↓
Gateway
```

A lista de proxies confiáveis deverá ser restritiva.

Não deverá ser adotado em produção:

```text
0.0.0.0/0
```

como origem confiável sem justificativa.

---

## 14. PROXY Protocol

Foram consideradas duas formas de preservar o IP original:

```text
X-Forwarded-For
```

e:

```text
PROXY Protocol
```

Para a arquitetura inicial, será priorizado:

```text
X-Forwarded-For
```

por se tratar de uma cadeia HTTP entre o proxy externo e o Gateway.

PROXY Protocol poderá ser estudado futuramente se surgir necessidade específica de proxy TCP ou preservação de metadados fora do contexto HTTP.

---

## 15. Estratégia de domínio

Foram consideradas duas abordagens.

### 15.1 Roteamento por path

Modelo atual:

```text
dominio/apae-geral
dominio/gestao-escolar
dominio/atendimento
dominio/site-comemorativo
```

#### Benefícios

- compatível com grande parte das aplicações atuais;
- menor impacto de migração;
- um único domínio principal;
- já validado parcialmente no ambiente Docker Compose.

#### Limitações

- maior acoplamento da aplicação ao `basePath`;
- cuidados adicionais com cookies;
- regras de path mais complexas;
- aplicações compartilham o mesmo host.

---

### 15.2 Subdomínios por produto

Alternativa:

```text
geral.exemplo.org
gestao.exemplo.org
atendimento.exemplo.org
comemorativo.exemplo.org
```

#### Benefícios

- maior isolamento entre aplicações;
- cookies naturalmente separados por host;
- aplicações podem operar na raiz `/`;
- políticas independentes por produto.

#### Limitações

- exige adaptação das aplicações atuais;
- aumenta quantidade de entradas DNS;
- exige estratégia de certificados wildcard ou certificados individuais;
- pode introduzir CORS entre serviços em hosts diferentes.

---

### 15.3 Decisão atual

O estado atual favorece roteamento por path.

Portanto, a primeira implementação deverá considerar como baseline:

```text
/apae-geral
/gestao-escolar
/atendimento
/site-comemorativo
```

Entretanto, a adoção definitiva de paths ou subdomínios deverá considerar:

- cookies;
- autenticação;
- CORS;
- redirects;
- URLs públicas;
- custo de adaptação das aplicações.

Subdomínios permanecem como alternativa válida de evolução.

---

## 16. CORS

No modelo baseado em paths, frontend e backend podem compartilhar:

```text
scheme
host
port
```

Exemplo:

```text
https://exemplo.org/apae-geral
https://exemplo.org/apae-geral/api
```

Isso pode reduzir a necessidade de CORS no browser.

Em uma arquitetura baseada em subdomínios:

```text
app.exemplo.org
api.exemplo.org
```

existem origens distintas.

A decisão de domínio deve, portanto, ser analisada juntamente com a estratégia de CORS de cada produto.

---

## 17. Cookies e autenticação

Quando múltiplas aplicações compartilham o mesmo host, é necessário avaliar:

- nome dos cookies;
- `Path`;
- `Domain`;
- `Secure`;
- `HttpOnly`;
- `SameSite`.

Deve ser evitada colisão entre cookies de aplicações distintas.

Possíveis estratégias:

```text
Path=/apae-geral
Path=/gestao-escolar
Path=/atendimento
```

ou nomes específicos por produto.

Essa análise deverá ser feita antes da implantação definitiva do domínio compartilhado.

---
