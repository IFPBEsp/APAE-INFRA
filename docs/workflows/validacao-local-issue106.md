# Revisao local da issue #106

## Revisoes utilizadas

Validacao realizada em 10/11/2026, sem commit, push, alteracao de configuracoes
do GitHub ou operacao no cluster nesta etapa.

- Branch de trabalho: `106-ci-padronizar-publicacao-pela-main-e-promocao-de-imagens-entre-homologacao-e-producao`.
- HEAD do #133: `06ab3c4b32cba31720b68dd8537133d573f3850e`.
- `dev` consultada: `27ac3cc578de3227cf2888cb94c97647c1c72ce3`.
- Workflow do #147: `6427ad688fe30d993b18db48e7e5bde3dc5d6b1f`.

As alteracoes locais foram verificadas no checkout e em uma copia temporaria
da `dev`, preservando os arquivos da base que nao pertencem a esta issue.
Uma segunda copia combinou o publisher com as alteracoes do #147. Essas copias
verificam o conteudo pretendido da integracao; nao representam merge publicado.

## Resultado dos checks

| Verificacao | Resultado |
| --- | --- |
| Suite no checkout local | 61 testes aprovados |
| Suite na previa baseada na `dev` | 61 testes aprovados |
| Suite na previa combinada com o publisher do #147 | 61 testes aprovados |
| actionlint dos workflows alterados e publisher combinado | Sem erros |
| markdownlint dos nove guias revisados | Sem erros |
| Renderizacao Kustomize v5.8.1 | Oito overlays renderizados |
| KubeLinter dos overlays renderizados | Sem erros |
| Kubeconform Kubernetes e ArgoCD | 57 recursos validos, sem erros ou schemas ignorados |
| `git diff --check` | Sem erros |

Os testes usam os scripts reais dos workflows e os manifests versionados em
copias descartaveis. As consultas ao GHCR, verificacoes externas e o envio de
eventos sao simulados. A execucao local nao substitui a verificacao de imagens
reais, os PRs produzidos pela automacao ou o sync e os testes funcionais no
cluster. Os Deployments dos overlays continuam com zero replicas.

## Compatibilidade com o #147

O publisher usa a mesma versao fixada de `actions/attest` e a mesma identidade
Cosign do workflow reutilizavel do #147. As restricoes de repositorio, ref e
commit do produto continuam obrigatorias. A verificacao de proveniencia
seleciona explicitamente o predicado SLSA v1.

A combinacao de texto gera um conflito no ponto em que o #147 acrescenta o
SBOM, imediatamente depois da verificacao de proveniencia. Na previa, foi
preservado o bloco completo do #147: geracao, validacao, atestacao e verificacao
do SBOM antes da assinatura e das tags finais. Nenhum passo de SBOM foi
incorporado ao checkout da #106 por esta verificacao.

Ao integrar os PRs, manter esse bloco e as verificacoes de identidade corrigidas
e executar novamente a suite no resultado efetivo do merge. O #147 continua
sujeito a sua propria revisao e aos checks da branch dele.

## Configuracoes pendentes para a ativacao

Consulta somente de leitura realizada no GitHub; valores de secrets nao foram
obtidos nem copiados.

| Local | Estado observado | Ajuste necessario |
| --- | --- | --- |
| INFRA: `gitops-image-updater` | Permite apenas `dev` | Manter na branch padrao `dev` |
| INFRA: `release-approval` | Permite apenas `dev`; possui revisor | Manter na branch padrao `dev`, preservando revisao |
| INFRA: `production-promotion` | Permite apenas `dev`; possui revisor | Manter na branch padrao `dev`, preservando revisao |
| Geral: `gitops-dispatch` | `main` permitida; App ID e chave presentes | Conferir a instalacao e as permissoes do App na execucao real |
| Atendimento: `gitops-dispatch` | App ID e chave presentes; branches irrestritas | Restringir o environment a `main` |
| Gestao Escolar: `gitops-dispatch` | Environment ausente | Criar para `main` e configurar App ID e chave do dispatcher |
| Site: `gitops-dispatch` | App ID e chave presentes; branches irrestritas | Restringir o environment a `main` |

O receptor executa na branch padrao da INFRA, atualmente `dev`, e abre PRs
para manifests e registros na `main`. As restricoes dos environments da INFRA
devem permitir a branch padrao da automacao. Os jobs locais de recebimento, aprovacao, promocao e
rollback tambem verificam a branch da INFRA antes de utilizar os environments.

## Sequencia para a validacao real

1. Revisar e integrar o #133 e conciliar o publisher com o #147; promover as
   alteracoes da INFRA de `dev` para `main` antes dos callers dos produtos.
2. Aplicar os ajustes de environments, conferir as permissoes dos Apps e definir
   os checks obrigatorios nas protecoes das branches.
3. Integrar as correcoes de vulnerabilidades da #137 e os callers na `main` dos
   produtos. Confirmar o scan das imagens finais, nao apenas dos lockfiles.
4. Aplicar o bootstrap atualizado para namespaces, AppProjects e raiz; solicitar
   o sync da raiz para adotar as filhas com sincronizacao manual.
5. Configurar Secrets, bancos, endpoints e rotas, aprovar a ativacao das replicas
   e validar cada produto em homologacao com as imagens reais verificadas.
6. Registrar a aprovacao, promover os mesmos digests para producao e executar
   rollback, incluindo evidencias dos bloqueios de origem invalida e versao
   incompleta.

Seguir [Releases GitOps](releases-gitops.md) para os inputs dos workflows e as
evidencias exigidas antes de encerrar a issue.

## Atualizacao apos o push

O commit `47e38b7` foi publicado no #133. A atualizacao com a `dev` exigiu
resolver conflitos nas Applications, namespaces, lint e documentacao.
A revisao confirmou que `repository_dispatch` executa na branch padrao `dev`.
A condicao anterior, restrita a `main`, foi corrigida para acompanhar a branch
padrao. Os manifests e registros continuam sendo lidos e atualizados na `main`.
