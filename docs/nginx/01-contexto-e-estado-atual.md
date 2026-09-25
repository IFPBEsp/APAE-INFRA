# Parte 1 — Contexto, requisitos e estado atual

> Este documento faz parte do estudo de arquitetura de NGINX e proxy reverso para os serviços APAE.

## 1. Contexto

O ecossistema APAE possui múltiplos produtos que serão executados em Kubernetes e disponibilizados externamente a partir da infraestrutura mantida no repositório `APAE-INFRA`.

Os principais produtos considerados neste estudo são:

- APAE Geral;
- APAE Atendimento;
- APAE Gestão Escolar;
- Site Comemorativo;
- novos serviços que venham a ser incorporados à plataforma.

O objetivo deste documento é definir uma arquitetura de entrada HTTP/HTTPS que seja:

- segura;
- simples de operar;
- compatível com Kubernetes;
- compatível com o modelo GitOps adotado no `APAE-INFRA`;
- desacoplada das aplicações;
- preparada para crescimento futuro;
- auditável e reproduzível.

A questão central analisada foi:

> **Como o tráfego externo deve entrar na infraestrutura da APAE, qual deve ser o papel do NGINX e onde deve ficar o roteamento específico de cada aplicação?**

---

## 2. Requisitos arquiteturais

A solução deve permitir:

- exposição controlada dos serviços públicos;
- manutenção de bancos, storage e serviços auxiliares fora da Internet;
- terminação TLS;
- redirecionamento HTTP para HTTPS;
- preservação do IP e contexto da requisição original;
- roteamento por host e/ou path;
- integração com Kubernetes;
- integração com ArgoCD;
- configuração versionada em Git;
- escalabilidade para novos serviços;
- observabilidade da camada de entrada;
- políticas básicas de segurança de borda;
- suporte a uploads e timeouts compatíveis com os produtos;
- evolução futura para múltiplos nodes sem redesenhar toda a arquitetura.

---

## 3. Levantamento do estado atual

### 3.1 APAE Geral

O frontend utiliza Next.js com:

```text
basePath: /apae-geral
```

O backend Spring também trabalha abaixo do prefixo:

```text
/apae-geral
```

A API pública atualmente é consumida pelo frontend através de:

```text
/apae-geral/api
```

O modelo atual favorece roteamento baseado em path.

Fluxo conceitual:

```text
/apae-geral
      ↓
frontend

/apae-geral/api
      ↓
backend
```

---

### 3.2 APAE Gestão Escolar

O frontend utiliza:

```text
basePath: /gestao-escolar
```

O backend Spring utiliza:

```text
server.servlet.context-path=/gestao-escolar
```

O frontend também possui configuração de rewrite para comunicação com o backend.

Fluxo conceitual:

```text
/gestao-escolar
      ↓
frontend

/gestao-escolar/api
      ↓
backend
```

---

### 3.3 Site Comemorativo

O Site Comemorativo utiliza Next.js e já possui suporte a:

```text
NEXT_PUBLIC_BASE_PATH
```

com fallback:

```text
/site-comemorativo
```

Fluxo conceitual:

```text
/site-comemorativo
      ↓
Next.js
```

---

### 3.4 APAE Atendimento

O backend utiliza:

```text
/atendimento
```

como context path.

O frontend atualmente não possui um `basePath` equivalente, mas utiliza `NEXT_PUBLIC_API_URL` em build-time para definir a URL da API.

Esse produto precisará de atenção especial na definição final de URL externa, principalmente se for mantido o modelo baseado em paths.

---

### 3.5 NGINX já existente

O `apae-site-comemorativo` possui atualmente um experimento integrado via Docker Compose com NGINX atuando como reverse proxy.

A configuração existente possui regras para:

```text
/apae-geral
/site-comemorativo
/gestao-escolar
/gestao-escolar/api
```

Esse experimento demonstra que o roteamento baseado em paths é viável para os produtos atuais.

Entretanto, essa configuração foi criada para um ambiente baseado em Docker Compose e não deverá ser transportada diretamente como arquitetura de produção Kubernetes.

Ela deve ser tratada como **baseline histórica e prova de conceito**.

---
