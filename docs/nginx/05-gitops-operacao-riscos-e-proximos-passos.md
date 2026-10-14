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

### 30.2 Configuração de entrada pública

Na arquitetura adotada, os recursos de entrada (GatewayClass, Gateway, HTTPRoute e configurações do NGINX Gateway Fabric) são versionados no `APAE-INFRA` e reconciliados pelo ArgoCD. Certificados poderão ser gerenciados pelo cert-manager, conforme a integração validada.

O NGINX externo não integra a implantação padrão. Caso uma necessidade operacional futura justifique adotá-lo, sua configuração deverá ser versionada e entregue à VPS por automação apropriada, sem duplicar as regras HTTPRoute.

---

## 31. Evolução ao adicionar novas aplicações

Com a arquitetura adotada, um novo produto deve ser integrado por manifests Kubernetes e HTTPRoute, sem configurar rotas específicas na VPS.

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

O NGINX Gateway Fabric permanece como data plane de entrada e utiliza os recursos Gateway API reconciliados pelo ArgoCD.

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

Na arquitetura adotada, não existe NGINX externo. O ArgoCD gerencia os recursos Kubernetes de entrada; componentes e configurações do host pertencem à automação própria da VPS.

---

## 33. Responsabilidade operacional consolidada

A arquitetura adotada separa responsabilidades da seguinte forma:

```text
NGINX Gateway Fabric
→ data plane público HTTP/HTTPS e implementação do Gateway API

GatewayClass / Gateway
→ controller associado, listeners e ponto de entrada

HTTPRoute
→ regras por aplicação

Service ClusterIP
→ descoberta e balanceamento interno

Pod
→ execução das aplicações

ArgoCD
→ reconciliação dos recursos Kubernetes

Git
→ fonte da verdade
```

Ansible permanece responsável pelos serviços do host e pela instalação do k3s e pelo bootstrap do ArgoCD, conforme o estudo específico. Não se pressupõe NGINX externo ou NodePort privado para a comunicação entre proxies.

---

## 34. Riscos e pontos de atenção

### 34.1 Entrada pública e ponto único de falha

O k3s single-node e sua VPS representam um ponto único de falha para o tráfego das aplicações. Na arquitetura adotada, a disponibilidade da entrada HTTP/HTTPS também depende do data plane do NGINX Gateway Fabric.

A implementação deverá prever monitoramento, verificação de saúde, reinício controlado e recuperação dos componentes de entrada. A adoção de outro proxy na mesma VPS não elimina a dependência do host único.

---

### 34.2 Duplicação de proxy

A alternativa de NGINX externo mais NGINX Gateway Fabric adiciona duas camadas HTTP, podendo duplicar TLS, logs, timeouts e políticas de segurança.

Após o comparativo da [seção 4.5 — Comparação das alternativas](02-alternativas-e-arquitetura.md#45-comparacao-das-alternativas), o estudo adota **Gateway API direto** para a VPS atual. A camada externa só deverá ser reconsiderada se surgir um requisito operacional comprovado que compense a complexidade adicional.

---

### 34.3 NodePort exposto

A exposição indevida de NodePorts representa um risco de acesso não autorizado aos serviços internos do cluster.

As medidas de mitigação deverão seguir os requisitos definidos na [seção 8.1 — NodePort](02-alternativas-e-arquitetura.md#81-nodeport), incluindo restrição dos endereços de exposição, verificação das regras efetivas de rede e testes externos de conectividade.

O UFW não deverá ser considerado, isoladamente, uma proteção suficiente para restringir o acesso aos NodePorts.

Na arquitetura adotada, não é necessário NodePort privado entre proxies. Se a alternativa com NGINX externo for implementada futuramente, deverá ser comprovado que somente essa origem autorizada alcança o endpoint interno do Gateway.

---

### 34.4 Headers falsificados

Na entrada direta, cabeçalhos `X-Forwarded-*` fornecidos pelos clientes não devem ser aceitos como prova do IP ou protocolo original. Se houver proxy confiável intermediário, sua origem efetivamente observada (inclusive após SNAT) deverá ser validada e restrita, conforme o estudo de TLS e segurança.

---

### 34.5 Configuração específica demais na borda

O roteamento específico dos produtos pertence aos recursos HTTPRoute. Não deverão ser introduzidas regras paralelas na configuração da VPS. Qualquer exceção deverá ser tecnicamente justificada e revisada.

---

## 35. Decisão arquitetural

Após a análise das alternativas, a arquitetura recomendada para o contexto atual da APAE utiliza **Gateway API com NGINX Gateway Fabric** para realizar o roteamento declarativo das aplicações Kubernetes.

Considerando a VPS HostGator com um cluster k3s single-node, a exposição direta do Gateway API é a alternativa preferencial, desde que não exista um requisito operacional concreto que justifique uma camada adicional de NGINX fora do cluster.

### 35.1 Arquitetura preferencial — Gateway API direto

```text
Internet
   |
   v
DNS
   |
   v
IP público da VPS
   |
   v
NGINX Gateway Fabric
   | Terminação TLS e entrada HTTP/HTTPS
   v
Gateway / HTTPRoute
   |
   v
Service ClusterIP
   |
   v
Pods das aplicações APAE
```

Nesta arquitetura:

- O NGINX Gateway Fabric atua como camada de entrada HTTP/HTTPS.
- O Gateway API define declarativamente os listeners e as rotas.
- Os recursos HTTPRoute direcionam as requisições aos Services Kubernetes correspondentes.
- Os Services das aplicações permanecem, preferencialmente, como ClusterIP, sem exposição pública direta.
- O ArgoCD reconcilia os recursos de roteamento e as aplicações.
- O cert-manager poderá automatizar a emissão e renovação dos certificados TLS, conforme a integração definida na implementação.

A exposição pública do Gateway Fabric deverá ser configurada para utilizar as portas 80/443, evitando conflitos com o Traefik integrado ao k3s e com outros serviços da VPS.

### 35.2 Arquitetura alternativa — NGINX externo + Gateway API

Caso seja comprovada a necessidade de manter uma camada de proxy independente do Kubernetes, poderá ser adotada a seguinte arquitetura:

```text
Internet
   |
   v
DNS
   |
   v
NGINX externo na VPS
   | Terminação TLS e entrada HTTP/HTTPS
   v
Endpoint interno restrito
   |
   v
NGINX Gateway Fabric
   |
   v
Gateway / HTTPRoute
   |
   v
Service ClusterIP
   |
   v
Pods das aplicações APAE
```

Nessa alternativa, o NGINX externo permanece instalado na VPS, fora do cluster Kubernetes, enquanto o Gateway Fabric realiza o roteamento declarativo das aplicações dentro do cluster.

A adoção de duas camadas somente será justificada mediante requisitos operacionais concretos, como:

- necessidade de disponibilizar serviços HTTP do host independentemente do Kubernetes;
- necessidade de manter uma página de manutenção acessível durante indisponibilidades do cluster;
- requisitos específicos de borda não atendidos adequadamente pelo Gateway Fabric;
- necessidade comprovada de separar os ciclos de vida do proxy público e dos componentes Kubernetes.

A separação conceitual entre borda pública e roteamento de aplicações não é, isoladamente, justificativa suficiente para manter dois proxies.

Se essa alternativa for adotada, o endpoint interno do Gateway deverá permanecer restrito. Não será suficiente depender exclusivamente do UFW para proteger NodePorts, conforme os requisitos da [seção 8.1 — NodePort](02-alternativas-e-arquitetura.md#81-nodeport).

### 35.3 Critérios para a implementação

Antes de implementar a arquitetura escolhida, deverão ser confirmados:

1. A forma de exposição pública do Gateway Fabric no k3s single-node.
2. A estratégia de terminação TLS, certificados e renovação.
3. A configuração do Traefik integrado ao k3s, evitando conflitos entre controllers e portas.
4. As políticas de segurança e acesso aos endpoints internos.
5. A instalação e a ordem de reconciliação dos CRDs do Gateway API, do NGINX Gateway Fabric e dos recursos de rota.
6. Os procedimentos de observabilidade, manutenção e recuperação.
7. A existência ou não de requisitos que justifiquem um NGINX externo adicional.

### 35.4 Conclusão

A decisão arquitetural estabelece o **Gateway API com NGINX Gateway Fabric como solução de roteamento das aplicações APAE**.

Para a infraestrutura atual, a exposição direta do Gateway é preferencial devido à menor complexidade operacional.

A arquitetura com NGINX externo foi avaliada e **não foi selecionada** para a primeira implantação. A decisão de exposição direta deverá ser confirmada na revisão do estudo da [issue #60](https://github.com/IFPBEsp/APAE-INFRA/issues/60); ainda será necessário validar a forma técnica de publicar o data plane nas portas 80/443.

Independentemente da topologia escolhida, o roteamento específico dos produtos continuará declarado nos recursos HTTPRoute e gerenciado pelo fluxo GitOps.

### Justificativa

A opção pelo Gateway API exposto diretamente evita duplicar proxies na mesma VPS e mantém:

- uma única camada de entrada HTTP/HTTPS;
- TLS e políticas de borda no Gateway Fabric, conforme recursos suportados;
- roteamento declarativo por HTTPRoute e reconciliação GitOps;
- Services ClusterIP sem exposição pública individual;
- menos componentes para manter, observar e depurar.

A alternativa com NGINX externo permanece registrada no comparativo arquitetural, mas não é parte do desenho adotado.

---

## 36. Hipóteses definidas para a primeira implementação

A primeira implantação seguirá o desenho de **k3s single-node + NGINX Gateway Fabric + Gateway API exposto diretamente**, sujeito à validação dos detalhes operacionais:

1. Gateway Fabric como único proxy HTTP público do produto, com listeners nas portas 80/443.
2. Roteamento por recursos Gateway e HTTPRoute versionados no Git e reconciliados pelo ArgoCD.
3. Workloads expostos internamente por Services ClusterIP.
4. TLS terminado no Gateway, com emissão e renovação de certificados automatizáveis por cert-manager.
5. Definição e verificação da estratégia de exposição do data plane, sem conflito com Traefik e ServiceLB do k3s.
6. Validação das políticas de segurança, dos headers, dos logs e da preservação do IP real.
7. Rotas baseadas em paths somente para aplicações compatíveis; adequações pendentes deverão bloquear a publicação por esse modelo.
8. NGINX externo e NodePort entre proxies **não** fazem parte desta primeira implantação.

---

## 37. Decisões que permanecem para implementação

O estudo arquitetural não define valores operacionais arbitrários.

Devem ser definidos durante a implementação:

- domínio e subdomínios reais;
- estratégia de exposição pública do Gateway nas portas 80/443, incluindo compatibilidade com o k3s;
- adequação do APAE Atendimento ao prefixo `/atendimento`: configurar o `basePath` do frontend e revisar `NEXT_PUBLIC_API_URL` (apontada para `http://localhost:8080` no build), validando chamadas à API, assets, navegação e redirecionamentos **antes da primeira publicação por path**;
- caso seja adotado NGINX externo, porta NodePort fixa, declarada
  em `spec.ports[].nodePort` e sincronizada com a configuração
  do NGINX, evitando erros HTTP 502 após recriações do Service;
- política de firewall e restrição de acesso aos endpoints internos;
- estratégia de TLS, emissão e renovação de certificados;
- valores de timeout, limites de upload e rate limiting;
- headers de segurança e formato dos logs;
- geração e propagação de request ID;
- namespaces do Gateway e política de `allowedRoutes`;
- configuração de trusted proxies, considerando possíveis SNAT/DNAT;
- versão e instalação do NGINX Gateway Fabric;
- configuração do Traefik e ServiceLB no k3s.

Essas definições deverão considerar a topologia aprovada, os requisitos reais das aplicações e os mecanismos de segurança, sem depender de valores padrão não validados.

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

O estudo seleciona **Gateway API com NGINX Gateway Fabric exposto diretamente** para a entrada HTTP/HTTPS dos produtos APAE no cluster k3s single-node.

```text
Internet / DNS
      ↓
IP público da VPS (80/443)
      ↓
NGINX Gateway Fabric (TLS e data plane)
      ↓
Gateway / HTTPRoute
      ↓
Service ClusterIP
      ↓
Pods
```

Essa arquitetura mantém uma única camada de proxy HTTP, roteamento declarativo reconciliado pelo ArgoCD, Services internos e menor complexidade operacional em comparação com a alternativa de NGINX externo adicional.

A implantação exige confirmar a exposição pública do Gateway, a estratégia de certificados, a convivência com Traefik/ServiceLB e as políticas de segurança. **O APAE Atendimento não deverá ser publicado sob `/atendimento` antes de corrigir seu `basePath`, sua URL de API e validar seu funcionamento por path.**

O NGINX externo permanece documentado apenas como alternativa não selecionada, sujeita a reavaliação se surgirem requisitos operacionais concretos.
