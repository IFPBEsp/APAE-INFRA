# ADR — Estratégia GitOps para Terraform e ArgoCD

- **Status:** Proposto para aprovação do time
- **Issue:** #59
- **Data:** 23/09/2026

## Contexto

O `APAE-INFRA` utiliza Git como fonte da verdade para infraestrutura e configuração, Terraform como ferramenta de Infrastructure as Code e ArgoCD como reconciliador GitOps dos recursos Kubernetes.

Era necessário decidir como o Terraform deveria se encaixar no modelo GitOps do projeto.

Foram avaliadas quatro abordagens:

1. GitHub Actions + Terraform;
2. ArgoCD + Terraform Operator;
3. ArgoCD + Crossplane;
4. arquitetura híbrida com responsabilidades separadas.

A decisão precisava considerar:

- bootstrap;
- state remoto;
- locking;
- drift;
- segurança;
- ambientes;
- ciclo `plan/apply`;
- complexidade operacional;
- capacidade de evolução.

## Decisão

Adotar a seguinte arquitetura:

```text
Git
│
├── terraform/
│      ↓
│   GitHub Actions
│      ↓
│   Terraform
│      ↓
│   infraestrutura fundacional
│
└── kubernetes/
       ↓
     ArgoCD
       ↓
    Kubernetes
       ↓
    aplicações
```

### Responsabilidades

#### Terraform + GitHub Actions

Responsáveis pela infraestrutura fundacional e pelo ciclo automatizado de Terraform.

#### ArgoCD

Responsável pela reconciliação dos recursos Kubernetes após a existência do cluster.

#### Git

Permanece como fonte da verdade dos dois domínios.

### Regras associadas à decisão

1. ArgoCD não executará Terraform diretamente.
2. Terraform Operator não será adotado neste momento.
3. Crossplane não será adotado neste momento.
4. Remote state e locking são pré-requisitos para automatizar `terraform apply`.
5. Drift de infraestrutura fundacional será inicialmente detectado e analisado, não corrigido automaticamente.
6. Terraform e ArgoCD não devem possuir ownership simultâneo sobre o mesmo recurso.
7. Infraestrutura complementar poderá ser reavaliada futuramente para Operator/Crossplane.

## Justificativa

A alternativa escolhida:

- evita dependência circular no bootstrap;
- aproveita a pipeline Terraform já existente;
- preserva o ciclo `plan → review → apply`;
- mantém Terraform em seu domínio nativo;
- mantém ArgoCD no domínio Kubernetes;
- reduz componentes adicionais;
- reduz RBAC e credenciais dentro do cluster;
- mantém Git como fonte da verdade;
- permite evolução posterior.

Terraform Operator e Crossplane são tecnicamente válidos, mas adicionam complexidade operacional sem que exista requisito atual suficiente para justificar sua adoção.

## Consequências positivas

- responsabilidades claras;
- menor complexidade;
- bootstrap independente do cluster;
- auditoria via Git e GitHub Actions;
- aproveitamento da infraestrutura existente;
- menor quantidade de componentes;
- possibilidade de adoção futura de controllers sem reescrever a fundação.

## Consequências negativas

- Terraform via pipeline não oferece reconciliation loop contínuo por padrão;
- drift precisará ser detectado por mecanismo adicional;
- backend remoto precisa ser definido;
- pipeline de apply ainda precisa ser implementada;
- aprovações por ambiente ainda precisam ser configuradas.

## Alternativas rejeitadas no momento

### ArgoCD + Terraform Operator

Não adotado nesta etapa porque aumenta o número de componentes e continua dependendo de um bootstrap externo ao cluster.

### ArgoCD + Crossplane

Não adotado nesta etapa porque sua principal vantagem está em cenários de Platform Engineering/self-service que não representam a necessidade atual do projeto.

## Reavaliação

Este ADR deve ser reavaliado se surgirem:

- múltiplos clusters;
- muitos stacks;
- ambientes efêmeros;
- múltiplos times;
- self-service;
- adoção estratégica de HCP Terraform;
- necessidade real de reconciliação contínua de infraestrutura externa;
- evolução formal para Platform Engineering.

## Referências

- ArgoCD — Declarative Setup  
  <https://argo-cd.readthedocs.io/en/latest/operator-manual/declarative-setup/>

- HashiCorp — Running Terraform in Automation  
  <https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform>

- HashiCorp — S3 Backend  
  <https://developer.hashicorp.com/terraform/language/backend/s3>

- HCP Terraform Operator  
  <https://developer.hashicorp.com/terraform/cloud-docs/integrations/kubernetes>

- Crossplane with ArgoCD  
  <https://docs.crossplane.io/latest/guides/crossplane-with-argo-cd/>
