# Validação das Applications e overlays — issue #92

## Revisão e condições do teste

Validação realizada em 09/11/2026 na VPS, com autorização para alternar
temporariamente do modo Compose para o cluster e retornar ao Compose ao final.

- PR: [#120](https://github.com/IFPBEsp/APAE-INFRA/pull/120).
- Commit validado: `3e124a260de1483837fbda35f813cd1d8f66477f`.
- Os manifests definitivos das Applications continuam com `targetRevision: main`.
- Os quatro overlays foram mantidos com zero réplicas em todos os Deployments.

Na data do teste, `argocd/apps/dev/` ainda não existia na `main` remota.
O PR tem `dev` como branch de destino; seu merge nessa branch, sozinho, não
disponibiliza os manifests na revisão acompanhada pelo ArgoCD.

Por isso, foi autorizada uma validação **temporária pelo commit do PR**.
Ela comprova a descoberta e a reconciliação dos manifests dessa revisão,
mas não substitui a verificação definitiva após sua integração à `main`.

## Renderização local

Os quatro overlays foram renderizados com Kustomize v5.8.1, verificando:

- Namespace `apae-dev` em todos os recursos.
- Todos os Deployments com `replicas: 0`.
- Ausência de identificações duplicadas entre os produtos.
- Applications definitivas apontando para `main`.

| Application | Recursos renderizados |
| --- | ---: |
| `apae-geral-dev` | 8 |
| `apae-atendimento-dev` | 5 |
| `gestao-escolar-dev` | 6 |
| `site-comemorativo-dev` | 3 |
| **Total** | **22** |

Os checks disponíveis do PR também estavam aprovados: commitlint, lint
Kubernetes, lint ArgoCD, Markdown e testes. Isso não representa aprovação humana.
A suíte local dessa revisão passou com **40 testes**, usando a mesma versão
de Kustomize fixada no CI.

## Preparação no cluster

1. O playbook de alternância ativou o cluster e parou as aplicações Compose.
2. Foi confirmada a ausência prévia das quatro Applications e dos 22 recursos
   de produto, evitando assumir ou remover recursos de outra implantação.
3. Os AppProjects existentes `apae` e `apae-infra` foram comparados com os
   manifests do PR: suas especificações eram iguais e não foram alteradas.
4. A especificação da raiz permanente `apae-root` foi registrada para comparação.
5. O namespace `apae-dev`, antes ausente, foi provisionado pelo Ansible com
   a definição de `argocd/namespaces.yaml`.

O namespace foi preservado após o teste como parte do bootstrap previsto.
Nenhum produto foi iniciado e nenhum acesso aos bancos ou buckets foi
configurado por esta validação.

## Descoberta e sincronização reais

Foi criada a raiz temporária `apae-pr120-validation`, com:

- AppProject `apae-infra`.
- Mesmo repositório, caminho `argocd` e filtro `apps/*/*.yaml` da raiz definitiva.
- Revisão fixada no commit validado.
- Sincronização solicitada manualmente, sem auto-sync da raiz temporária.

A operação da raiz terminou com `phase: Succeeded` e registrou as quatro
Applications definidas no PR. A raiz permanente não foi modificada.

As quatro filhas inicialmente refletiram os manifests definitivos, que apontam
para `main`. Somente nas cópias de teste no cluster, suas revisões foram
temporariamente fixadas no commit autorizado. O auto-sync das filhas permaneceu
com `prune` e `selfHeal` habilitados, como declarado nos manifests.

Resultado observado nas quatro Applications:

```text
NAME                    REVISION                                   SYNC     HEALTH
apae-atendimento-dev    3e124a260de1483837fbda35f813cd1d8f66477f   Synced   Healthy
apae-geral-dev          3e124a260de1483837fbda35f813cd1d8f66477f   Synced   Healthy
gestao-escolar-dev      3e124a260de1483837fbda35f813cd1d8f66477f   Synced   Healthy
site-comemorativo-dev   3e124a260de1483837fbda35f813cd1d8f66477f   Synced   Healthy
```

Também foram confirmados oito Deployments com zero réplicas e ausência de
pods no namespace dos produtos. `Healthy` nesse cenário comprova o estado
dos recursos declarados, não a disponibilidade funcional das aplicações.

## Testes de selfHeal e prune

Os testes utilizaram apenas ConfigMaps não sensíveis no namespace de teste,
com os produtos em zero réplicas:

- **selfHeal:** o valor `SERVER_PORT` do ConfigMap
  `gestao-escolar-backend-config` foi alterado temporariamente de `8080`
  para `8081`. Após solicitar nova comparação, o ArgoCD restaurou `8080`,
  conforme o Git.
- **prune:** foi criado o ConfigMap descartável `pr120-prune-probe`, ausente
  no Git e com identificação de rastreamento da Application de Gestão.
  Após nova comparação, o ArgoCD removeu esse recurso automaticamente.
- A Application de Gestão voltou a `Synced` e `Healthy` após os testes.

Nenhum registro de banco, documento ou credencial foi utilizado nesses testes.

## Limpeza do ambiente temporário

Ao concluir:

1. Foram removidas a raiz temporária e as quatro Applications de teste.
2. Foram removidos apenas os 22 recursos de produto previamente identificados
   como ausentes antes do teste; o ConfigMap descartável já havia sido removido.
3. Foi confirmada a ausência de Deployments, ReplicaSets e pods em `apae-dev`.
4. A especificação da raiz permanente e as políticas dos dois AppProjects
   permaneceram iguais às registradas antes do teste.

O namespace `apae-dev` foi mantido. Os manifests versionados continuam
apontando para `main`; não foi deixado acompanhamento permanente da branch do PR.

O retorno ao Compose concluiu sem falhas:

```text
apae-prod : ok=112 changed=12 unreachable=0 failed=0 skipped=12 rescued=0 ignored=0
```

Uma verificação independente confirmou os cinco endpoints HTTPS com HTTP 200,
timer TLS ativo, registro de modo `compose` e os mesmos IDs completos, horários
de início e volumes de PostgreSQL e MinIO observados antes da janela.
Não houve reinício ou recriação desses dois serviços durante o teste.

```text
apae-prod : ok=6 changed=0 unreachable=0 failed=0 skipped=2 rescued=0 ignored=0
```

A VPS foi deixada no modo Compose, com os produtos disponíveis e o K3s parado.

## Verificação definitiva após integração à main

Para concluir a implantação permanente, em outra janela de manutenção:

1. Disponibilizar na `main` os manifests revisados, respeitando o fluxo de
   integração do repositório. O merge do PR #120 em `dev` não basta.
2. Ativar o modo cluster pelo playbook da issue #140.
3. Reaplicar o bootstrap da issue #91 conforme seu procedimento Ansible,
   incluindo namespace, AppProjects e raiz. Não aplicar objetos de bootstrap
   a partir de uma Application do ArgoCD.
4. Confirmar a descoberta das quatro filhas pela raiz permanente e a
   sincronização dos overlays pela `main`, sem overrides de revisão.
5. Conferir as condições das Applications, os recursos resultantes e as
   réplicas em zero. Não habilitar os produtos sem imagens e configurações
   previamente validadas nas issues de implantação.
6. Retornar ao Compose enquanto esse for o modo de disponibilização dos produtos.

Comandos de consulta no modo cluster:

```bash
sudo k3s kubectl get namespace apae-dev
sudo k3s kubectl get applications -n argocd \
  -o 'custom-columns=NAME:.metadata.name,REVISION:.spec.source.targetRevision,SYNC:.status.sync.status,HEALTH:.status.health.status'
sudo k3s kubectl get deployments,pods -n apae-dev
```

A validação temporária registrada neste documento encerra o teste pré-merge
da revisão. O acompanhamento definitivo pela `main` permanece dependente dessa
integração e da verificação descrita acima.

## Evolução na issue #106

A implementação da #106 acrescenta o ambiente `prod` e remove o auto-sync
da raiz e das filhas para cumprir a revisão e a sincronização manuais.
As evidências acima correspondem exclusivamente à revisão #120 mencionada,
com quatro Applications e auto-sync nas filhas; não validam essa nova revisão.
O procedimento atual está em [Releases GitOps](../workflows/releases-gitops.md).
