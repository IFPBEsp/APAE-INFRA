# Terraform — arquitetura GitOps e escopo na HostGator

Este diretório contém o estudo arquitetural da issue #59 e sua atualização para a VPS HostGator na issue #86.

A decisão atual está em [Conclusão e próximos passos](06-conclusao-e-proximos-passos.md): Terraform para recursos externos com integração validada, Ansible para host/k3s/bootstrap e ArgoCD para os recursos Kubernetes atribuídos às Applications. A proposta aguarda validação do time. Inventário e acesso operacional ficam fora da documentação pública; a estratégia de backup e recuperação foi encaminhada à issue #107 e sua implementação e teste à #108; a homologação prática de capacidade à #90.

Os documentos 01, 02, 03 e 04 preservam a análise conceitual da issue #59. Menções a provedores e infraestrutura fundacional nesses textos não confirmam contratação nem suporte da HostGator.

O documento 03 será atualizado pelo [PR #101](https://github.com/IFPBEsp/APAE-INFRA/pull/101), que escolheu o HCP Terraform Free. Ele permanece sem alterações neste PR para evitar sobreposição; suas referências históricas não substituem a delimitação atual da HostGator.

## Pergunta central

> **Como aplicar GitOps ao ciclo de vida da infraestrutura Terraform da APAE e qual deve ser o papel do ArgoCD nesse fluxo?**

O objetivo desta documentação é sustentar uma decisão arquitetural. Ela não descreve toda a implementação futura do Terraform nem substitui runbooks, documentação operacional ou issues específicas de execução.

## Escopo do estudo

O estudo cobre:

- GitOps aplicado ao Terraform;
- responsabilidades de Git, Terraform, GitHub Actions, ArgoCD e Kubernetes;
- alternativas arquiteturais;
- problema de bootstrap;
- separação entre infraestrutura fundacional e complementar;
- Terraform State remoto;
- locking e concorrência;
- drift detection;
- segurança necessária para avaliar as alternativas;
- separação entre ambientes;
- ciclo `plan` / `review` / `apply`;
- falhas parciais e rollback em nível conceitual;
- decisão arquitetural;
- um ADR consolidando a decisão;
- próximos passos que deverão virar issues próprias.

## Fora do escopo

O estudo original #59 não definiu os itens abaixo. A issue #86 delimita o papel do Ansible e a distribuição k3s como arquitetura-alvo; implementação e escolhas operacionais continuam nas issues específicas:

- implementação do `terraform apply`;
- implementação do backend remoto HCP Terraform (issue #87 / PR #101, ainda pendente de integração);
- configuração do bucket/state;
- implementação de módulos Terraform;
- provisionamento real da VPS ou de outros provedores;
- implementação do k3s e homologação de capacidade (issue #90);
- playbooks Ansible e mecanismo detalhado de bootstrap (issue #90, conforme ADR 004);
- TFLint, Checkov, OPA ou outra estratégia de Policy as Code;
- `terraform test` ou framework de testes;
- Vault, External Secrets ou secret manager;
- disaster recovery detalhado;
- RTO/RPO;
- runbooks operacionais;
- upgrades de Kubernetes, ArgoCD ou VPS;
- política completa de backup;
- implementação de Terraform Operator ou Crossplane.

Esses assuntos podem ser derivados da decisão arquitetural, mas devem ser tratados em issues próprias.

## Documentos

1. [`01-contexto-e-principios.md`](./01-contexto-e-principios.md)
2. [`02-alternativas-arquiteturais.md`](./02-alternativas-arquiteturais.md)
3. [`03-bootstrap-state-locking-e-drift.md`](./03-bootstrap-state-locking-e-drift.md)
4. [`04-seguranca-ambientes-e-ciclo-terraform.md`](./04-seguranca-ambientes-e-ciclo-terraform.md)
5. [`05-decisao-arquitetural.md`](./05-decisao-arquitetural.md)
6. [`06-conclusao-e-proximos-passos.md`](./06-conclusao-e-proximos-passos.md) — capacidades da VPS, escopo da issue #86, responsabilidades e pendências de validação

## Resultado esperado

Ao final do estudo, o time deve conseguir responder de forma objetiva:

- quem provisiona a infraestrutura fundacional;
- quem reconcilia recursos Kubernetes;
- onde o Git se posiciona como fonte da verdade;
- se o ArgoCD deve ou não participar diretamente da execução do Terraform;
- se Terraform Operator ou Crossplane agregam valor no estágio atual;
- quais pré-requisitos devem existir antes de automatizar `terraform apply`.
