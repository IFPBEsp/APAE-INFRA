# Homologação, promoção e rollback de releases

O resultado da revisão local e as configurações pendentes de ativação estão em
[Validação local da issue #106](validacao-local-issue106.md).

## Branches, ambientes e aprovação

A `main` do APAE-INFRA contém os manifests reconciliados pelo ArgoCD e os
registros de releases. As mudanças de implementação continuam passando por
`dev` e pela promoção da infraestrutura para `main` antes da ativação.
O nome do overlay `dev` identifica homologação, não uma branch de origem.

| Produto no payload | Diretório Kubernetes | Imagens da release |
| --- | --- | --- |
| `apae-geral` | `apae-geral` | frontend + backend |
| `apae-atendimento` | `apae-atendimento` | frontend + backend |
| `apae-gestao-escolar` | `gestao-escolar` | frontend + backend |
| `site-comemorativo` | `site-comemorativo` | imagem única |

Todos os PRs de atualização de homologação, registro de aprovação, promoção e
rollback têm como destino `main`. Uma notificação comum só pode alterar
`overlays/dev` e o registro candidato; não altera `overlays/prod`.
As tags `sha-<7 primeiros caracteres do commit>` servem para consulta. Os
overlays e a promoção usam os digests completos.

A raiz e as oito Applications filhas usam `targetRevision: main` e sync manual.
Não há auto-merge nem acionamento do ArgoCD pelos workflows de release.
O bootstrap Ansible é responsável pelos AppProjects, namespaces e raiz;
sincronizar a raiz registra as Applications filhas. Cada filha deve ser
sincronizada explicitamente depois do merge do PR do seu ambiente.

Ao adotar esses manifests num cluster existente, atualizar a raiz pelo
bootstrap e sincronizá-la antes de validar o novo comportamento das filhas.
A remoção do auto-sync no Git só produz efeito no cluster após essa adoção.

## Configuração dos GitHub Apps e environments

| Local | Environment | Credenciais |
| --- | --- | --- |
| Cada produto | `gitops-dispatch` | variável `GITOPS_DISPATCH_APP_ID`; secret `GITOPS_DISPATCH_APP_PRIVATE_KEY` |
| INFRA | `gitops-image-updater` | secrets `IMAGE_UPDATER_APP_ID` e `IMAGE_UPDATER_APP_PRIVATE_KEY` |
| INFRA | `release-approval` | os mesmos secrets do App de PRs |
| INFRA | `production-promotion` | os mesmos secrets do App de PRs |

O App de notificação tem `contents: write` no APAE-INFRA, necessário ao dispatch.
O App de PRs tem `contents: write` e `pull_requests: write` somente na INFRA.
Não compartilhar a chave do App de PRs com os produtos.

Restringir os quatro environments à branch `main` do respectivo repositório.
`release-approval` e `production-promotion` exigem um revisor humano, com
autoaprovação pelo solicitante desabilitada. As branches protegidas exigem
aprovação de PR e resolução de discussões. Os workflows também restringem a
execução à `main` da INFRA antes do uso das credenciais dos environments.

A consulta de imagens privadas pode usar `GHCR_READ_USERNAME` e
`GHCR_READ_TOKEN` no receptor. Essas credenciais não autorizam abertura de PRs.
O job de publicação do produto concede `contents: read`, `packages: write`,
`id-token: write` e `attestations: write` ao workflow reutilizável.

## Publicação e candidato

1. As validações do produto devem passar antes da publicação. Ao compor os
   callers, ligar os jobs de publicação às validações com `needs`; apenas ter
   um workflow de testes separado não cria essa dependência.
2. Publicar a partir da `main`, chamando o reutilizável em `@main` ou em um
   commit completo já revisado. Remover referências à branch de desenvolvimento
   da #106. Conciliar os PRs antigos que apenas trocam `@dev` por `@main`.
3. Build e Trivy precisam terminar antes das tags finais. A assinatura Cosign
   e a proveniência SLSA são verificadas antes da promoção das tags.
4. O caller notifica somente após todas as imagens da versão serem publicadas.
   Frontend e backend devem usar o mesmo commit, execução e tentativa.
5. O receptor confere tag/digest no GHCR, proveniência SLSA autenticada,
   repositório, commit da `main`, workflow autorizado e assinatura Cosign.
   A identidade Cosign é a do reutilizável da INFRA, com ref `main` ou SHA
   completo; o repositório, ref e commit do produto também são obrigatórios.
6. O PR inclui o overlay de homologação e
   `releases/candidates/<produto>/<commit completo>.json`. Conferir os digests,
   a origem, os checks e a revisão humana antes do merge.

O registro conjunto contém `application`, `source_repository`, `source_commit`,
`workflow_run` e `images` com `backend` e `frontend`. Cada imagem contém
`image`, `tag`, `digest` e `workflow_run`. O registro do Site contém esses
metadados de imagem diretamente e acrescenta `verification_run` da INFRA;
seu `workflow_run` de publicação é extraído da atestação autenticada.
Um payload com uma metade da versão não autoriza o fluxo conjunto.

Registros existentes não são substituídos por uma nova publicação do mesmo
commit com conteúdo diferente. Em caso de conflito, investigar a diferença e
publicar uma nova revisão do produto. Não editar o candidato para forçar uma
promoção. Uma nova publicação pode atualizar a homologação, mas a promoção
continua selecionando explicitamente um commit aprovado.

## Frontends e a mesma imagem nos dois ambientes

`NEXT_PUBLIC_*` e os rewrites de `next.config.*` são avaliados no build.
Configurar uma variável no Deployment não altera automaticamente esses valores
no bundle ou no rewrite já compilado.

Os callers devem usar caminhos públicos relativos e nomes de Service iguais
nos dois namespaces. O DNS curto resolve o backend no namespace do frontend:

| Produto | `NEXT_PUBLIC_API_URL` | Backend interno estável |
| --- | --- | --- |
| Geral | `/apae-geral/api` | `http://api:8080/apae-geral/api` para `API_URL` em runtime |
| Atendimento | `/atendimento/api` | `BACKEND_URL=http://atendimento:8080` |
| Gestão Escolar | `/gestao-escolar/api` | `BACKEND_URL=http://gestao-escolar-backend:8080` |

Esses nomes correspondem aos Services versionados. Não usar o nome da imagem
Docker como se fosse o nome do Service. Evitar `vars.NEXT_PUBLIC_API_URL` ou
`vars.BACKEND_URL` específicos de ambiente no build de uma imagem promovível.
Se uma configuração precisar variar entre os ambientes, o produto deve ler
essa configuração no servidor em runtime, sem incorporá-la ao bundle.

Antes do aceite, revisar também as rotas de servidor do Geral que ainda usam
`NEXT_PUBLIC_API_URL` para fazer chamadas do servidor: uma URL relativa do
navegador não substitui `API_URL` absoluto no servidor. O Site exige a revisão
dos seus próprios valores públicos e Secrets de runtime.

## Homologação e registro de aprovação

Depois do merge do candidato, sincronizar manualmente a Application `*-dev`
e validar as funcionalidades, a saúde dos workloads e os digests realmente
executados. Anexar a evidência a uma issue, PR ou execução do GitHub sob IFPBEsp.
Um overlay coincidente no Git comprova intenção; não comprova saúde do cluster.

Executar o workflow **Approve homologated release** em `main`, informando
`application`, `candidate_commit` completo, `evidence_url` e `approval_reason`.
O environment exige revisão antes do job. O workflow compara o candidato com
o overlay e abre outro PR com `releases/approved/<produto>/<commit>.json`.

O registro aprovado inclui o hash SHA-256 dos bytes do candidato, os digests e
a evidência de homologação. A aprovação torna-se efetiva após revisão e merge
desse PR. Se uma nova candidata já substituiu os digests no overlay, a aprovação
da candidata anterior é recusada: homologar a versão selecionada novamente.

## Promoção, bootstrap de produção e rollback

Executar **Promote approved release to production** em `main`, com o produto,
commit aprovado e motivo. O workflow lê o registro aprovado já integrado,
valida seu hash e abre um PR alterando exclusivamente as imagens de
`overlays/prod`. O corpo referencia o registro aprovado. Não executa build,
assinatura nem publicação de imagens. Revisar, mesclar e sincronizar a
Application `*-prod` manualmente. Comparar os digests com os de homologação.

Os overlays iniciais de produção usam `unpublished` e zero réplicas. Não existe
digest real de produção antes da primeira promoção. O workflow substitui essa
referência pelos digests aprovados e preserva a quantidade de réplicas.
Não aumentar réplicas antes de preparar Secrets, bancos, endpoints de runtime,
rotas, TLS e a primeira promoção. O `management-app` permanece desativado e
fora da combinação frontend/backend, pois não possui imagem publicada.

Para rollback, executar **Roll back production to previously deployed release**
em `main`, informando um commit aprovado anteriormente, produto e motivo do
incidente. Os digests precisam aparecer juntos numa mesma revisão do histórico
da `main` para aquele overlay de produção. Após revisão e merge do PR de
rollback, sincronizar manualmente e confirmar os digests em execução.
O histórico do Git demonstra a configuração anterior, não uma implantação
bem-sucedida: manter também a evidência da sincronização e da saúde do cluster.

## Evidências para encerrar a #106

Para cada produto, registrar na issue:

- Publicação real da `main`, commit completo, execução, tag e digests.
- Scan da imagem final, assinatura e atestações verificadas.
- Evento recebido, execução da INFRA e PR com o registro candidato.
- Sync manual e validação funcional em homologação, com digests em execução.
- PR do registro aprovado e sua evidência de homologação.
- PR de promoção e confirmação dos mesmos digests em produção, sem rebuild.
- Versão posterior e rollback para uma combinação anterior aprovada.
- Falhas controladas: origem inválida, frontend/backend incompletos e tentativa
  de atualização direta de produção, todas sem PR de atualização aceito.

Os testes locais cobrem scripts, manifests e cenários de falha com serviços
simulados. Não substituem as execuções no GHCR, Actions e cluster.

```bash
python3 -m unittest discover -s tests -v
```

Usar Kustomize v5.8.1, como fixado em `.github/actions/setup-kustomize`.
