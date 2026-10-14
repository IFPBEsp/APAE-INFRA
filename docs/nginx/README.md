# Estudo de Arquitetura — NGINX e Proxy Reverso para os Serviços APAE

Este estudo documenta a arquitetura de entrada HTTP/HTTPS dos serviços APAE hospedados em um cluster Kubernetes **k3s single-node** na VPS HostGator.

O estudo foi dividido em cinco partes para facilitar a leitura, a revisão e a manutenção das decisões arquiteturais.

A decisão foi consolidada no [ADR 003 — NGINX Gateway Fabric com Gateway API para entrada HTTP/HTTPS](../adr/003-nginx-gateway-fabric-e-gateway-api.md), com status proposto para revisão pelo time.

## Estrutura

1. [Contexto, requisitos e estado atual](01-contexto-e-estado-atual.md)
   - Contexto e requisitos arquiteturais.
   - Levantamento das aplicações APAE.
   - Particularidades de roteamento por path.
   - NGINX existente no ambiente Docker Compose, utilizado como referência histórica.

2. [Alternativas e arquitetura recomendada](02-alternativas-e-arquitetura.md)
   - Comparação entre NGINX externo, Ingress Controller e Gateway API.
   - Justificativa da escolha do Gateway API exposto diretamente.
   - NGINX Gateway Fabric e separação de responsabilidades.
   - Roteamento declarativo com Gateway e HTTPRoute.
   - Alternativas de exposição no k3s: NodePort, hostPort, hostNetwork e ServiceLB.
   - Requisitos de segurança e prevenção de conflitos de portas.

3. [TLS, segurança de borda e acesso externo](03-tls-seguranca-e-acesso.md)
   - Terminação TLS no NGINX Gateway Fabric.
   - Gerenciamento de certificados com cert-manager.
   - Comparação entre certificados individuais, SAN e wildcard.
   - Redirecionamento HTTP para HTTPS.
   - Forwarded headers, trusted proxies e IP real.
   - Estratégia de domínios, CORS, cookies e autenticação.

4. [Comunicação, aplicações e observabilidade](04-comunicacao-aplicacoes-e-observabilidade.md)
   - Comunicação interna por Services Kubernetes.
   - Proteção de serviços administrativos e bancos de dados.
   - Uploads e limites de requisição.
   - Timeouts e WebSocket.
   - Rate limiting e headers de segurança.
   - HSTS e exposição de informações do servidor.
   - Logs, métricas, Request ID e saúde do Gateway.

5. [GitOps, operação, riscos e próximos passos](05-gitops-operacao-riscos-e-proximos-passos.md)
   - Organização dos recursos Kubernetes no repositório.
   - Reconciliação dos recursos pelo ArgoCD.
   - Responsabilidades operacionais.
   - Riscos e requisitos de segurança.
   - Decisão arquitetural e justificativas.
   - Requisitos para a primeira implementação.
   - Pendências técnicas e validações necessárias.
   - Referências e conclusão.

## Arquitetura consolidada

A arquitetura selecionada utiliza **NGINX Gateway Fabric exposto diretamente**, sem uma segunda camada obrigatória de NGINX fora do Kubernetes.

```text
Internet
   |
   | HTTPS
   v
DNS
   |
   v
IP público da VPS HostGator
   |
   | Portas 80/443
   v
NGINX Gateway Fabric
   | TLS / entrada HTTP/HTTPS
   v
Gateway API / HTTPRoute
   |
   v
Services ClusterIP
   |
   v
Pods das aplicações APAE
```

O NGINX Gateway Fabric implementa o processamento do tráfego HTTP/HTTPS. O Gateway API fornece os recursos declarativos de entrada e roteamento, enquanto o ArgoCD reconcilia as configurações versionadas no Git.

A emissão e renovação de certificados serão planejadas com cert-manager, conforme a integração definida na implementação.

### Justificativa da escolha

A arquitetura foi selecionada por:

- Utilizar uma única camada de proxy HTTP.
- Reduzir a complexidade operacional da VPS.
- Evitar duplicação de TLS, logs e políticas de tráfego.
- Centralizar o roteamento em recursos HTTPRoute.
- Facilitar a integração com ArgoCD e GitOps.
- Manter os Services internos sem exposição pública direta.
- Facilitar a inclusão de novas aplicações.

A alternativa **NGINX externo + Gateway API** foi estudada, mas não selecionada para a implementação inicial por não haver, até o momento, um requisito operacional comprovado que justifique uma segunda camada de proxy.

## Requisitos pendentes de implementação

A decisão arquitetural não representa uma implantação já concluída.

Ainda deverão ser definidos e validados:

- Exposição segura do Gateway Fabric nas portas públicas 80/443.
- Configuração do Traefik e do ServiceLB no k3s.
- Instalação e ordenação dos CRDs do Gateway API e do controller.
- Integração do cert-manager e emissão dos certificados.
- Configuração das políticas de segurança, limites e observabilidade.
- Adequação do frontend APAE Atendimento ao prefixo `/atendimento`.
- Validação de roteamento, TLS, disponibilidade e recuperação após reinicializações.

Essas atividades deverão ser executadas e validadas antes da entrada em produção.

## Issues relacionadas

- [#60 — Estudo da arquitetura de proxy reverso](https://github.com/IFPBEsp/APAE-INFRA/issues/60)
- [#90 — Provisionamento do cluster k3s](https://github.com/IFPBEsp/APAE-INFRA/issues/90)
- [#63 — Estudo de gerenciamento da VPS com Ansible](https://github.com/IFPBEsp/APAE-INFRA/issues/63)

---

> **Decisão arquitetural:** o NGINX Gateway Fabric será a camada de entrada HTTP/HTTPS do cluster k3s, com roteamento declarativo pelo Gateway API e gerenciamento dos recursos Kubernetes via ArgoCD. O NGINX externo não faz parte da arquitetura inicial selecionada.
