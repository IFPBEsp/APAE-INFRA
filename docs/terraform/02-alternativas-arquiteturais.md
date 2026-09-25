# Alternativas arquiteturais

Este documento compara as alternativas consideradas para aplicar GitOps ao Terraform no `APAE-INFRA`.

---

## 1. Alternativa A — GitHub Actions + Terraform

### Funcionamento

```text
Git
 ↓
Pull Request
 ↓
GitHub Actions
 ↓
terraform fmt / validate / plan
 ↓
review
 ↓
merge / aprovação
 ↓
terraform apply
 ↓
infraestrutura
```

Git continua sendo a fonte da verdade.

Terraform continua sendo responsável pelo estado da infraestrutura.

GitHub Actions é o executor do ciclo de automação.

### Benefícios

- baixa complexidade;
- aproveita ferramentas já utilizadas pelo projeto;
- aproveita a pipeline Terraform já existente;
- não depende do Kubernetes para provisionar a infraestrutura;
- preserva o fluxo `plan → review → apply`;
- fácil associação entre commit, PR e mudança;
- Terraform mantém state, locking e providers em seu modelo nativo;
- menor quantidade de componentes adicionais;
- debugging concentrado em GitHub Actions e Terraform;
- implantação incremental.

### Limitações

- não possui reconciliation loop contínuo por padrão;
- drift precisa ser detectado por execução posterior;
- remote state e locking precisam ser configurados;
- controle de `apply` precisa ser implementado.

### Aderência ao APAE-INFRA

Alta.

A infraestrutura atual do repositório já possui parte significativa desse fluxo.

---

## 2. Alternativa B — ArgoCD + Terraform Operator

### Funcionamento conceitual

```text
Git
 ↓
ArgoCD
 ↓
Custom Resources
 ↓
Terraform Operator
 ↓
serviço/executor Terraform
 ↓
infraestrutura
```

O ponto importante é que ArgoCD não executaria diretamente:

```bash
terraform apply
```

ArgoCD reconciliaria recursos Kubernetes.

Um Operator observaria esses recursos e seria responsável por acionar o ciclo Terraform.

No caso do HCP Terraform Operator, o Operator integra Kubernetes ao HCP Terraform, que gerencia workspaces/runs.

### Benefícios

- aproxima Terraform do modelo baseado em controllers;
- permite declarar recursos relacionados ao Terraform via Kubernetes;
- pode oferecer reconciliação contínua;
- mantém Git no fluxo;
- pode centralizar execução, state e runs em uma plataforma especializada.

### Custos

Passam a existir mais componentes:

```text
Git
ArgoCD
Kubernetes
Terraform Operator
HCP Terraform ou executor equivalente
Terraform
Provider
Infraestrutura externa
```

Isso adiciona:

- dependências;
- RBAC;
- secrets;
- lifecycle do Operator;
- observabilidade adicional;
- troubleshooting distribuído;
- possível dependência SaaS;
- maior curva de aprendizado.

### Limitação de bootstrap

O Operator só existe depois que:

```text
Kubernetes
```

já existe.

Logo, ele não elimina a necessidade de uma camada externa para provisionar o cluster que hospedará o Operator.

### Aderência ao APAE-INFRA

Média.

É tecnicamente válida, porém o estudo não identificou uma necessidade atual que compense a complexidade adicionada.

---

## 3. Alternativa C — ArgoCD + Crossplane

### Funcionamento

```text
Git
 ↓
ArgoCD
 ↓
Custom Resources
 ↓
Crossplane
 ↓
Provider
 ↓
infraestrutura externa
```

Crossplane transforma Kubernetes em um control plane também para recursos externos.

A infraestrutura passa a ser representada por APIs Kubernetes.

### Benefícios

- reconciliação contínua;
- modelo Kubernetes-native;
- integração natural com GitOps;
- possibilidade de criar abstrações próprias;
- potencial para self-service;
- forte aderência a cenários de Platform Engineering.

Exemplo conceitual futuro:

```yaml
apiVersion: infra.apae.ifpb.edu.br/v1alpha1
kind: ApaeEnvironment
metadata:
  name: atendimento-prod
spec:
  database: true
  storage: true
```

### Custos

- CRDs adicionais;
- Providers Crossplane;
- Compositions;
- lifecycle de controllers;
- debugging mais complexo;
- sobreposição possível com Terraform;
- necessidade de maturidade operacional maior.

Também seria necessário validar suporte adequado ao provedor de infraestrutura utilizado pelo projeto.

### Limitação de bootstrap

Assim como um Terraform Operator, Crossplane depende de Kubernetes previamente existente.

### Aderência ao APAE-INFRA

Baixa no estágio atual.

Seu valor aumenta se o projeto evoluir para uma plataforma interna com:

- múltiplos times;
- ambientes frequentes;
- self-service;
- APIs próprias de infraestrutura;
- necessidade real de reconciliação contínua.

---

## 4. Alternativa D — Arquitetura híbrida

A alternativa híbrida mantém responsabilidades diferentes por domínio.

```text
                         Git
                          │
              ┌───────────┴────────────┐
              │                        │
         terraform/               kubernetes/
              │                        │
       GitHub Actions                 ArgoCD
              │                        │
              ▼                        ▼
     infraestrutura externa        Kubernetes
                                       │
                                       ▼
                                   workloads
```

A infraestrutura fundacional continua em Terraform.

O cluster e os workloads permanecem no domínio do ArgoCD.

Em um cenário futuro, pode-se adicionar:

```text
ArgoCD
 ↓
Operator / Crossplane
 ↓
infraestrutura complementar
```

sem alterar a responsabilidade da camada de bootstrap.

---

## 5. Comparação

| Critério | Actions + Terraform | ArgoCD + Terraform Operator | ArgoCD + Crossplane |
| --- | --- | --- | --- |
| Git como fonte da verdade | Sim | Sim | Sim |
| Bootstrap independente do cluster | Sim | Não | Não |
| Aproveita pipeline atual | Alto | Baixo | Baixo |
| Mantém Terraform como IaC principal | Sim | Sim | Parcial/depende |
| Integração direta com ArgoCD | Desnecessária | Alta | Alta |
| Reconciliação contínua | Não por padrão | Sim | Sim |
| Componentes adicionais | Poucos | Vários | Vários |
| Complexidade | Baixa | Média/Alta | Alta |
| Curva de aprendizado | Baixa | Média | Alta |
| Aderência ao estágio atual | Alta | Média | Baixa |
| Potencial para Platform Engineering | Médio | Alto | Muito alto |

---

## 6. Síntese

As três opções conseguem preservar Git como fonte da verdade.

A principal diferença é **quem executa e reconcilia a infraestrutura**.

A alternativa A resolve o problema atual com menos componentes.

As alternativas B e C passam a fazer mais sentido quando existir necessidade concreta de:

- reconciliação contínua de recursos externos;
- infraestrutura orientada a aplicações;
- self-service;
- plataforma interna;
- múltiplas stacks e times;
- abstrações de infraestrutura via Kubernetes.

---

## 7. Referências

- HashiCorp — Running Terraform in Automation  
  <https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform>

- HCP Terraform Operator for Kubernetes  
  <https://developer.hashicorp.com/terraform/cloud-docs/integrations/kubernetes>

- Crossplane with ArgoCD  
  <https://docs.crossplane.io/latest/guides/crossplane-with-argo-cd/>

- ArgoCD — Declarative Setup  
  <https://argo-cd.readthedocs.io/en/latest/operator-manual/declarative-setup/>
