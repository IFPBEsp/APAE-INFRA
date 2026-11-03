# Parte 1 — Contexto, requisitos e estado atual

> Este documento faz parte do estudo de arquitetura de entrada HTTP/HTTPS e roteamento para os serviços APAE.

## 1. Contexto

O ecossistema APAE possui múltiplos produtos que serão executados em Kubernetes e disponibilizados externamente a partir da infraestrutura mantida no repositório `APAE-INFRA`.

Os principais produtos considerados neste estudo são:

- APAE Geral;
- APAE Atendimento;
- APAE Gestão Escolar;
- Site Comemorativo;
- novos serviços incorporados futuramente.

O objetivo é definir uma arquitetura de entrada HTTP/HTTPS segura, simples de operar, auditável, reproduzível e compatível com GitOps, sem acoplar a configuração da VPS às rotas de cada aplicação.

A arquitetura selecionada no estudo é **Gateway API com NGINX Gateway Fabric exposto diretamente**, dentro de um **cluster k3s single-node** na VPS HostGator, conforme o escopo da [issue #90](https://github.com/IFPBEsp/APAE-INFRA/issues/90). Os recursos Kubernetes serão declarados no Git e reconciliados pelo ArgoCD, após o bootstrap necessário.

Fluxo lógico previsto:

```text
Internet / DNS
      |
      v
IP público da VPS HostGator
      | HTTP/HTTPS (80/443)
      v
NGINX Gateway Fabric (data plane no k3s)
      | TLS e processamento HTTP
      v
Gateway / HTTPRoute
      |
      v
Services ClusterIP
      |
      v
Pods das aplicações APAE
```

O diagrama é conceitual: os recursos `Gateway` e `HTTPRoute` descrevem a configuração aplicada pelo controller e não representam proxies adicionais no caminho de rede.

**Não está prevista uma segunda instância obrigatória de NGINX no host.** O NGINX externo foi avaliado como alternativa, mas não selecionado para o cenário atual por adicionar outra camada de proxy sem requisito operacional comprovado. A comparação e a justificativa estão em [Alternativas e arquitetura](02-alternativas-e-arquitetura.md).

A decisão arquitetural não equivale a uma implantação concluída. A forma de expor o data plane nas portas 80/443, a configuração dos componentes padrão do k3s, a emissão de certificados e os procedimentos de recuperação ainda exigem implementação e validação.

A questão central do estudo é:

> **Como expor os produtos APAE com segurança, mantendo o roteamento específico de cada aplicação declarado no Kubernetes e gerenciado por GitOps?**

---

## 2. Requisitos arquiteturais

A solução deverá atender aos seguintes requisitos:

- expor somente os serviços públicos autorizados;
- manter bancos de dados, storage e serviços auxiliares sem exposição pública direta;
- disponibilizar entrada HTTP/HTTPS nas portas 80/443, com terminação TLS no Gateway;
- automatizar emissão e renovação de certificados, com cert-manager como solução prevista, sujeita à validação da integração;
- redirecionar HTTP para HTTPS de acordo com os recursos suportados pela implementação;
- preservar corretamente o host, o protocolo e o IP de origem, considerando SNAT/DNAT e sem confiar em headers enviados arbitrariamente por clientes;
- declarar roteamento por host e/ou path usando `Gateway` e `HTTPRoute`;
- manter os Services das aplicações preferencialmente como `ClusterIP`;
- versionar os manifests e reconciliá-los via ArgoCD;
- evitar regras específicas de cada produto na configuração do host;
- prever logs, métricas, limites de requisições, uploads e timeouts compatíveis com as aplicações;
- evitar conflitos de portas e controllers com Traefik e outros componentes do k3s;
- validar acessibilidade pública, comportamento das rotas e mecanismos de recuperação;
- permitir evolução futura para mais serviços e, se necessário, múltiplos nós, mediante revisão das premissas de infraestrutura.

A compatibilidade das aplicações com os prefixos públicos é um requisito próprio: uma `HTTPRoute` não corrige automaticamente `basePath`, URLs de API, assets, cookies ou redirecionamentos inadequados.

---

## 3. Levantamento do estado atual

Os caminhos descritos abaixo representam o comportamento e as configurações identificados nos projetos, não uma confirmação de que todos já estejam publicados no k3s. O roteamento definitivo deverá ser testado com as aplicações reais.

### 3.1 APAE Geral

O frontend Next.js utiliza:

```text
basePath: /apae-geral
```

O backend Spring utiliza o contexto:

```text
/apae-geral
```

As rotas `/apae-geral/api/*` são **Route Handlers do Next.js**, implementados em `apps/apae/src/app/api/`. Portanto, requisições a esse prefixo devem chegar ao **frontend**, e não diretamente ao Spring.

O Spring disponibiliza endpoints sob seu próprio contexto, como `/apae-geral/patients` e `/apae-geral/auth`, sem o prefixo `/api`. Na arquitetura selecionada, o backend permanece acessível pelo **Service interno** do Kubernetes; suas chamadas devem seguir a configuração de comunicação adotada pelo frontend.

Fluxo conceitual:

```text
Internet
   |
   v
HTTPRoute: PathPrefix /apae-geral
   |
   v
Service frontend Next.js (ClusterIP)
   |-- páginas e recursos estáticos
   |-- /apae-geral/api/* (Route Handlers)
   `-- chamadas ao Service interno do Spring
          |-- /apae-geral/patients
          `-- /apae-geral/auth
```

**Não criar uma regra pública específica para encaminhar `/apae-geral/api/*` ao Spring**, pois isso direcionaria os Route Handlers ao serviço incorreto e poderia provocar erros HTTP 404.

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

O frontend também possui configuração de rewrite para comunicação com o backend. Diferentemente do APAE Geral, a rota `/gestao-escolar/api` corresponde ao caminho de acesso ao backend no modelo estudado.

Fluxo conceitual:

```text
/gestao-escolar
      |
      v
Service frontend

/gestao-escolar/api
      |
      v
Service backend
```

A configuração definitiva da `HTTPRoute` deverá respeitar os paths efetivamente atendidos pela aplicação e os rewrites existentes, sem presumir que uma regra de `PathPrefix` deva reescrever a URL.

---

### 3.3 Site Comemorativo

O Site Comemorativo utiliza Next.js e possui configuração de base path via:

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
       |
       v
Service Next.js
```

Antes da publicação, é necessário garantir que o valor usado no build corresponda ao prefixo configurado na `HTTPRoute` e validar recursos estáticos e redirecionamentos.

---

### 3.4 APAE Atendimento

O backend utiliza:

```text
/atendimento
```

como context path.

O frontend Next.js **ainda não está preparado para ser publicado sob `/atendimento`**: não possui `basePath` correspondente, e a configuração observada de `NEXT_PUBLIC_API_URL` utiliza `http://localhost:8080` durante o build.

Antes da primeira implantação por roteamento baseado em path, será necessário:

- adequar o `basePath` do frontend para `/atendimento` ou revisar formalmente a estratégia de URL pública;
- configurar `NEXT_PUBLIC_API_URL` para um endereço alcançável pelo cliente no ambiente de produção, sem depender de `localhost` do navegador;
- validar chamadas à API, recursos estáticos, navegação, autenticação, cookies e redirecionamentos;
- verificar o comportamento de HTTPRoute e dos paths realmente servidos pelo frontend e pelo backend.

**Essa adequação é um pré-requisito para publicar o APAE Atendimento em `/atendimento`**, não uma funcionalidade já implementada pelo Gateway API.

---

### 3.5 NGINX já existente

O repositório `apae-site-comemorativo` possui um experimento integrado via Docker Compose com NGINX atuando como proxy reverso.

A configuração contém referências a caminhos como:

```text
/apae-geral
/site-comemorativo
/gestao-escolar
/gestao-escolar/api
```

Esse experimento oferece referências úteis sobre os prefixes e sobre a integração dos produtos, mas corresponde a um ambiente Docker Compose e **não representa a arquitetura selecionada para produção no Kubernetes**.

Para o k3s, o roteamento das aplicações será declarado em recursos `HTTPRoute`, implementados pelo NGINX Gateway Fabric e reconciliados por GitOps. Não será necessário transportar as regras específicas do `nginx.conf` para um NGINX externo obrigatório.

A configuração existente deve ser tratada como **referência histórica e prova de conceito**, sujeita à validação do comportamento das aplicações.

---

## Referências relacionadas

- [Alternativas e arquitetura](02-alternativas-e-arquitetura.md)
- [TLS, segurança de borda e acesso](03-tls-seguranca-e-acesso.md)
- [GitOps, operação, riscos e próximos passos](05-gitops-operacao-riscos-e-proximos-passos.md)
- [Issue #60 — Arquitetura de entrada HTTP/HTTPS](https://github.com/IFPBEsp/APAE-INFRA/issues/60)
- [Issue #90 — Cluster k3s single-node](https://github.com/IFPBEsp/APAE-INFRA/issues/90)
