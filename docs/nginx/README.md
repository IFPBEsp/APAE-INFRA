# Estudo de Arquitetura — NGINX e Proxy Reverso para os Serviços APAE

Este estudo foi dividido em partes para facilitar leitura, revisão e manutenção sem perder o conteúdo do documento original.

## Estrutura

1. [Contexto, requisitos e estado atual](01-contexto-e-estado-atual.md)
   - contexto do estudo;
   - requisitos arquiteturais;
   - levantamento dos produtos APAE e do NGINX já existente.

2. [Alternativas e arquitetura recomendada](02-alternativas-e-arquitetura.md)
   - alternativas estudadas;
   - arquitetura NGINX Edge + Gateway API;
   - separação de responsabilidades;
   - NodePort, hostPort e hostNetwork.

3. [TLS, segurança de borda e acesso externo](03-tls-seguranca-e-acesso.md)
   - TLS e certificados;
   - redirects HTTP → HTTPS;
   - forwarded headers;
   - trusted proxies;
   - PROXY Protocol;
   - domínio, CORS e cookies.

4. [Comunicação, aplicações e observabilidade](04-comunicacao-aplicacoes-e-observabilidade.md)
   - comunicação interna;
   - serviços públicos e privados;
   - uploads;
   - timeouts;
   - WebSocket;
   - rate limiting;
   - headers de segurança;
   - HSTS;
   - logs, observabilidade e Request ID.

5. [GitOps, operação, riscos e próximos passos](05-gitops-operacao-riscos-e-proximos-passos.md)
   - organização no repositório;
   - ArgoCD;
   - responsabilidades operacionais;
   - riscos;
   - decisão arquitetural;
   - hipóteses da primeira implementação;
   - pontos pendentes;
   - fora do escopo;
   - próximos passos;
   - referências;
   - conclusão.

## Arquitetura consolidada

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

> **NGINX controla a borda da VPS; Gateway API controla o roteamento das aplicações dentro do Kubernetes.**
