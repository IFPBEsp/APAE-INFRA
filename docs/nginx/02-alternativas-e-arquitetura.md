# Parte 2 — Alternativas e arquitetura recomendada

> Este documento faz parte do estudo de arquitetura de NGINX e proxy reverso para os serviços APAE.

## 4. Alternativas estudadas

O estudo considera a utilização de uma VPS HostGator com um cluster Kubernetes k3s single-node, conforme a issue #90.

As alternativas foram avaliadas considerando:

- simplicidade operacional e manutenção;
- integração com Kubernetes e GitOps;
- roteamento declarativo das aplicações;
- terminação TLS e gerenciamento de certificados;
- segurança e exposição das portas públicas;
- observabilidade, logs e políticas de tráfego;
- disponibilidade e recuperação de falhas;
- possibilidade de evolução futura da infraestrutura.

A adoção de Gateway API não exige necessariamente uma camada de NGINX externa ao cluster. Por isso, o estudo compara tanto a exposição direta do Gateway quanto a utilização de duas camadas de proxy reverso.

### 4.1 NGINX externo roteando diretamente para cada aplicação

Fluxo:

```text
Internet
   |
   v
NGINX na VPS
   |
   |-- APAE Geral
   |-- Atendimento
   |-- Gestão Escolar
   `-- Site Comemorativo
```

Exemplo conceitual:

```nginx
location /apae-geral {
    proxy_pass http://apae-geral;
}

location /gestao-escolar {
    proxy_pass http://gestao-escolar;
}
```

Os endereços utilizados no exemplo representam upstreams conceituais, não configurações prontas para implantação.

#### Benefícios

- Arquitetura simples de compreender inicialmente.
- Semelhante ao experimento existente com Docker Compose.
- Não exige um Gateway Controller dentro do Kubernetes.
- Permite centralizar TLS e políticas de borda em um único proxy.

#### Limitações

O NGINX externo passa a conhecer os caminhos e os destinos específicos de cada aplicação.

A inclusão de novos produtos ou a alteração das rotas exige modificações no arquivo `nginx.conf`.

Isso cria uma configuração de roteamento paralela aos manifests Kubernetes e aumenta o acoplamento entre a VPS e os serviços internos do cluster.

Também dificulta a delegação do gerenciamento das rotas aos projetos consumidores por meio de recursos declarativos.

#### Conclusão

Não é a alternativa preferencial para a arquitetura GitOps proposta, pois centraliza no host configurações específicas das aplicações.

---

### 4.2 NGINX externo + Ingress Controller

Fluxo:

```text
Internet
   |
   v
NGINX externo na VPS
   |
   v
Ingress Controller
   |
   v
Ingress
   |
   v
Service
   |
   v
Pod
```

Nesta alternativa, o NGINX externo funciona como borda pública, enquanto o Ingress Controller interpreta os recursos Ingress e encaminha as requisições para os Services Kubernetes.

#### Benefícios

- Permite declarar rotas dentro do Kubernetes.
- Reduz a necessidade de manter regras específicas das aplicações no NGINX externo.
- Oferece integração com ferramentas de GitOps.
- Separa conceitualmente a entrada pública e o roteamento interno.

#### Limitações

- Introduz duas camadas de proxy HTTP.
- Exige coordenação entre certificados, headers, logs e timeouts.
- Aumenta os componentes que precisam ser configurados e monitorados.
- A separação entre borda e roteamento não comprova, isoladamente, a necessidade de dois proxies.
- O recurso Ingress oferece um modelo menos expressivo de políticas e delegação quando comparado ao Gateway API.

A escolha de um Ingress Controller também exigiria considerar a manutenção e o ciclo de suporte da implementação selecionada.

#### Conclusão

Não foi selecionada como arquitetura preferencial.

O estudo prioriza Gateway API por permitir um modelo mais expressivo de roteamento e responsabilidades.

---

### 4.3 NGINX externo + Gateway API

Fluxo:

```text
Internet
   |
   v
NGINX externo na VPS
   |
   v
Endpoint interno do Gateway
   |
   v
NGINX Gateway Fabric
   |
   v
Gateway / HTTPRoute
   |
   v
Service
   |
   v
Pod
```

Nesta alternativa, o NGINX externo recebe o tráfego público HTTP/HTTPS, enquanto o NGINX Gateway Fabric implementa o roteamento declarativo dentro do cluster Kubernetes.

O NGINX externo conhece apenas o endpoint do Gateway, sem manter regras específicas dos produtos APAE.

#### Benefícios

- Mantém o roteamento das aplicações declarado em recursos HTTPRoute.
- Permite versionar as rotas e reconciliá-las pelo ArgoCD.
- Reduz o acoplamento entre as aplicações e a configuração do host.
- Pode oferecer uma borda operacional independente do Kubernetes.
- Pode atender serviços HTTP executados diretamente na VPS, caso esse requisito exista.
- Permite manter um endpoint de manutenção ou recuperação no host, mesmo durante indisponibilidades do cluster, se implementado independentemente dele.

#### Limitações

- Adiciona duas camadas de processamento HTTP.
- Exige manter e atualizar dois componentes de proxy.
- Pode duplicar funcionalidades como TLS, redirects, headers, rate limiting, limites de requisição e logs.
- Aumenta a complexidade de diagnóstico de falhas.
- Exige configurar corretamente a transmissão do IP real do cliente e os headers `X-Forwarded-*`.
- Requer proteger o endpoint interno do Gateway.
- Não elimina o ponto único de falha representado pela VPS.

A separação conceitual entre NGINX Edge e Gateway API não é, por si só, justificativa suficiente para essa duplicação.

#### Condições para adoção

A arquitetura com duas camadas deverá ser adotada somente quando houver pelo menos um requisito operacional concreto que justifique o NGINX externo, como:

- Necessidade de publicar serviços HTTP do host independentes do cluster Kubernetes.
- Necessidade de manter uma página de manutenção ou recuperação acessível durante intervenções no k3s.
- Requisitos específicos de borda que não possam ser atendidos adequadamente pelo Gateway Fabric.
- Necessidade operacional comprovada de separar o ciclo de vida do proxy público e dos componentes Kubernetes.

Esses requisitos deverão ser registrados, avaliados e validados antes da implementação.

#### Conclusão

É uma alternativa tecnicamente válida, mas sua adoção permanece condicionada à comprovação de benefícios que justifiquem a complexidade adicional.

---

### 4.4 Gateway API exposto diretamente

Fluxo:

```text
Internet
   |
   v
IP público da VPS
   |
   v
NGINX Gateway Fabric
   |
   v
Gateway / HTTPRoute
   |
   v
Service
   |
   v
Pod
```

Nesta alternativa, o NGINX Gateway Fabric recebe diretamente o tráfego público HTTP/HTTPS, sem um NGINX adicional no host.

O Gateway Fabric executa o roteamento das requisições conforme os recursos Gateway e HTTPRoute declarados no Kubernetes.

A exposição pública do data plane deverá ser configurada para permitir acesso às portas 80/443, sem conflito com os serviços existentes na VPS ou com os componentes do k3s.

#### Benefícios

- Uma única camada de proxy HTTP.
- Menor complexidade de instalação, manutenção e monitoramento.
- Elimina a duplicação desnecessária de políticas de borda.
- Permite gerenciamento declarativo das rotas por Gateway API.
- Facilita a integração com ArgoCD.
- Centraliza o roteamento das aplicações no Kubernetes.
- Reduz a quantidade de componentes envolvidos no diagnóstico de falhas.
- Permite evolução da infraestrutura sem transferir regras de aplicação para configurações manuais no host.

#### TLS e certificados

A terminação TLS poderá ocorrer diretamente no Gateway.

A emissão e renovação dos certificados poderão ser automatizadas por cert-manager, conforme a integração e os recursos suportados na implementação escolhida.

A estratégia deverá contemplar:

- emissão e renovação automática dos certificados;
- armazenamento seguro das chaves privadas;
- redirecionamento HTTP para HTTPS;
- configuração de listeners;
- observabilidade e alertas de expiração;
- validação dos headers de proxy e da origem das requisições.

#### Limitações

- A entrada HTTP/HTTPS depende diretamente da disponibilidade do cluster e do data plane do Gateway Fabric.
- É necessário definir a forma segura de exposição das portas públicas 80/443 no k3s single-node.
- É necessário validar a interação com o Traefik integrado ao k3s e evitar conflitos entre controllers.
- A recuperação do Gateway e dos certificados precisa estar documentada.
- Serviços executados diretamente no host exigirão uma estratégia própria de publicação, caso existam.

#### Conclusão

É a alternativa preferencial para a VPS single-node quando não houver requisitos concretos que exijam um proxy independente do Kubernetes.

A escolha reduz a complexidade operacional e preserva o roteamento declarativo das aplicações.

---

### 4.5 Comparação das alternativas

| Critério | NGINX direto | NGINX + Ingress | NGINX + Gateway API | Gateway API direto |
| --- | --- | --- | --- | --- |
| Camadas de proxy HTTP | 1 | 2 | 2 | 1 |
| Roteamento via GitOps no Kubernetes | Limitado | Sim | Sim | Sim |
| Recursos HTTPRoute | Não | Não | Sim | Sim |
| Terminação TLS | NGINX externo | NGINX externo ou controller | NGINX externo | Gateway Fabric |
| Gerenciamento de certificados | Certbot ou equivalente | Depende da topologia | Certbot ou equivalente | cert-manager ou equivalente |
| Complexidade operacional | Inicialmente baixa | Alta | Alta | Menor |
| Configuração de rotas no host | Sim | Não é necessária | Não é necessária | Não |
| Dependência do cluster para tráfego das aplicações | Sim | Sim | Sim | Sim |
| Possibilidade de serviços HTTP independentes do cluster | Sim | Sim | Sim | Exige solução adicional |
| Integração com ArgoCD | Parcial | Sim | Sim | Sim |

A comparação evidencia que o uso de duas camadas de proxy não elimina a dependência do cluster para disponibilizar as aplicações hospedadas nele.

O principal benefício potencial do NGINX externo está na possibilidade de manter serviços HTTP independentes do Kubernetes e separar a operação da borda pública.

Essas necessidades devem ser comprovadas antes de aceitar o custo adicional da arquitetura dupla.

### 4.6 Recomendação do estudo

Para o cenário atual da APAE, com uma única VPS HostGator e um cluster k3s single-node, recomenda-se:

1. Utilizar Gateway API com NGINX Gateway Fabric para o roteamento declarativo das aplicações Kubernetes.
2. Considerar a exposição direta do Gateway API como alternativa preferencial pela menor complexidade operacional.
3. Manter NGINX externo + Gateway API como alternativa condicionada à existência de requisitos operacionais concretos.
4. Validar a estratégia de TLS, certificados, exposição das portas 80/443 e compatibilidade com os componentes do k3s.
5. Registrar a decisão final com o time antes da implementação.

A decisão definitiva sobre manter ou não o NGINX externo deverá ser tomada antes da criação dos manifests e playbooks responsáveis pela exposição pública dos serviços.

O roteamento das aplicações continuará sendo responsabilidade dos recursos Gateway API, independentemente da alternativa de entrada pública escolhida.

---

## 5. Arquitetura recomendada

Após a comparação das alternativas, a arquitetura proposta para a
infraestrutura atual da APAE utiliza **Gateway API com NGINX Gateway Fabric**
para realizar a entrada HTTP/HTTPS e o roteamento declarativo das aplicações
hospedadas no Kubernetes.

Considerando a VPS HostGator com um cluster k3s single-node, recomenda-se
preferencialmente a exposição direta do Gateway API, evitando manter duas
camadas de proxy HTTP sem um requisito operacional concreto.

A utilização de NGINX externo ao cluster permanece como alternativa
válida, condicionada à comprovação de necessidades específicas.

### 5.1 Arquitetura preferencial — Gateway API direto

```text
                         INTERNET
                            |
                            | HTTPS
                            v
                           DNS
                            |
                            v
                      IP público VPS
                            |
                            | Portas 80/443
                            v
                 +-----------------------+
                 | NGINX Gateway Fabric  |
                 |                       |
                 | TLS / HTTPS           |
                 | HTTP -> HTTPS         |
                 | Políticas HTTP        |
                 | Logs e métricas       |
                 |                       |
                 | Data plane do Gateway |
                 +-----------+-----------+
                             |
                             v
                       Gateway API
                  Gateway / HTTPRoute
                             |
                  +----------+----------+
                  |                     |
                  v                     v
               HTTPRoute             HTTPRoute
               APAE Geral            Gestão Escolar
                  |                     |
                  v                     v
               Service               Service
               ClusterIP             ClusterIP
                  |                     |
                  v                     v
                 Pods                  Pods

              Outras aplicações seguem
              o mesmo modelo declarativo.
```

O fluxo representa uma arquitetura lógica. O Gateway API define os
recursos declarativos, enquanto o NGINX Gateway Fabric implementa
o processamento e o encaminhamento do tráfego.

A exposição pública do data plane deverá ser definida durante a
implementação, garantindo acesso às portas 80/443 sem conflitos
com o Traefik integrado ao k3s ou outros serviços da VPS.

#### Responsabilidades

- **NGINX Gateway Fabric:** implementar o Gateway API e processar
  o tráfego HTTP/HTTPS recebido.
- **Gateway:** declarar listeners, portas e configurações de entrada.
- **HTTPRoute:** declarar as regras de roteamento de cada aplicação.
- **Services ClusterIP:** disponibilizar os workloads internamente.
- **ArgoCD:** reconciliar os recursos Kubernetes declarados no Git.
- **cert-manager:** poderá automatizar a emissão e renovação dos
  certificados TLS, conforme a integração adotada.

As funcionalidades de redirecionamento HTTPS, rate limiting,
limites de requisição e demais políticas dependerão dos recursos
efetivamente suportados pela versão e configuração selecionadas
do NGINX Gateway Fabric.

#### Fluxo resumido

```text
Internet
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
Pod
```

Essa alternativa reduz o número de componentes operacionais,
centraliza o roteamento no Kubernetes e preserva o modelo GitOps.

### 5.2 Arquitetura alternativa — NGINX externo + Gateway API

Caso seja identificado um requisito concreto para manter uma
camada de proxy independente do Kubernetes, poderá ser adotada
a seguinte arquitetura:

```text
                         INTERNET
                            |
                            | HTTPS
                            v
                           DNS
                            |
                            v
                      IP público VPS
                            |
                            v
                 +-----------------------+
                 | NGINX externo na VPS  |
                 |                       |
                 | TLS / HTTPS           |
                 | HTTP -> HTTPS         |
                 | Políticas de borda    |
                 | Logs                  |
                 +-----------+-----------+
                             |
                             | HTTP interno
                             v
                   Endpoint interno
                   restrito do cluster
                             |
                             v
                 +-----------------------+
                 | NGINX Gateway Fabric  |
                 |                       |
                 | Gateway API           |
                 | Roteamento HTTPRoute  |
                 +-----------+-----------+
                             |
                  +----------+----------+
                  |                     |
                  v                     v
              Service               Service
              ClusterIP             ClusterIP
                  |                     |
                  v                     v
                 Pods                  Pods
```

Nessa alternativa, o NGINX externo fica instalado diretamente
na VPS, fora do cluster Kubernetes.

O NGINX externo conhece apenas o endpoint interno do Gateway,
enquanto as regras específicas dos produtos permanecem
declaradas nos recursos HTTPRoute.

A adoção dessa topologia somente será recomendada quando
existir um requisito operacional comprovado, como:

- publicação de serviços HTTP independentes do cluster;
- necessidade de manter uma página de manutenção durante
  indisponibilidades do Kubernetes;
- políticas específicas de borda não atendidas adequadamente
  pelo Gateway Fabric;
- necessidade operacional de ciclos de vida separados
  entre o proxy público e o Gateway Kubernetes.

O endpoint interno deverá ser protegido por mecanismos
adequados de rede, sem depender exclusivamente do UFW
para restringir NodePorts.

Os detalhes de exposição e segurança deverão seguir a
[seção 8.1 — NodePort](#81-nodeport), caso NodePort seja
o mecanismo selecionado para comunicação entre o NGINX
externo e o cluster.

#### Fluxo resumido

```text
Internet
    |
    v
NGINX externo na VPS
    |
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
Pod
```

### 5.3 Critérios para a decisão definitiva

Antes da implementação, deverão ser validados:

1. A forma de exposição pública do NGINX Gateway Fabric no
   cluster k3s single-node.
2. A compatibilidade entre as portas públicas 80/443 e os
   componentes de rede instalados pelo k3s.
3. A necessidade de manter ou desabilitar o Traefik integrado.
4. A estratégia de emissão, armazenamento e renovação dos
   certificados TLS.
5. Os recursos de segurança, observabilidade e políticas HTTP
   suportados pelo Gateway Fabric.
6. A necessidade real de serviços HTTP independentes do cluster.
7. Os mecanismos de recuperação da entrada pública em caso
   de falha do Kubernetes.
8. A existência de requisitos que justifiquem o custo
   operacional de uma segunda camada de proxy.

### 5.4 Conclusão

A arquitetura estabelece **Gateway API com NGINX Gateway Fabric**
como solução proposta para o roteamento declarativo dos produtos APAE.

Para a VPS atual, a exposição direta do Gateway API é a alternativa
preferencial pela menor complexidade operacional.

O NGINX externo permanece como alternativa condicionada à
comprovação de requisitos que justifiquem uma camada
independente do Kubernetes.

A escolha definitiva da topologia de entrada deverá ser
validada com o time antes da implementação, conforme a
[issue #60](https://github.com/IFPBEsp/APAE-INFRA/issues/60).

Independentemente da alternativa escolhida, as regras específicas
das aplicações deverão permanecer nos recursos HTTPRoute
versionados no Git e reconciliados pelo ArgoCD.

---

## 6. Princípio central de separação de responsabilidades

A principal decisão deste estudo é:

> **O roteamento específico das aplicações deve permanecer nos recursos HTTPRoute, independentemente de existir ou não um NGINX externo.**

Na topologia preferencial, o NGINX Gateway Fabric recebe o tráfego público e aplica as rotas declaradas no Kubernetes. Se um requisito concreto justificar uma borda independente, o NGINX externo conhecerá apenas o endpoint do Gateway, sem duplicar regras por produto.

Os prefixos `/apae-geral`, `/atendimento`, `/gestao-escolar` e `/site-comemorativo` serão administrados por recursos Gateway API, observadas as particularidades de cada aplicação. Em especial, `/apae-geral/api/*` pertence aos Route Handlers do frontend Next.js e não deve ser encaminhado diretamente ao Spring.

Assim, evitamos manter `nginx.conf` e `HTTPRoute` como fontes concorrentes de roteamento das aplicações.

---

## 7. Responsabilidades por camada

### 7.1 Entrada pública HTTP/HTTPS

**Na arquitetura preferencial**, o data plane do NGINX Gateway Fabric é a entrada HTTP/HTTPS e poderá concentrar terminação TLS, redirecionamentos, logs e políticas suportadas pela implementação escolhida. O cert-manager é candidato à automação dos certificados; sua compatibilidade e configuração devem ser validadas.

**Na alternativa condicionada**, o NGINX externo é instalado na VPS, fora do k3s, sob responsabilidade do Ansible, e passa a receber o tráfego público. Nesse cenário, poderá assumir TLS, redirecionamentos e políticas globais, encaminhando requisições a um único endpoint interno do Gateway Fabric. Não deverá conter regras individuais por produto.

A adoção desse segundo proxy depende de um requisito operacional comprovado, como oferecer um serviço HTTP independente do cluster ou uma página de manutenção durante intervenções. A mera distinção entre borda e roteamento não justifica duplicar proxies.

As duas opções precisam garantir proteção da origem, preservação adequada dos headers `X-Forwarded-*`, observabilidade e ausência de conflitos nas portas 80/443.

---

### 7.2 NGINX Gateway Fabric

O NGINX Gateway Fabric é a implementação candidata a reconciliar e materializar o comportamento dos recursos Gateway API no cluster.

```text
GatewayClass / Gateway / HTTPRoute (declarativos)
                    |
                    v
          NGINX Gateway Fabric
                    |
                    v
              Data plane NGINX
                    |
                    v
             Services ClusterIP
```

Com Gateway API direto, o data plane é exposto publicamente de maneira controlada. Na topologia com NGINX externo, o data plane é acessado por um endpoint interno restrito. **Esses modos são alternativas**, e a exposição final deve ser confirmada antes da instalação.

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

Exemplo conceitual para o APAE Geral:

```text
HTTPRoute
    |
    |-- PathPrefix: /apae-geral
    |          |
    |          v
    |     Service frontend Next.js
    |          |
    |          |-- paginas e recursos estaticos
    |          |-- /apae-geral/api/* (Route Handlers)
    |          |
    |          `-- requisicoes internas
    |                  |
    |                  v
    |             Service backend Spring
    |             (ClusterIP, nao exposto no Gateway)
```

O Gateway API não deverá criar uma regra específica para encaminhar `/apae-geral/api/*` ao backend Spring, pois esse prefixo pertence aos Route Handlers do Next.js.

O roteamento público do APAE Geral deverá encaminhar o prefixo `/apae-geral` ao frontend. O backend será acessado internamente pelo Service Kubernetes correspondente.

No APAE Gestão Escolar, a situação é diferente: `/gestao-escolar/api` corresponde ao backend e pode exigir uma regra específica de roteamento, conforme a configuração da aplicação.

---

### 7.4 Services

Os Services das aplicações deverão permanecer, sempre que possível, como:

```yaml
type: ClusterIP
```

Isso significa que os workloads não precisam ser diretamente acessíveis pela Internet.

O Gateway será o ponto responsável por encaminhar o tráfego externo para os Services autorizados.

---

## 8. Exposição HTTP/HTTPS no k3s

O mecanismo de exposição depende da topologia aprovada na seção 5:

- **Gateway API direto (preferencial):** expor o data plane do Gateway Fabric nas portas públicas 80/443 de maneira controlada, sem um segundo proxy HTTP.
- **NGINX externo + Gateway API (condicionada):** disponibilizar um endpoint interno restrito do data plane para que somente o proxy na VPS consiga acessá-lo.

Foram consideradas as opções NodePort, hostPort, hostNetwork e LoadBalancer local. Nenhuma deve ser ativada sem validação de compatibilidade com o k3s single-node, segurança, recuperação e ausência de conflitos de portas.

### 8.1 NodePort

NodePort é uma opção **para o endpoint interno na arquitetura com NGINX externo**, não uma exigência da arquitetura preferencial. O Kubernetes normalmente reserva o intervalo `30000-32767` para NodePorts.

Fluxo exclusivo da alternativa com proxy externo:

```text
NGINX externo na VPS
        |
        v
Endpoint NodePort restrito
        |
        v
Data plane NGINX Gateway Fabric
```

**Requisito de segurança:** não assumir que o UFW sozinho impede o acesso externo a NodePorts. O encaminhamento realizado pelo kube-proxy, com regras de NAT e filtragem, pode não percorrer as mesmas cadeias do firewall local que se espera.

Uma possibilidade a ser investigada para o cenário em que proxy e cluster compartilham a VPS é restringir os endereços de exposição por `nodePortAddresses`. O uso de loopback (`127.0.0.0/8`) **não está garantido em todas as versões e modos de kube-proxy** e não deve ser adotado sem verificação específica.

A implementação deverá avaliar:

- compatibilidade da versão do k3s e do modo de kube-proxy com acesso local restrito;
- necessidade de configuração adicional de kernel e implicações de segurança no modo `iptables`;
- suporte efetivo a NodePort via loopback no modo `nftables` utilizado;
- interfaces e endereços nos quais o NodePort fica realmente acessível;
- alternativas à exposição por NodePort quando não for possível restringi-lo com segurança.

Se o endpoint interno utilizar loopback, o caminho esperado será:

```text
NGINX externo
    |
    v
127.0.0.1:<NodePort>
    |
    v
Data plane NGINX Gateway Fabric
```

Esse exemplo **não constitui uma configuração pronta**. Antes de uso em produção, é obrigatório testar que o proxy alcança o serviço, que o NodePort não responde no IP público e que essa proteção permanece após reinício do k3s e da VPS. Firewall local e controles adicionais do provedor são defesa em profundidade, não comprovação isolada de bloqueio.

### 8.2 hostPort

Permite que um Pod utilize uma porta do nó diretamente. Pode ser avaliado para exposição pública do data plane na topologia preferencial, desde que haja controle das portas 80/443 e prevenção de conflitos.

**Vantagens:** caminho direto e menor dependência de um Service NodePort.

**Limitações:** acoplamento ao nó, restrições de agendamento e riscos de conflitos com outros serviços. A configuração deve ser validada na VPS e na versão do Gateway Fabric adotada.

### 8.3 hostNetwork

Permite que o Pod utilize a rede do host. É alternativa a avaliar para a entrada direta do Gateway, não uma escolha automática.

**Vantagens:** caminho de rede curto em single-node.

**Limitações:** menor isolamento, conflito potencial de portas, maior acoplamento à VPS e comportamento das NetworkPolicies dependente do CNI. Exige análise e testes de segurança.

### 8.4 LoadBalancer local (k3s ServiceLB)

O k3s oferece ServiceLB para disponibilizar Services do tipo `LoadBalancer` em ambientes sem balanceador externo. Essa opção deve ser considerada especialmente na topologia de Gateway API direto, após confirmar como o Service do Gateway Fabric será criado e quais portas serão ocupadas.

A instalação padrão do k3s pode incluir Traefik e ServiceLB. Dependendo da configuração, eles podem reservar as portas 80/443 e conflitar com a exposição do Gateway Fabric ou com um NGINX externo.

**Decisão de implementação ainda pendente:** definir se Traefik será desabilitado ou substituído, e se ServiceLB será mantido ou desabilitado conforme o mecanismo de exposição escolhido. Não há justificativa para exigir `--disable=servicelb` em todas as topologias antes dessa decisão.

Se a topologia escolhida exigir desabilitar componentes padrão do k3s, os parâmetros correspondentes deverão ser documentados e testados junto à instalação; por exemplo, `--disable=traefik` e, somente quando necessário, `--disable=servicelb`.

### 8.5 Critérios de validação

Antes da entrada em produção, comprovar:

1. O data plane atende às portas públicas 80/443 **apenas pelo mecanismo aprovado**.
2. Traefik, ServiceLB, NGINX do host e Gateway Fabric não disputam as mesmas portas.
3. Não existem NodePorts ou Services publicados inadvertidamente no IP público.
4. TLS, redirecionamentos e headers funcionam de acordo com a topologia escolhida.
5. O roteamento para os Services `ClusterIP` funciona, inclusive para os Route Handlers do Next.js no APAE Geral.
6. Os controles de exposição persistem após reinicialização da VPS e do cluster.
7. A decisão sobre uma ou duas camadas de proxy foi registrada e revisada pelo time.

---
