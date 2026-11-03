# ADR — NGINX Gateway Fabric com Gateway API para entrada HTTP/HTTPS

## Status

Proposto — consolida a arquitetura selecionada no estudo de `docs/nginx`, pendente de confirmação pelo time na revisão da issue #60. A implementação e as validações operacionais ainda não estão concluídas.

Data do registro: 2026-10-13.

## Contexto

Os produtos APAE Geral, APAE Atendimento, APAE Gestão Escolar e Site Comemorativo precisam de uma entrada HTTP/HTTPS segura e reproduzível no cluster **k3s single-node**, hospedado em uma VPS HostGator, conforme o escopo da issue #90.

O roteamento deve acompanhar o ciclo de vida das aplicações por manifests Kubernetes versionados no `APAE-INFRA` e reconciliados pelo ArgoCD. Manter regras específicas de cada produto em um `nginx.conf` no host criaria outra fonte de configuração e acoplaria a operação da VPS às aplicações.

O experimento com NGINX e Docker Compose no Site Comemorativo serve como referência histórica de integração, mas não define a arquitetura de produção no Kubernetes.

Neste ADR, **Gateway API** é a API declarativa do Kubernetes, implementada pelo **NGINX Gateway Fabric**. A expressão “API Gateway” usada para descrever a arquitetura se refere a essa camada de entrada e roteamento; o estudo não seleciona um produto adicional de gerenciamento de APIs.

## Alternativas consideradas

| Alternativa | Avaliação | Resultado |
| --- | --- | --- |
| NGINX externo roteando diretamente para as aplicações | Simples inicialmente, mas exige rotas por produto no host e mantém configuração paralela aos manifests Kubernetes. | Não selecionada. |
| NGINX externo + Ingress Controller | Permite roteamento declarativo, mas adiciona dois proxies e exige coordenação de TLS, headers, logs e timeouts; Ingress oferece menor expressividade para políticas e delegação que Gateway API no estudo. | Não selecionada. |
| NGINX externo + NGINX Gateway Fabric com Gateway API | Mantém HTTPRoute no Kubernetes e permite uma borda independente do cluster, ao custo de dois proxies e maior complexidade operacional. | Alternativa futura, condicionada a requisito concreto. |
| NGINX Gateway Fabric com Gateway API exposto diretamente | Mantém uma única camada de proxy HTTP, TLS no Gateway e roteamento declarativo reconciliado por GitOps. | Selecionada no estudo para a implantação inicial. |

## Decisão

Adotar **NGINX Gateway Fabric como única camada pública de proxy HTTP/HTTPS**, implementando **Gateway API** no k3s. As portas públicas de entrada serão 80/443, com terminação TLS no data plane do Gateway Fabric e encaminhamento apenas para Services autorizados pelas rotas.

O fluxo de tráfego será:

```text
Cliente / Internet
        |
        | DNS aponta para o IP público da VPS
        | HTTP/HTTPS (80/443)
        v
NGINX Gateway Fabric — data plane no k3s
        | TLS e roteamento configurado por Gateway API
        v
Services ClusterIP autorizados
        |
        v
Pods das aplicações APAE
```

O fluxo de configuração será:

```text
Git (APAE-INFRA)
        |
        v
ArgoCD
        |
        v
GatewayClass / Gateway / HTTPRoute e políticas suportadas
        |
        v
Controller do NGINX Gateway Fabric
        |
        v
Configuração do data plane NGINX
```

`Gateway` e `HTTPRoute` são recursos declarativos, não proxies adicionais no caminho da requisição. O controller materializa sua configuração no data plane.

### Responsabilidades e GitOps

- A infraestrutura administra CRDs, controller, `GatewayClass`, `Gateway`, listeners e políticas de associação de rotas, incluindo namespaces e `allowedRoutes`.
- Cada aplicação administra suas `HTTPRoute`, Services, Deployments e configurações, dentro das permissões definidas pela infraestrutura.
- Os recursos Kubernetes são versionados no `APAE-INFRA` e reconciliados pelo ArgoCD após o bootstrap, respeitando a ordem de instalação das dependências.
- Ansible permanece responsável pela configuração do host, instalação do k3s e bootstrap do ArgoCD, conforme o estudo específico.
- Os Services das aplicações permanecem preferencialmente `ClusterIP`; comunicação interna utiliza DNS e Services Kubernetes, sem passar obrigatoriamente pelo Gateway público.
- Arquivos NGINX gerados pelo controller não serão editados manualmente. Políticas utilizarão mecanismos suportados pela versão e pelos schemas instalados.

### TLS e segurança

- Terminar TLS no Gateway e redirecionar HTTP para HTTPS, preservando eventuais exceções necessárias ao desafio ACME escolhido.
- Planejar emissão e renovação com **Let's Encrypt e cert-manager**, validando a integração com Gateway API; declarar recursos `Certificate` explicitamente quando necessário.
- Para um hostname compartilhado com roteamento por path, utilizar um certificado para esse hostname. Wildcard, SAN ou certificados por produto dependem de uma futura estratégia de subdomínios.
- Armazenar chaves privadas em Secrets com acesso restrito, sem texto claro no Git, e monitorar renovação e expiração.
- Permitir inicialmente HTTP entre Gateway e Services internos, sujeito aos requisitos de segurança; TLS interno poderá ser adotado mediante justificativa e suporte.
- Validar o IP de origem efetivamente observado, considerando SNAT/DNAT. Headers `X-Forwarded-*` enviados por clientes não serão aceitos automaticamente como fonte confiável; eventuais proxies confiáveis deverão ter origens explicitamente restritas.
- Manter bancos, storage e interfaces administrativas sem exposição pública direta. Ausência de `HTTPRoute` não substitui controles de rede e autenticação.
- Validar cookies, CORS, CSRF e autenticação por aplicação. Compartilhar hostname não implica compartilhar sessões ou autorizações.

### Roteamento dos produtos

A referência inicial é um hostname compartilhado com **roteamento por path**, condicionado à compatibilidade das aplicações. Subdomínios poderão ser considerados mediante revisão da estratégia pública.

| Produto | Encaminhamento e restrições |
| --- | --- |
| APAE Geral | `/apae-geral` vai para o frontend Next.js, incluindo `/apae-geral/api/*`, que pertence aos Route Handlers. O Spring é acessado pelo Service interno; não criar rota pública desse prefixo `/api` para o Spring. |
| APAE Gestão Escolar | `/gestao-escolar` atende o frontend; `/gestao-escolar/api` corresponde ao acesso ao backend no modelo estudado. Validar os paths e rewrites reais antes de definir a rota definitiva. |
| Site Comemorativo | `/site-comemorativo` atende o Next.js; o `NEXT_PUBLIC_BASE_PATH` usado no build deve coincidir com o prefixo publicado. |
| APAE Atendimento | A publicação em `/atendimento` fica bloqueada até adequar o `basePath` do frontend e substituir a URL de API identificada como `http://localhost:8080` no build por um endereço alcançável pelo navegador em produção. |

Uma regra `PathPrefix` não implica reescrita automática da URL nem corrige assets, cookies, redirecionamentos ou configuração de API. Chamadas executadas no navegador precisam de endereços públicos alcançáveis; chamadas server-side podem utilizar Services internos.

### Políticas de tráfego e observabilidade

Configurar limites de corpo e timeouts compatíveis com cada aplicação, considerando uploads próximos de 50 MB identificados no estudo e overhead multipart. Não elevar os limites globais além do necessário nem presumir que os padrões atendem aos produtos.

Rate limiting, headers de segurança, redução de informações de versão e suporte a WebSocket dependerão dos recursos efetivamente suportados e das necessidades dos produtos. Controles de autenticação e regras de negócio continuam nas aplicações. HSTS será avaliado após estabilizar HTTPS; `includeSubDomains` e `preload` exigem avaliação específica.

Prever access/error logs, métricas de volume, latência e erros, correlação por request ID validado ou gerado, saúde do controller e do data plane, condições de `Gateway`/`HTTPRoute` e testes externos HTTP/HTTPS. A integração prevista considera Loki/Grafana para logs e Prometheus para métricas, sujeita à instalação. Logs devem minimizar dados sensíveis e ter retenção e acesso definidos.

## Motivação

A exposição direta reduz os componentes que precisam ser mantidos e observados na VPS e evita duplicar TLS, logs, timeouts e políticas entre dois proxies. Gateway API separa a administração da entrada das regras por aplicação e mantém o roteamento declarativo no Kubernetes.

Novos produtos podem ser incorporados por manifests e `HTTPRoute`, sem adicionar regras específicas ao host. Essa escolha preserva o Git como fonte da verdade e a reconciliação pelo ArgoCD.

## Consequências

### Positivas

- Uma única camada de proxy HTTP e menor complexidade operacional.
- Roteamento auditável, reproduzível e integrado ao fluxo GitOps.
- Separação de responsabilidades entre infraestrutura e aplicações.
- Services internos sem publicação individual desnecessária.
- Inclusão de novos produtos sem alterar regras de roteamento da VPS.

### Negativas e riscos

- A VPS e o k3s single-node continuam como ponto único de falha; a entrada pública também depende do data plane do Gateway.
- Não há borda HTTP independente para servir uma página de manutenção durante indisponibilidade do cluster.
- A exposição em 80/443 exige validação de rede, isolamento, preservação de IP e convivência com os componentes padrão do k3s.
- A implantação depende de CRDs, controller, certificados e rotas instalados e reconciliados na ordem correta.
- As aplicações precisam demonstrar compatibilidade com os paths publicados; o APAE Atendimento exige adequação prévia.
- Políticas podem depender de extensões e capacidades específicas do Gateway Fabric, que deverão ser verificadas na versão adotada.

## Implementação e critérios de validação

Este ADR registra a escolha arquitetural; não fixa versões, domínio, portas internas ou valores de políticas ainda não validados. Antes da entrada em produção, será necessário:

1. Definir versões compatíveis e a ordem de instalação de CRDs do Gateway API, NGINX Gateway Fabric, cert-manager e recursos de entrada e rota.
2. Selecionar e validar a exposição do data plane em 80/443. Avaliar os mecanismos do estudo, incluindo `hostPort`, `hostNetwork` e ServiceLB, sem assumir uma opção como aprovada.
3. Definir a configuração do Traefik e ServiceLB conforme a exposição escolhida, evitando conflitos de portas; a desativação do ServiceLB não é obrigatória em todas as topologias.
4. Definir domínio, listeners, namespaces, `allowedRoutes`, referências autorizadas e controles de acesso e rede. Comprovar que não há Services ou NodePorts internos publicados inadvertidamente.
5. Validar emissão, renovação e recuperação de certificados, redirecionamento HTTPS e funcionamento do desafio ACME.
6. Testar todas as rotas com as aplicações reais, incluindo assets, navegação, autenticação, cookies e redirects. Preservar os Route Handlers do APAE Geral e bloquear Atendimento por path até concluir sua adequação.
7. Testar uploads abaixo, próximos e acima dos limites, respostas `413`, timeouts e WebSocket quando necessário, usando apenas políticas suportadas.
8. Testar headers de origem falsificados e documentar IP observado, efeitos de SNAT e proxies confiáveis antes de aplicar políticas dependentes de IP.
9. Implantar observabilidade e documentar recuperação do Gateway e certificados, incluindo reinicialização da VPS e do k3s; confirmar que rotas e controles de exposição persistem após reinícios.

## Condições para revisão

Reavaliar um NGINX externo somente se houver requisito comprovado de serviços HTTP do host independentes do cluster, página de manutenção durante intervenções, políticas de borda não atendidas pelo Gateway Fabric ou ciclos de vida separados para a entrada pública e o Kubernetes.

Se essa alternativa for aprovada, o NGINX externo conhecerá apenas o endpoint interno restrito do Gateway, mantendo as regras dos produtos em `HTTPRoute`. Um eventual NodePort deverá ter porta fixa declarada e sincronizada com o proxy, restrição de acesso comprovada por testes externos e após reinícios, sem depender exclusivamente do UFW nem presumir suporte a loopback. TLS, headers confiáveis e responsabilidades das duas camadas deverão ser revisados.

A expansão para múltiplos nós ou a mudança para subdomínios também exige revisar as premissas de exposição, disponibilidade e certificados deste ADR.

## Referências

- [Índice e arquitetura consolidada do estudo](../nginx/README.md).
- [Contexto, requisitos e estado atual](../nginx/01-contexto-e-estado-atual.md).
- [Alternativas e arquitetura recomendada](../nginx/02-alternativas-e-arquitetura.md).
- [TLS, segurança de borda e acesso externo](../nginx/03-tls-seguranca-e-acesso.md).
- [Comunicação, aplicações e observabilidade](../nginx/04-comunicacao-aplicacoes-e-observabilidade.md).
- [GitOps, operação, riscos e próximos passos](../nginx/05-gitops-operacao-riscos-e-proximos-passos.md).
- [Issue #60 — Estudo da arquitetura de proxy reverso](https://github.com/IFPBEsp/APAE-INFRA/issues/60).
- [Issue #90 — Provisionamento do cluster k3s](https://github.com/IFPBEsp/APAE-INFRA/issues/90).
- [Issue #63 — Estudo de gerenciamento da VPS com Ansible](https://github.com/IFPBEsp/APAE-INFRA/issues/63).
