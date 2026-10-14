# Parte 3 — TLS, segurança de borda e acesso externo

> Este documento faz parte do estudo de arquitetura de NGINX e proxy reverso para os serviços APAE.

## 9. TLS

A arquitetura **selecionada** para a VPS HostGator com k3s single-node utiliza **NGINX Gateway Fabric exposto diretamente**, sem NGINX externo como camada obrigatória:

```text
Cliente
   ↓ HTTPS (porta 443)
IP público da VPS
   ↓
NGINX Gateway Fabric (data plane)
   ↓
Gateway / HTTPRoute
   ↓ HTTP interno, inicialmente
Service ClusterIP → Pods
```

A terminação TLS ocorrerá no data plane do NGINX Gateway Fabric, mediante listener HTTPS e referência ao Secret TLS autorizada no Gateway. O controller interpreta os recursos Gateway API; não constitui um hop HTTP adicional no caminho de requisições.

Essa decisão permite centralizar o certificado, o roteamento HTTP e as políticas suportadas no ambiente Kubernetes, sem duplicar o proxy no sistema operacional da VPS. O ArgoCD reconciliará os recursos declarados em Git; a emissão e renovação dos certificados poderão ser automatizadas pelo **cert-manager**, conforme a integração com Gateway API suportada pelas versões selecionadas.

O tráfego entre o Gateway e os Services poderá iniciar em HTTP na rede interna do cluster, sujeito à análise de requisitos de segurança. TLS entre componentes internos poderá ser adotado posteriormente quando houver justificativa e suporte técnico.

O NGINX externo com Certbot permanece apenas como alternativa **não selecionada**, a ser reavaliada se surgir requisito operacional concreto de proxy independente do Kubernetes. Não é parte obrigatória da implantação inicial.

---

## 10. Certificados

### 10.1 Emissão e renovação com cert-manager

Para a arquitetura selecionada, a estratégia proposta é utilizar **Let's Encrypt com cert-manager**, emitindo e renovando certificados em Secrets Kubernetes referenciados pelos listeners HTTPS do Gateway.

```text
Let's Encrypt (ACME)
       ↓
cert-manager / Issuer ou ClusterIssuer
       ↓
Secret TLS no Kubernetes
       ↓
Gateway HTTPS (NGINX Gateway Fabric)
```

A implementação deverá definir o método de validação ACME, as permissões dos Secrets, o mecanismo de integração entre cert-manager e Gateway API e os alertas de expiração. O suporte à criação automática de certificados a partir de Gateways deve ser confirmado na versão adotada; caso necessário, os recursos Certificate serão declarados explicitamente.

### 10.2 Certificado para roteamento por path

Na primeira implantação, se os produtos utilizarem **um único host**, por exemplo `apae.exemplo.org`, com caminhos `/apae-geral`, `/gestao-escolar`, `/atendimento` e `/site-comemorativo`, **um certificado para `apae.exemplo.org` é suficiente**. Certificados TLS identificam nomes DNS, e não caminhos HTTP.

Assim, **não é necessário certificado wildcard nem um certificado individual para cada produto** quando todos compartilham o mesmo hostname.

### 10.3 Certificados individuais, SAN e wildcard

Caso a arquitetura evolua para subdomínios:

- **Certificados individuais:** permitem ciclo de vida e isolamento por hostname; aumentam a quantidade de certificados e renovações a administrar.
- **Certificado SAN (multidomínio):** cobre vários hostnames explicitamente listados; simplifica a quantidade de Secrets, mas pode aumentar o impacto de renovações e alterações da lista.
- **Wildcard (`*.exemplo.org`):** facilita cobrir múltiplos subdomínios de um nível, mas amplia o impacto da exposição da chave privada e normalmente exige validação **DNS-01** no ACME. Não cobre automaticamente o domínio raiz `exemplo.org` nem subdomínios de níveis adicionais.

Para **um único domínio com roteamento por path**, a escolha inicial é um **certificado comum para o hostname público**, gerenciado pelo cert-manager. Wildcard ou certificados individuais serão reconsiderados somente se a estratégia de hostnames mudar e houver benefício operacional justificado.

### 10.4 Requisitos mínimos

- renovação automática e monitoramento de vencimento;
- armazenamento seguro dos Secrets TLS, com acesso restrito;
- validação de domínio e de desafios ACME;
- listeners HTTPS e redirecionamento HTTP → HTTPS corretamente configurados;
- testes de renovação e recuperação sem procedimentos manuais recorrentes;
- versionamento declarativo dos recursos sem armazenar chaves privadas em texto claro no Git.

---

## 11. HTTP para HTTPS

A entrada pública deverá redirecionar HTTP para HTTPS usando recursos Gateway API e os mecanismos suportados pelo NGINX Gateway Fabric.

```text
HTTP :80
   ↓
HTTPRoute com RequestRedirect (301/308)
   ↓
HTTPS :443
```

O listener HTTP poderá ter exceções estritamente necessárias ao desafio ACME selecionado, se aplicável. A implementação deverá validar que o método de emissão/renovação escolhido funciona com o redirecionamento e com as rotas do Gateway.

---

## 12. Headers de proxy

Na arquitetura selecionada, **não existe NGINX externo** para normalizar os headers. O NGINX Gateway Fabric é o primeiro proxy HTTP gerenciado pela APAE e não deve confiar automaticamente em `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host` ou `X-Real-IP` enviados diretamente por clientes externos.

O processamento desses headers deve seguir a configuração suportada pelo NGINX Gateway Fabric, com teste explícito de requisições que enviem valores falsificados. A origem e o protocolo vistos pelas aplicações devem ser derivados de metadados confiáveis do Gateway.

Caso futuramente seja implantado um proxy/CDN anterior ao Gateway, a confiança em cabeçalhos de encaminhamento deverá ser limitada aos endereços efetivamente observados dos proxies autorizados e à topologia real de rede; não basta confiar em qualquer cabeçalho recebido.

---

## 13. Trusted proxies e IP real

### 13.1 Gateway API exposto diretamente

O data plane do NGINX Gateway Fabric deverá determinar o IP do cliente a partir da conexão recebida, levando em conta eventual SNAT na exposição do Service e o modo de rede do k3s. Se o Kubernetes mascarar a origem, a implementação deverá avaliar os mecanismos suportados para preservá-la, sem declarar como confiável uma faixa de endereços ampla.

Os cabeçalhos `X-Forwarded-*` enviados por clientes externos não serão tratados como fonte confiável do IP original.

### 13.2 Alternativa futura com NGINX externo

Se uma segunda camada de proxy vier a ser aprovada, o NGINX externo deverá normalizar os headers recebidos dos clientes, e o Gateway Fabric deverá confiar somente no proxy autorizado.

```text
Cliente → NGINX externo → endpoint interno → NGINX Gateway Fabric
```

O endereço confiável deve ser **o que o Gateway efetivamente observa após eventuais SNAT/DNAT**, e não necessariamente `127.0.0.1`, mesmo que o NGINX externo use loopback para acessar um NodePort.

### 13.3 Validações obrigatórias

1. Identificar o IP de origem observado pelo data plane em testes reais.
2. Confirmar se existe SNAT no caminho de exposição e documentar seus efeitos.
3. Testar `X-Forwarded-For` falsificado e verificar os valores registrados nos logs.
4. Restringir a lista de proxies confiáveis ao menor conjunto de endereços autorizado.
5. Confirmar que o endereço confiável não pode ser utilizado por clientes não autorizados.

Não utilizar `0.0.0.0/0` como faixa de proxies confiáveis. Uma configuração inadequada pode gerar spoofing do IP do cliente ou logs contendo apenas o IP interno do node.

---

## 14. PROXY Protocol

Foram avaliados `X-Forwarded-For` e PROXY Protocol como mecanismos para transportar a origem da conexão através de proxies.

Para a arquitetura direta, **não há necessidade presumida de PROXY Protocol**: o Gateway recebe tráfego da infraestrutura de exposição do cluster e deve ser configurado conforme a preservação de IP suportada nesse caminho.

O PROXY Protocol somente será considerado se houver um componente intermediário que o envie e se o listener receptor oferecer suporte explícito e seguro a esse protocolo. Não habilitá-lo indiscriminadamente em listeners públicos.

---

## 15. Estratégia de domínio

Foram avaliadas duas abordagens para os produtos APAE.

### 15.1 Roteamento por path

Modelo de referência:

```text
apae.exemplo.org/apae-geral
apae.exemplo.org/gestao-escolar
apae.exemplo.org/atendimento
apae.exemplo.org/site-comemorativo
```

#### Benefícios

- Um hostname e, portanto, um certificado TLS principal.
- Menor quantidade de registros DNS.
- Adequação às aplicações que já utilizam `basePath`.
- Roteamento centralizado em recursos HTTPRoute versionados em Git.

#### Limitações

- As aplicações precisam lidar corretamente com prefixos e URLs absolutas.
- Cookies no mesmo host exigem cuidado com `Path` e nomes.
- Redirects, arquivos estáticos, autenticação e rewrites precisam ser validados.
- Compartilhar o mesmo hostname não torna todos os caminhos equivalentes do ponto de vista de autorização.

**Pendência bloqueante para o APAE Atendimento:** o frontend ainda não possui `basePath` para `/atendimento` e a variável `NEXT_PUBLIC_API_URL` foi identificada no estudo apontando para `http://localhost:8080` durante o build. Antes de publicar nesse path, será necessário adaptar a aplicação e validar assets, navegação, redirects e chamadas à API. Essa pendência não é solucionada apenas com uma HTTPRoute.

No APAE Geral, `/apae-geral/api/*` corresponde a Route Handlers do Next.js e deve ser encaminhado ao frontend. O backend Spring permanece acessível pelo Service interno, não por uma rota pública específica `/apae-geral/api`.

### 15.2 Subdomínios por produto

Alternativa:

```text
geral.exemplo.org
gestao.exemplo.org
atendimento.exemplo.org
comemorativo.exemplo.org
```

#### Benefícios

- Isolamento por hostname e melhor separação de cookies.
- Possibilidade de aplicações publicadas na raiz `/`.
- Políticas de entrada e certificados separados por produto.

#### Limitações

- Mais entradas DNS e decisões sobre certificados (individuais, SAN ou wildcard).
- Possibilidade de CORS entre frontends e APIs em origens distintas.
- Possível necessidade de adaptar aplicações que usam `basePath` fixo.

### 15.3 Decisão atual

A estratégia de referência para o primeiro ciclo continua sendo **roteamento por path**, sujeita à adequação dos produtos antes da publicação. O uso de Gateway API direto não obriga a escolher paths; subdomínios permanecem uma alternativa evolutiva ou uma opção caso a adaptação por path não se mostre viável.

A escolha dos hostnames e dos paths deverá considerar autenticação, cookies, CORS, redirects, URLs públicas e esforço real de adaptação. A implantação do APAE Atendimento em `/atendimento` permanece **bloqueada** até que sua compatibilidade seja demonstrada.

---

## 16. CORS

No modelo por path, páginas e APIs publicadas sob o mesmo esquema, hostname e porta compartilham a mesma origem para o navegador. Exemplo:

```text
https://apae.exemplo.org/apae-geral
https://apae.exemplo.org/apae-geral/api
```

Isso pode reduzir a necessidade de CORS no browser, mas **não dispensa** a validação de autenticação, CSRF, headers e políticas específicas de cada aplicação. No APAE Geral, `/apae-geral/api` é atendido por Route Handlers do Next.js.

Em uma arquitetura por subdomínios, como `app.exemplo.org` e `api.exemplo.org`, as origens são distintas e as permissões CORS deverão ser definidas explicitamente quando houver chamadas entre elas.

---

## 17. Cookies e autenticação

Quando múltiplas aplicações compartilham o mesmo hostname, é necessário avaliar:

- nome dos cookies;
- `Path`;
- `Domain`;
- `Secure`;
- `HttpOnly`;
- `SameSite`;
- proteção CSRF e política de autenticação entre aplicações.

Evitar colisões e compartilhamento acidental de sessão entre produtos. Quando pertinente, utilizar cookies específicos por aplicação, por exemplo:

```text
Path=/apae-geral
Path=/gestao-escolar
Path=/atendimento
```

A configuração efetiva deverá ser validada em conjunto com as aplicações e suas bibliotecas de autenticação antes da disponibilização do domínio compartilhado.

---
