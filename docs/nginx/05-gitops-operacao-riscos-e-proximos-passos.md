# Parte 5 — GitOps, operação, riscos e próximos passos

> Este documento faz parte do estudo de arquitetura de NGINX e proxy reverso para os serviços APAE.

## 30. GitOps e organização no repositório

A arquitetura deve preservar o Git como fonte da verdade.

### 30.1 Recursos Kubernetes

Exemplo de organização:

```text
kubernetes/
├── gateway/
│   ├── gatewayclass.yaml
│   ├── gateway.yaml
│   └── kustomization.yaml
│
├── apae-geral/
│   └── base/
│       ├── api/
│       ├── apae/
│       └── route.yaml
│
├── apae-atendimento/
│   └── base/
│       ├── atendimento/
│       ├── atendimento-app/
│       └── route.yaml
│
├── apae-gestao-escolar/
│   └── base/
│       └── route.yaml
│
└── apae-site-comemorativo/
    └── base/
        └── route.yaml
```

A infraestrutura controla:

```text
GatewayClass
Gateway
Gateway Controller
```

Cada aplicação controla:

```text
HTTPRoute
Services
Deployments
ConfigMaps
```

---

### 30.2 Configuração do NGINX externo

A configuração deverá permanecer versionada no `APAE-INFRA`.

Estrutura possível:

```text
nginx/
├── nginx.conf
├── conf.d/
│   └── gateway.conf
└── README.md
```

O mecanismo de entrega dessa configuração para a VPS será tratado em estudo separado.

---

## 31. Evolução ao adicionar novas aplicações

Com a arquitetura recomendada, um novo produto não deverá exigir alteração no NGINX externo.

Exemplo:

```text
Novo produto
   ↓
Deployment
   ↓
Service
   ↓
HTTPRoute
   ↓
ArgoCD
```

O NGINX continua encaminhando tráfego para o mesmo Gateway.

Essa propriedade é importante para reduzir acoplamento e tornar o crescimento do ecossistema previsível.

---

## 32. ArgoCD

Os recursos Kubernetes relacionados a roteamento deverão ser reconciliados pelo ArgoCD.

Fluxo:

```text
Git
 ↓
Pull Request
 ↓
Merge
 ↓
ArgoCD
 ↓
Gateway / HTTPRoute
 ↓
estado desejado
```

O NGINX externo permanecerá fora da responsabilidade do ArgoCD.

---

## 33. Responsabilidade operacional consolidada

A arquitetura final separa responsabilidades da seguinte forma:

```text
NGINX externo
→ entrada da Internet / edge

NodePort
→ interface controlada host → cluster

NGINX Gateway Fabric
→ data plane Kubernetes

Gateway API
→ modelo declarativo de roteamento

HTTPRoute
→ regras por aplicação

Service
→ descoberta e balanceamento interno

Pod
→ execução da aplicação

ArgoCD
→ reconciliação dos recursos Kubernetes

Git
→ fonte da verdade
```

---

## 34. Riscos e pontos de atenção

### 34.1 NGINX externo como ponto único de falha

No cenário de VPS single-node, o NGINX externo é parte crítica da disponibilidade.

Esse risco é coerente com a própria existência de uma única VPS, que já representa um limite de alta disponibilidade.

A arquitetura deve permitir evolução futura sem redesenho completo.

---

### 34.2 Duplicação de proxy

A existência de NGINX externo e NGINX Gateway Fabric adiciona dois hops HTTP.

Essa escolha foi considerada aceitável porque os componentes exercem responsabilidades distintas:

```text
edge
vs
application routing
```

A configuração deverá evitar duplicar regras de aplicação entre os dois.

---

### 34.3 NodePort exposto

O NodePort deverá ser protegido por firewall.

Não deverá ser tratado como endpoint público.

---

### 34.4 Headers falsificados

A confiança em `X-Forwarded-*` deverá ser restrita ao proxy externo conhecido.

---

### 34.5 Configuração específica demais na borda

A inclusão progressiva de regras por aplicação no NGINX externo pode recriar acoplamento.

Toda exceção deverá ser tecnicamente justificada.

---

## 35. Decisão arquitetural

Após o estudo das alternativas, a arquitetura recomendada para o contexto atual da APAE é:

```text
Internet
   ↓
DNS
   ↓
NGINX externo
   ↓
NodePort privado
   ↓
NGINX Gateway Fabric
   ↓
Gateway API
   ↓
HTTPRoute
   ↓
Service ClusterIP
   ↓
Pods
```

### Justificativa

A decisão busca equilibrar:

- segurança;
- simplicidade;
- separação de responsabilidades;
- compatibilidade com GitOps;
- desacoplamento entre VPS e aplicações;
- utilização das abstrações nativas do Kubernetes;
- manutenção centralizada da borda;
- evolução futura do cluster.

Não se pretende transformar o NGINX externo em um roteador de aplicações.

O NGINX será responsável pela borda.

O Gateway API será responsável pelo roteamento das aplicações.

---

## 36. Hipóteses definidas para a primeira implementação

A primeira implementação deverá considerar:

1. NGINX externo executado na VPS, responsável pela borda HTTP/HTTPS.
2. k3s single-node com os componentes padrão Traefik e ServiceLB desabilitados.
3. NGINX atuando como edge proxy.
4. TLS terminado no NGINX externo.
5. HTTP entre NGINX externo e Gateway inicialmente.
6. NGINX Gateway Fabric como implementação de Gateway API.
7. Service do NGINX Gateway Fabric configurado explicitamente como `NodePort`, sem depender do `LoadBalancer` padrão.
8. Gateway API para roteamento interno.
9. Portas públicas `80` e `443` reservadas para o NGINX externo.
10. `HTTPRoute` para regras por produto.
11. NodePort como interface inicial entre host e Gateway.
12. NodePort protegido contra acesso externo e acessível somente pelo caminho local validado durante a implementação.
13. workloads publicados através de `ClusterIP`.
14. `X-Forwarded-*` para propagação do contexto original.
15. trusted proxies configurados explicitamente.
16. configuração do NGINX externo genérica e sem rotas por aplicação.
17. roteamento baseado em paths como baseline de menor impacto.
18. subdomínios mantidos como opção futura.
19. observabilidade da borda preparada para Loki/Grafana.
20. configuração versionada no `APAE-INFRA`.
21. ArgoCD responsável exclusivamente pelos recursos Kubernetes.

---

## 37. Decisões que permanecem para implementação

O estudo arquitetural não define valores operacionais arbitrários.

Devem ser definidos durante a implementação:

- domínio real;
- portas NodePort;
- política exata de firewall;
- certificado e mecanismo definitivo de emissão;
- valores de timeout;
- valor global de upload;
- regras exatas de rate limiting;
- headers de segurança finais;
- formato de logs;
- geração/propagação de request ID;
- namespaces do Gateway;
- política de `allowedRoutes`;
- configuração final de trusted proxies;
- versão e instalação do NGINX Gateway Fabric.

Esses valores deverão ser escolhidos a partir dos requisitos reais e não apenas por defaults genéricos.

---

## 38. Referências

Documentação oficial utilizada como apoio ao estudo:

- Kubernetes Gateway API:  
  <https://kubernetes.io/docs/concepts/services-networking/gateway/>

- Gateway API — API Overview:  
  <https://gateway-api.sigs.k8s.io/docs/concepts/api-overview/>

- Gateway API — HTTPRoute:  
  <https://gateway-api.sigs.k8s.io/reference/api-types/httproute/>

- Gateway API — GatewayClass:  
  <https://gateway-api.sigs.k8s.io/reference/api-types/gatewayclass/>

- Gateway API — Gateway:  
  <https://gateway-api.sigs.k8s.io/reference/api-types/gateway/>

- Kubernetes Services / NodePort:  
  <https://kubernetes.io/docs/concepts/services-networking/service/>

- NGINX Gateway Fabric:  
  <https://docs.nginx.com/nginx-gateway-fabric/>

- NGINX Gateway Fabric — Data Plane Configuration:  
  <https://docs.nginx.com/nginx-gateway-fabric/how-to/data-plane-configuration/>

- NGINX Gateway Fabric — API Reference:  
  <https://docs.nginx.com/nginx-gateway-fabric/reference/api/>

---

## 39. Conclusão

O estudo conclui que a separação entre uma camada de borda externa e uma camada declarativa de roteamento dentro do Kubernetes atende adequadamente às necessidades atuais da APAE.

A arquitetura:

```text
NGINX Edge
   ↓
NodePort
   ↓
NGINX Gateway Fabric
   ↓
Gateway API
   ↓
HTTPRoute
   ↓
ClusterIP
   ↓
Pods
```

permite manter:

- uma única entrada pública controlada;
- workloads internos não expostos diretamente;
- TLS e políticas globais concentrados na borda;
- roteamento de aplicações declarativo;
- integração com ArgoCD;
- Git como fonte da verdade;
- baixa dependência do NGINX externo em relação aos produtos;
- caminho de evolução para novos serviços e futuros clusters maiores.

A principal regra arquitetural derivada do estudo é:

> **NGINX controla a borda da VPS; Gateway API controla o roteamento das aplicações dentro do Kubernetes.**
