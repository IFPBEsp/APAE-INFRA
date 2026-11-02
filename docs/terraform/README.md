# Issue #59 — Estudo de GitOps para Terraform e ArgoCD

Este diretório contém a documentação do estudo arquitetural da issue #59 do `APAE-INFRA`.

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

Não são definidos nesta issue:

- implementação do `terraform apply`;
- escolha final do backend remoto;
- configuração do bucket/state;
- implementação de módulos Terraform;
- provisionamento real da Contabo;
- escolha entre k3s, kubeadm ou outra distribuição Kubernetes;
- Ansible, cloud-init ou mecanismo detalhado de bootstrap;
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
6. [`06-conclusao-e-proximos-passos.md`](./06-conclusao-e-proximos-passos.md)

## Resultado esperado

Ao final do estudo, o time deve conseguir responder de forma objetiva:

- quem provisiona a infraestrutura fundacional;
- quem reconcilia recursos Kubernetes;
- onde o Git se posiciona como fonte da verdade;
- se o ArgoCD deve ou não participar diretamente da execução do Terraform;
- se Terraform Operator ou Crossplane agregam valor no estágio atual;
- quais pré-requisitos devem existir antes de automatizar `terraform apply`.
