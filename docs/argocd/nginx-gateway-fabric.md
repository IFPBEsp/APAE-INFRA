# NGINX Gateway Fabric no k3s

## Exposição na VPS

O data plane do NGINX Gateway Fabric usa uma réplica e publica as portas
80 e 443 da VPS com `hostPort`. O Service do data plane usa `ClusterIP`.
Essa configuração reserva apenas as portas de entrada necessárias e mantém
a rede do pod separada da rede do host.

| Opção | Avaliação |
| --- | --- |
| `hostPort` | Escolhido para expor 80 e 443 no nó único da VPS. |
| ServiceLB | Exigiria reativar o componente desabilitado na #90 e publicar um Service `LoadBalancer`. |
| `hostNetwork` | Colocaria o pod na rede do host. O gateway precisa de apenas dois mapeamentos de porta. |

O k3s mantém Traefik e ServiceLB desabilitados conforme a #90. As portas
80 e 443 precisam estar livres antes da instalação.

## Versões

- Gateway API `1.6.3`, canal `standard`, com o pacote versionado no APAE-INFRA.
- NGINX Gateway Fabric `2.8.1`, com o chart fixado no commit
  `ed383f6aaa256a3e0b75c89f6d6e9f75fbe5faa3` do repositório oficial.

## Ordem de sincronização

1. Confirmar as permissões do AppProject `apae-infra` e verificar se já existem
   CRDs da Gateway API na VPS. Se existirem, identificar a versão e quem os
   gerencia antes de sincronizar.
2. Sincronizar `gateway-api-crds` e aguardar os CRDs ficarem `Established` e o
   namespace `nginx-gateway` ficar `Active`.
3. Sincronizar `nginx-gateway-fabric` e confirmar que o Job de certificados
   concluiu, o controller está disponível e a GatewayClass `nginx` foi aceita.
4. Sincronizar `nginx-gateway` e confirmar `Accepted=True` e `Programmed=True`
   no Gateway `apae-gateway`.

As três sincronizações são manuais. As duas Applications que instalam CRDs
usam `ServerSideApply=true`.

## Validação externa

Durante o teste da #111, criar o Secret TLS temporário, aplicar o patch do
listener HTTPS e aplicar a HTTPRoute de teste. De fora da VPS, verificar
o retorno `302` em `/__gateway-check` nas portas 80 e 443. Para HTTPS,
usar `curl --resolve` com o hostname `gateway-smoke.test` e confiar
explicitamente no certificado de teste.

Repetir os testes após o reinício do k3s e da VPS. Registrar as condições
do Gateway e da rota, o tipo do Service gerado e as respostas externas.
Depois, remover a rota, o listener temporário e o Secret. O TLS definitivo
e o DNS ficam na #112.
