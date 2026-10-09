# Parte 2 — Alternativas e arquitetura recomendada

> Este documento faz parte do estudo de arquitetura de NGINX e proxy reverso para os serviços APAE.

## 4. Alternativas estudadas

### 4.1 NGINX externo roteando diretamente para cada aplicação

Fluxo:

```text
Internet
   ↓
NGINX
   ├── APAE Geral
   ├── Atendimento
   ├── Gestão Escolar
   └── Site Comemorativo
```

Exemplo:

```nginx
location /apae-geral {
    proxy_pass ...;
}

location /gestao-escolar {
    proxy_pass ...;
}
```

#### Benefícios

- simples de compreender;
- semelhante ao Docker Compose já existente;
- baixo número inicial de componentes.

#### Limitações

O NGINX externo passa a conhecer detalhes de todas as aplicações.

Cada novo produto exige alteração em:

```text
nginx.conf
```

Isso cria uma segunda fonte de verdade para roteamento, paralela aos manifests Kubernetes.

Fluxo indesejado:

```text
nginx.conf
+
Kubernetes manifests
```

Também aumenta o acoplamento entre a VPS e a estrutura interna do cluster.

#### Conclusão

Não foi adotada como arquitetura recomendada.

---

### 4.2 NGINX externo + Ingress Controller

Fluxo:

```text
Internet
   ↓
NGINX externo
   ↓
Ingress Controller
   ↓
Ingress
   ↓
Service
```

Essa abordagem permitiria manter o NGINX externo como borda e utilizar recursos Kubernetes para roteamento interno.

Entretanto, o estudo evoluiu para Gateway API por oferecer um modelo de responsabilidades mais explícito e uma API mais expressiva para o roteamento moderno de serviços.

O antigo projeto comunitário `ingress-nginx` também não deve ser utilizado como base para uma nova arquitetura, pois foi aposentado em 2026.

---

### 4.3 NGINX externo + Gateway API

Fluxo:

```text
Internet
   ↓
NGINX externo
   ↓
Gateway Controller
   ↓
Gateway
   ↓
HTTPRoute
   ↓
Service
   ↓
Pod
```

Essa alternativa preserva o NGINX como camada de borda, enquanto o roteamento específico das aplicações permanece dentro do Kubernetes.

#### Benefícios

- responsabilidades bem separadas;
- aplicações não precisam ser conhecidas pelo NGINX externo;
- integração natural com GitOps;
- `HTTPRoute` pode ser versionado junto aos manifests de cada aplicação;
- `Service` continua responsável pelo service discovery e balanceamento interno;
- novos produtos podem ser adicionados sem alterar o NGINX externo;
- reduz acoplamento entre host e aplicações.

#### Conclusão

Foi selecionada como base da arquitetura recomendada.

---

## 5. Arquitetura recomendada

A arquitetura selecionada para continuidade da implementação é:

```text
                         INTERNET
                            │
                            │ HTTPS
                            ▼
                           DNS
                            │
                            ▼
                      IP público VPS
                            │
                            ▼
                    ┌─────────────────┐
                    │   NGINX EDGE    │
                    │                 │
                    │ TLS             │
                    │ HTTP → HTTPS    │
                    │ headers         │
                    │ rate limiting   │
                    │ body limits     │
                    │ access logs     │
                    └────────┬────────┘
                             │
                             │ HTTP interno
                             │
                             ▼
                     NodePort privado
                             │
                             ▼
                   NGINX Gateway Fabric
                             │
                             ▼
                         Gateway API
                             │
                  ┌──────────┴──────────┐
                  │                     │
               HTTPRoute            HTTPRoute
                  │                     │
                  ▼                     ▼
              Services              Services
              ClusterIP             ClusterIP
                  │                     │
                  ▼                     ▼
                 Pods                  Pods
```

A arquitetura pode ser resumida por:

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
ClusterIP Service
    ↓
Pod
```

---

## 6. Princípio central de separação de responsabilidades

A principal decisão do estudo é:

> **O NGINX externo não deve ser a fonte de verdade do roteamento das aplicações.**

O NGINX externo deve conhecer apenas o entrypoint Kubernetes.

Fluxo esperado:

```text
NGINX externo
      ↓
um único upstream
      ↓
Gateway
```

O roteamento:

```text
/apae-geral
/atendimento
/gestao-escolar
/site-comemorativo
```

deve ser responsabilidade dos recursos Gateway API.

Isso evita:

```text
nginx.conf
+
HTTPRoute
```

como fontes concorrentes de configuração.

---

## 7. Responsabilidades por camada

### 7.1 NGINX externo

Responsável pela borda da infraestrutura:

```text
NGINX Edge
├── receber HTTP/HTTPS;
├── terminar TLS;
├── redirecionar HTTP → HTTPS;
├── aplicar headers básicos de proxy;
├── preservar contexto da requisição;
├── aplicar limites globais de request;
├── aplicar proteção genérica de borda;
├── controlar timeouts globais;
├── produzir access/error logs;
└── encaminhar tráfego ao Gateway Kubernetes.
```

Não deverá conhecer:

- Pods;
- nomes internos dos backends;
- topologia das aplicações;
- regras específicas de cada produto, salvo exceções tecnicamente justificadas.

---

### 7.2 NGINX Gateway Fabric

Dentro do cluster, o NGINX Gateway Fabric será a primeira implementação considerada para Gateway API.

Seu papel é:

```text
Gateway API
      ↓
NGINX Gateway Fabric
      ↓
data plane NGINX
      ↓
Services
```

Apesar de existirem dois componentes baseados em NGINX, eles possuem responsabilidades diferentes:

```text
NGINX externo
→ edge proxy

NGINX Gateway Fabric
→ data plane Kubernetes
```

Essa separação evita que a camada externa precise conhecer a topologia interna.

---

### 7.3 Gateway API

Gateway API será responsável por representar declarativamente a infraestrutura e o roteamento HTTP dentro do cluster.

Principais recursos:

```text
GatewayClass
Gateway
HTTPRoute
```

#### GatewayClass

Define qual controller implementa os Gateways.

#### Gateway

Representa o ponto de entrada Kubernetes e seus listeners.

#### HTTPRoute

Representa as regras específicas de roteamento HTTP.

Exemplo conceitual:

```text
/apae-geral/api
      ↓
apae-geral-backend

/apae-geral
      ↓
apae-geral-frontend
```

---

### 7.4 Services

Os Services das aplicações deverão permanecer, sempre que possível, como:

```yaml
type: ClusterIP
```

Isso significa que os workloads não precisam ser diretamente acessíveis pela Internet.

O Gateway será o ponto responsável por encaminhar o tráfego externo para os Services autorizados.

---

## 8. Exposição NGINX → Kubernetes

Foram analisadas as seguintes alternativas:

- NodePort;
- hostPort;
- hostNetwork;
- LoadBalancer local.

### 8.1 NodePort

Foi selecionado como hipótese inicial.

Fluxo:

```text
NGINX externo
      ↓
NodePort
      ↓
Gateway data plane
```

O Kubernetes utiliza por padrão o intervalo:

```text
30000-32767
```

para NodePorts.

#### Motivos

- mantém o networking padrão dos Pods;
- reduz acoplamento com a rede do host;
- é simples em uma VPS single-node;
- permite evolução futura para múltiplos nodes;
- é um mecanismo padrão Kubernetes;
- é compatível com NGINX Gateway Fabric.

#### Requisito de segurança

O NodePort não deverá ficar acessível pela interface de rede pública da VPS.

Não é suficiente depender exclusivamente do UFW para bloquear as portas NodePort. O kube-proxy implementa esses serviços por meio de regras de rede, incluindo NAT e encaminhamento de pacotes, que podem seguir um caminho diferente da cadeia `INPUT` filtrada pelas regras usuais do firewall local.

Como o NGINX Edge e o cluster Kubernetes estarão na mesma VPS, a abordagem recomendada é restringir os endereços pelos quais os NodePorts são disponibilizados ao loopback do host.

A configuração deverá utilizar o recurso `nodePortAddresses` do kube-proxy, com `127.0.0.0/8` ou o valor equivalente `localhost`, desde que haja suporte no modo de proxy e na versão do Kubernetes utilizados pelo k3s.

O NGINX Edge deverá encaminhar as requisições para o endereço local:

```text
NGINX Edge
    ↓
127.0.0.1:<NodePort>
    ↓
NGINX Gateway Fabric
```

A compatibilidade com loopback deverá ser validada durante a implementação, considerando a versão do Kubernetes fornecida pelo k3s e o modo de proxy utilizado.

No modo `iptables`, o acesso ao NodePort pelo loopback depende do suporte a localhost NodePorts e da configuração do parâmetro de kernel `route_localnet`, cuja habilitação pode ter efeitos colaterais de segurança que precisam ser avaliados.

No modo `nftables`, o acesso por loopback depende da feature gate `KubeProxyNFTablesLocalhostNodePorts`, que deve estar habilitada, além da inclusão explícita dos endereços de loopback em `nodePortAddresses`.

A configuração não deverá ser considerada válida apenas porque o serviço está acessível via `127.0.0.1`. Caso a combinação de versão, modo de proxy e configuração do k3s não permita restringir o NodePort ao loopback com segurança, deverá ser adotada e validada outra forma de comunicação local antes da exposição dos serviços.

O firewall local e o firewall do provedor continuarão sendo utilizados como camadas adicionais de defesa. Nenhum deles deverá ser considerado, isoladamente, garantia de que o NodePort está inacessível externamente.

#### Validações obrigatórias

A implementação deverá comprovar que:

- o NGINX consegue alcançar o NodePort por 127.0.0.1;
- o NodePort não pode ser acessado pelo IP público da VPS;
- as portas públicas necessárias continuam restritas a HTTP (80) e HTTPS (443);
- a configuração permanece válida após reiniciar o k3s e a VPS.

---

### 8.2 hostPort

Permite que o Pod abra diretamente uma porta do node.

Benefícios:

- simples;
- elimina uma camada de Service NodePort.

Limitações:

- maior acoplamento com o node;
- restrições de scheduling;
- conflitos de porta;
- pior evolução para múltiplos replicas/nodes.

Não foi selecionado como hipótese principal.

---

### 8.3 hostNetwork

Permite que o Pod utilize diretamente a rede do node.

Benefícios:

- caminho extremamente curto;
- simples em single-node.

Limitações:

- maior acoplamento ao host;
- menor isolamento;
- comportamento de NetworkPolicy pode depender do CNI;
- dificulta portabilidade.

Não foi selecionado como hipótese principal.

---

### 8.4 LoadBalancer local (K3s ServiceLB)

O Kubernetes permite Services do tipo `LoadBalancer`, mas precisa de uma implementação de balanceador para disponibilizá-los.

O k3s inclui o ServiceLB, que fornece essa funcionalidade sem depender de um balanceador externo. Para cada Service do tipo `LoadBalancer`, o ServiceLB cria Pods que utilizam `hostPort` nas portas do Service.

#### Benefícios

- implementação integrada ao k3s;
- não exige um provedor de LoadBalancer externo;
- permite disponibilizar Services do tipo `LoadBalancer` em um cluster single-node;
- integração com os Services nativos do Kubernetes.

#### Limitações no cenário da APAE

O k3s instala o Traefik por padrão, e o ServiceLB utiliza as portas `80` e `443` para disponibilizar esse componente.

Essas portas também precisam ficar disponíveis para o NGINX Edge, que será o ponto de entrada HTTP/HTTPS da VPS.

Manter o Traefik e o ServiceLB com a configuração padrão pode causar conflito de portas e impedir que o NGINX Edge seja iniciado corretamente. Além disso, o NGINX Gateway Fabric cria um Service do tipo `LoadBalancer` por padrão quando um Gateway é criado.

Portanto, adotar o ServiceLB sem ajustar os componentes e Services do cluster não é compatível com a arquitetura proposta.

#### Decisão

Não utilizaremos o ServiceLB do k3s como mecanismo de exposição do NGINX Gateway Fabric.

Na instalação do k3s, os componentes padrão Traefik e ServiceLB deverão ser desabilitados:

```text
--disable=traefik
--disable=servicelb
```

---
