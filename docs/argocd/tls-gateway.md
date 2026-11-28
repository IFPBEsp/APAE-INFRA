# Hostname temporário e TLS no Gateway

A [#112](https://github.com/IFPBEsp/APAE-INFRA/issues/112) prepara um hostname
compartilhado para os produtos, com roteamento por paths na
[#113](https://github.com/IFPBEsp/APAE-INFRA/issues/113). O NGINX Gateway Fabric
termina TLS e o cert-manager emite e renova o certificado via HTTP-01.

## Hostname temporário

- Formato `apae-<ipv4-publico-com-hifens>.sslip.io`.
- Manutenção pela equipe de infraestrutura do APAE-INFRA. Luiz
  (`@LuizArtur29`) é o responsável registrado na #112 pelo acompanhamento
  desta implantação.
- O serviço externo sslip.io resolve o IP embutido no hostname. Uma falha no
  serviço pode afetar a entrada e a renovação. Uma troca de IPv4 muda o hostname
  temporário e exige novo certificado, atualização de rotas e revisão das
  configurações de aplicação abaixo.
- Hostname definido: `apae-143-95-170-25.sslip.io`. A consulta do registro `A` a
  `1.1.1.1` retornou o IPv4 confirmado e a entrada externa respondeu em
  HTTP na porta 80 em 28/11/2026.

## Preparar e ativar

1. Concluir a [adoção da #111](nginx-gateway-fabric.md), incluindo a configuração
   de sync da raiz e o bootstrap dos projetos pelo
   [Ansible](../../ansible/docs/argocd-bootstrap-recovery.md). Confirmar que o
   Gateway está `Programmed=True`, que o modo ativo é cluster e que as portas
   TCP 80 e 443 serão atendidas pelo data plane.
2. Confirmar o IPv4 público no provedor e na entrada efetiva do Gateway. De uma
   estação externa à VPS, gerar o hostname e conferir que o DNS público retorna
   esse IPv4. A porta 80 precisa responder de fora e a URL do desafio também
   precisa ser alcançável a partir do cluster durante o self-check.

   ```bash
   read -r -p 'IPv4 público confirmado: ' VPS_IP
   HOSTNAME_APAE="apae-${VPS_IP//./-}.sslip.io"
   dig +short "$HOSTNAME_APAE" A
   curl --noproxy '*' --head --max-time 10 "http://$HOSTNAME_APAE/"
   ```

3. Substituir o exemplo em
   [staging/certificate.yaml](../../kubernetes/infra/nginx-gateway-tls/staging/certificate.yaml).
   O Kustomize replica o nome para o certificado de produção, o listener HTTPS
   e o redirecionamento. Usar o mesmo hostname nas rotas de produto da #113.
   Se houver uma caixa institucional de operações para ACME, configurar
   `spec.acme.email` nos dois Issuers.
4. Sincronizar a raiz para registrar a Application `cert-manager`. Confirmar
   que os CRDs `gateways.gateway.networking.k8s.io` e
   `httproutes.gateway.networking.k8s.io` estão estabelecidos antes do sync do
   cert-manager. Sincronizar `cert-manager` pelo ArgoCD e aguardar
   `Synced/Healthy`, incluindo o webhook e a verificação de inicialização.
5. Alterar `spec.source.path` de
   [nginx-gateway.yaml](../../argocd/apps/infra/nginx-gateway.yaml) para
   `kubernetes/infra/nginx-gateway-tls/staging` na revisão Git adotada pela
   raiz. Sincronizar a raiz e depois a Application `nginx-gateway`. Em staging,
   o Gateway continua com o listener HTTP e o certificado de teste fica em um
   Secret próprio.

   ```bash
   sudo k3s kubectl -n nginx-gateway wait --for=condition=Ready \
     issuer/letsencrypt-staging certificate/apae-staging-tls --timeout=5m
   ```

6. Com a emissão de staging comprovada, atualizar o path da mesma Application
   para `kubernetes/infra/nginx-gateway-tls/production` e sincronizar a raiz.
   Na filha `nginx-gateway`, usar sync seletivo apenas de
   `Issuer/letsencrypt-production` e `Certificate/apae-public-tls`. Esperar
   que ambos fiquem `Ready=True`. Isso mantém o listener HTTP atual disponível
   para o desafio enquanto o certificado confiável é emitido.

   ```bash
   sudo k3s kubectl -n nginx-gateway wait --for=condition=Ready \
     issuer/letsencrypt-production certificate/apae-public-tls --timeout=5m
   ```

7. Sincronizar seletivamente o `Gateway/apae-gateway`. A inclusão da porta
   443 pode recriar o data plane. Aguardar o rollout de
   `deployment/apae-gateway-nginx` e validar o listener `https` com
   `Programmed=True` e `ResolvedRefs=True`, além do acesso HTTPS externo,
   antes de sincronizar `HTTPRoute/apae-http-redirect`. Se houver rotas de
   produto ativas, validar os endpoints HTTPS na mesma janela antes de
   ativar o redirect. Depois, confirmar a convergência de todos os recursos
   da Application. Durante a transição, usar sync sem prune. As rotas da
   #113 devem apontar para `sectionName: https`. Se precisarem vir de outros
   namespaces, autorizar apenas os namespaces previstos no listener HTTPS.

### Verificar HTTPS, redirecionamento e renovação

De fora da VPS, conferir a cadeia e o SAN do certificado servido e inspecionar
o redirecionamento sem segui-lo:

```bash
openssl s_client -connect "$HOSTNAME_APAE:443" -servername "$HOSTNAME_APAE" \
  -verify_hostname "$HOSTNAME_APAE" -verify_return_error </dev/null |
  openssl x509 -noout -issuer -serial -dates -ext subjectAltName
curl --noproxy '*' --head --max-time 10 \
  "http://$HOSTNAME_APAE/apae-geral/exemplo?origem=tls&teste=1"
```

Esperar um `302` cujo `Location` preserve o hostname, o path e os dois
parâmetros. Repetir em HTTPS nos endpoints reais coordenados na #113.
O HTTP-01 cria uma rota temporária no mesmo namespace com correspondência
`Exact` em `/.well-known/acme-challenge/<token>`. Ela tem precedência sobre o
redirecionamento por prefixo `/` para o mesmo hostname. Verificar isso numa
emissão ou renovação real, consultando `Challenge`, `Order` e o estado da rota
temporária enquanto estiverem visíveis. Um path com token fictício pode
redirecionar normalmente.

Com o redirecionamento já ativo, executar uma única renovação controlada em
staging. Confirmar aumento de `status.revision` e atualização do certificado
de staging. Em seguida, em janela acordada, registrar revisão, serial e validade
do certificado servido e repetir para produção, respeitando os
[limites do Let's Encrypt](https://letsencrypt.org/docs/rate-limits/).
Executar o `cmctl` de uma sessão administrativa com acesso ao cluster:

```bash
cmctl renew -n nginx-gateway apae-staging-tls
# Após validar staging e na janela de produção:
cmctl renew -n nginx-gateway apae-public-tls
```

Comparar a revisão do `Certificate` e o serial do certificado apresentado
por uma nova conexão externa. Conferir também se a cadeia continua confiável
e se as rotas dos produtos continuam respondendo. Registrar data, versão,
estados, resultado HTTP e validade em evidência sanitizada da #112. Evitar
incluir chaves, conteúdo de Secrets, tokens ACME ou URLs assinadas. Os alertas
de expiração serão implantados e testados na
[#116](https://github.com/IFPBEsp/APAE-INFRA/issues/116).

### Evidências da validação de 28/11/2026

A VPS foi validada com k3s `v1.36.5+k3s1`, Gateway API `v1.6.3` e
NGINX Gateway Fabric `2.8.1`. Na fase controlada, a Application
`nginx-gateway` foi sincronizada pelo ArgoCD no commit `334b6e3`.
As Applications `cert-manager` e `nginx-gateway` terminaram
`Synced/Healthy`. A adoção pela raiz em `main` segue o procedimento da #111
após a integração do [PR #133](https://github.com/IFPBEsp/APAE-INFRA/pull/133).

| Verificação | Resultado observado |
| --- | --- |
| DNS e porta 80 | O registro `A` no resolvedor público retornou o IPv4 da VPS. A requisição externa recebeu resposta HTTP antes da ativação do redirect. |
| Primeira emissão | Os certificados de staging e de produção atingiram `Ready=True` na revisão 1, nessa ordem, com pedidos ACME `valid`. |
| HTTPS | Listener `Programmed=True` e `ResolvedRefs=True`. Cadeia Let's Encrypt `YR1` e SAN do hostname temporário verificados em conexão externa. |
| Redirecionamento | `302` de HTTP para HTTPS preservou hostname, path `/apae-geral/exemplo` e query `origem=tls&teste=1`. |
| HTTP-01 com redirect ativo | Uma conta temporária de staging passou de autorização `pending` para pedido `valid` usando o mesmo hostname. Seus recursos de teste foram removidos. |
| Renovação | Staging e produção passaram da revisão 1 para a 2. O serial público de produção mudou de final `AE97C` para `72354`, com validade até 26/02/2027 às 13:02:41 UTC. |
| Acesso ao Secret | O RBAC negou à ServiceAccount padrão de `apae-dev` a leitura do Secret TLS de produção. |

O teste HTTPS chegou ao Gateway, que retornou `404` com a cadeia válida.
Os testes de endpoints, cookies, callbacks e demais configurações das
aplicações serão realizados com as rotas de produto da #113.

## Segredos e recuperação

A política da [#93](https://github.com/IFPBEsp/APAE-INFRA/issues/93) usa
Sealed Secrets para segredos declarados no Git. O cert-manager é o responsável
pelos Secrets de conta ACME e de certificado desta configuração. O Gateway
referencia apenas o Secret TLS de produção no próprio namespace. Restringir a
leitura dos Secrets a operadores e workloads autorizados e revisar o RBAC do
namespace antes da publicação. O Git contém apenas referências aos Secrets.

1. Em falha de emissão ou renovação, conferir DNS, porta 80, `parentRefs`,
   condições de `Issuer` e `Certificate` e eventos de `Order` e `Challenge`.
   Preservar o Secret válido durante o diagnóstico.
2. Para recuperação do cluster, seguir
   [backup e restauração do k3s](../../ansible/docs/k3s-backup-restore.md)
   e a [estratégia de recuperação](../backup/03-operacao-e-recuperacao.md)
   da [#107](https://github.com/IFPBEsp/APAE-INFRA/issues/107) e
   [#108](https://github.com/IFPBEsp/APAE-INFRA/issues/108). O datastore
   recuperado pode incluir os Secrets ACME/TLS e deve permanecer protegido
   por criptografia e controle de acesso no destino do backup.
3. Em reinstalação sem um backup utilizável, restaurar a entrada HTTP e
   reinstalar CRDs, controllers e manifests pelo fluxo GitOps. Validar staging
   e reemitir produção antes de ativar o listener HTTPS e o redirect. Se o
   Secret sumiu, observar a reemissão automática. Para forçar renovação de um
   certificado existente após resolver a causa, usar `cmctl renew`.
4. Se for preciso voltar ao Gateway HTTP durante a implantação inicial,
   retirar primeiro a rota de redirecionamento. Reverter a Application para
   a revisão/path anterior, revisar o diff e sincronizar sem purgar CRDs,
   emissores ou certificados válidos.

## Inventário de configurações dependentes de hostname

O inventário parte dos manifests e do [estudo das aplicações](../nginx/01-contexto-e-estado-atual.md).
A #113 e os responsáveis pelos produtos devem confirmar os valores na revisão
de cada imagem antes da entrada pública.

| Área | Configuração a revisar |
| --- | --- |
| Gateway | Hostnames do listener HTTPS, das HTTPRoutes públicas e do redirect. `Certificate.spec.dnsNames`, `issuerRef` e `tls.certificateRefs`. |
| APAE Geral | Prefixo `/apae-geral` e Route Handlers do Next.js em `/apae-geral/api`. Conferir links, redirecionamentos de autenticação e atributos de cookies. O Service da API é interno. |
| Gestão Escolar | Prefixos `/gestao-escolar` e `/gestao-escolar/api`. Conferir `NEXT_PUBLIC_API_URL` no build, rewrites e origem permitida no backend. Uma URL pública diferente exige nova imagem quando embutida no bundle. |
| Site Comemorativo | Conferir `NEXT_PUBLIC_BASE_PATH` e `NEXT_PUBLIC_URL_APAE` no build, links para o APAE Geral e recursos estáticos sob `/site-comemorativo`. |
| APAE Atendimento | Validar suporte do frontend a `/atendimento`, substituir URLs de build para localhost se presentes e conferir `NEXT_PUBLIC_API_URL` e a configuração de origem do backend, incluindo `FRONT_END_URL` se usada na imagem. |
| Autenticação e browser | Conferir CORS, origens confiáveis de CSRF, callbacks, logout e URLs absolutas. Preferir cookies host-only, sem atributo `Domain` para `sslip.io`, e revisar `Secure`, `SameSite` e `Path` por produto. |
| Integrações | Revisar webhooks, e-mails, links externos e endpoints usados em URLs pré-assinadas de storage, quando aplicáveis. Testar a validade das URLs geradas em cada hostname. |

Para cada item, registrar onde o valor é configurado e se é lido em runtime
ou no build. Planejar reconstrução e publicação das imagens com
`NEXT_PUBLIC_*` e quaisquer URLs absolutas embutidas. Vincular as lacunas
de cada produto à #113 ou à issue correspondente do produto.

## Migração para o domínio definitivo

1. Registrar a execução como acompanhamento da #112 e coordenar a janela com
   o [corte definitivo](https://github.com/IFPBEsp/APAE-INFRA/issues/169).
   Confirmar o IPv4 de destino. Criar o registro DNS `A`, e `AAAA` somente
   se toda a entrada estiver pronta em IPv6. Conferir a resolução autoritativa
   e em resolvedores públicos antes de solicitar o certificado.
2. Manter o hostname sslip.io e seu certificado ativos. Declarar um novo
   `Certificate` para o domínio definitivo, com Secret próprio. Usar HTTP-01
   na porta 80 do Gateway e comprovar emissão em staging antes do certificado
   de produção. Aguardar `Ready=True` no certificado de produção.
3. Adicionar um listener HTTPS com hostname e Secret do domínio definitivo.
   Anexar as HTTPRoutes do domínio novo a esse listener. Publicar as imagens
   reconstruídas e aplicar os valores de runtime conforme o inventário.
   Enquanto ambos os nomes estiverem ativos, conferir quais configurações
   precisam aceitar as duas origens.
4. Validar HTTPS, redirect da porta 80, paths e parâmetros, assets, autenticação,
   logout, uploads, callbacks, integrações e URLs pré-assinadas no hostname
   definitivo. Cookies host-only implicam nova autenticação no domínio novo.
   Atualizar consumidores externos e manter os callbacks antigos enquanto
   houver fluxos em andamento. Preservar os endpoints antigos pelo prazo de
   validade dos links assinados ou reemitir esses links.
5. Depois da validação e da janela de convivência, decidir se o hostname
   temporário redirecionará navegação ao definitivo. Testar paths e
   parâmetros no redirect. Remover o listener, as rotas e o certificado
   antigos somente quando callbacks e URLs assinadas antigos tiverem sido
   tratados e o período acordado de reversão tiver terminado.
6. Em regressão, restaurar a revisão GitOps e as imagens/configurações que
   atendem o hostname temporário. Desativar qualquer redirecionamento para o
   domínio novo, restabelecer as origens e callbacks anteriores e validar
   TLS, autenticação e rotas antes de retomar a migração.
