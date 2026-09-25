# Contexto e princípios

## 1. Contexto

O `APAE-INFRA` centraliza infraestrutura como código, pipelines de CI/CD, Kubernetes, ArgoCD, observabilidade e demais elementos de infraestrutura utilizados pelos sistemas da APAE.

O repositório já segue uma direção GitOps para Kubernetes:

```text
Git
 ↓
ArgoCD
 ↓
Kubernetes
```

Ao mesmo tempo, Terraform foi escolhido como ferramenta de Infrastructure as Code para a infraestrutura externa ao cluster.

A estrutura prevista no repositório é:

```text
terraform/
├── modules/
└── environments/
```

e já existe uma pipeline de validação Terraform para Pull Requests.

Essa pipeline executa, de forma resumida:

```text
terraform fmt
      ↓
terraform init
      ↓
terraform validate
      ↓
terraform plan
      ↓
resultado publicado no PR
```

Portanto, o estudo não parte de uma folha em branco. A questão é como evoluir essa base mantendo coerência com GitOps.

---

## 2. Pergunta arquitetural

A pergunta deste estudo é:

> **Como aplicar GitOps ao ciclo de vida da infraestrutura Terraform da APAE e qual deve ser o papel do ArgoCD nesse fluxo?**

A formulação evita assumir antecipadamente que:

```text
GitOps = ArgoCD
```

ou que:

```text
Terraform via GitOps = Terraform executado pelo ArgoCD
```

Essas equivalências não são necessárias.

---

## 3. GitOps como modelo operacional

Para este estudo, GitOps é entendido como um modelo em que:

```text
Git
 ↓
estado desejado versionado
 ↓
Pull Request
 ↓
review
 ↓
automação/reconciliação
 ↓
estado real
```

As propriedades desejadas são:

- Git como fonte da verdade;
- mudanças rastreáveis;
- revisão antes de alterações relevantes;
- automação;
- reprodutibilidade;
- auditoria;
- redução de mudanças manuais;
- possibilidade de detectar divergência entre estado desejado e estado real.

O mecanismo responsável por levar o estado real ao estado desejado pode variar conforme o domínio.

---

## 4. Papel do ArgoCD

ArgoCD é um reconciliador GitOps voltado para Kubernetes.

Seu modelo central é:

```text
Git
 ↓
manifestos/Helm/Kustomize
 ↓
ArgoCD
 ↓
Kubernetes API
```

O ArgoCD trabalha com o conceito de estado desejado e estado vivo do cluster:

```text
desired state
      ↓
comparação
      ↓
live state
      ↓
Synced / OutOfSync
```

Isso o torna adequado para:

- `Application`;
- `Deployment`;
- `Service`;
- `Ingress`;
- `ConfigMap`;
- `NetworkPolicy`;
- Operators;
- observabilidade;
- demais recursos Kubernetes.

O fato de o projeto utilizar GitOps não implica que ArgoCD precise se tornar executor genérico de qualquer ferramenta.

---

## 5. Papel do Terraform

Terraform é responsável por representar e alterar infraestrutura externa através de configuração declarativa e providers.

Seu ciclo típico é:

```text
configuração
 ↓
terraform plan
 ↓
avaliação das mudanças
 ↓
terraform apply
 ↓
infraestrutura
```

Diferentemente do ArgoCD, uma execução comum do Terraform via pipeline não mantém necessariamente um loop contínuo de reconciliação.

Isso não impede seu uso dentro de um modelo GitOps.

---

## 6. Papel do GitHub Actions

GitHub Actions pode funcionar como mecanismo de automação para:

```text
Git
 ↓
Pull Request
 ↓
Terraform CLI
 ↓
infraestrutura
```

Nesse desenho:

- Git contém o estado desejado;
- Terraform interpreta esse estado;
- GitHub Actions executa o workflow;
- o review humano controla a promoção de mudanças relevantes.

O GitHub Actions não se torna a fonte da verdade. Ele é apenas o executor.

---

## 7. Separação entre modelo e ferramenta

A separação conceitual adotada neste estudo é:

```text
GitOps
= modelo operacional

Terraform
= IaC para infraestrutura

GitHub Actions
= executor de automação

ArgoCD
= reconciliador Kubernetes
```

Isso permite aplicar GitOps de forma coerente sem forçar todas as mudanças através de um único componente.

---

## 8. Objetivos da arquitetura

A arquitetura escolhida deve:

1. manter Git como fonte da verdade;
2. preservar review por Pull Request;
3. permitir `terraform plan` antes do `apply`;
4. não depender do cluster para criar o próprio cluster;
5. proteger o Terraform State;
6. evitar concorrência perigosa;
7. permitir detecção de drift;
8. separar credenciais e privilégios;
9. suportar `dev`, `hml` e `prod`;
10. manter baixa complexidade operacional;
11. permitir evolução futura sem reescrever toda a solução.

---

## 9. Critério de simplicidade

Adicionar um novo componente só se justifica quando ele resolve um problema concreto.

Portanto, a análise considera não apenas capacidade técnica, mas também:

- número de componentes;
- pontos de falha;
- manutenção;
- RBAC;
- secrets;
- curva de aprendizado;
- observabilidade;
- debugging;
- dependências externas.

A arquitetura mais sofisticada não é automaticamente a mais adequada ao estágio atual do projeto.

---

## 10. Referências

- ArgoCD — Declarative Setup  
  <https://argo-cd.readthedocs.io/en/latest/operator-manual/declarative-setup/>

- HashiCorp — Running Terraform in Automation  
  <https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform>

- Terraform Provider Contabo  
  <https://registry.terraform.io/providers/contabo/contabo/latest/docs>
