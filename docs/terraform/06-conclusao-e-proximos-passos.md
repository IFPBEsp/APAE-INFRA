# Conclusão e próximos passos

## 1. Conclusão do estudo

A issue #59 tinha como objetivo responder:

> **Como aplicar GitOps ao ciclo de vida da infraestrutura Terraform da APAE e qual deve ser o papel do ArgoCD nesse fluxo?**

O estudo conclui que GitOps não exige que Terraform seja executado pelo ArgoCD.

A arquitetura proposta é:

```text
Git
├── GitHub Actions → Terraform → infraestrutura fundacional
└── ArgoCD → Kubernetes → workloads
```

Git permanece como fonte da verdade em ambos os fluxos.

---

## 2. Decisão

### Terraform

Responsável pela infraestrutura fundacional.

### GitHub Actions

Responsável por automatizar o ciclo Terraform.

### ArgoCD

Responsável pela reconciliação Kubernetes.

### Terraform Operator

Não será adotado nesta etapa.

### Crossplane

Não será adotado nesta etapa.

### Drift

Será detectado antes de qualquer tentativa de correção automática da infraestrutura fundacional.

### Remote State

Será obrigatório antes da automação do `terraform apply`.

---

## 3. Por que essa decisão atende ao projeto

Ela preserva:

- GitOps;
- revisão por Pull Request;
- rastreabilidade;
- auditabilidade;
- Infrastructure as Code;
- separação de responsabilidades;
- simplicidade operacional;
- segurança;
- possibilidade de evolução futura.

E evita:

- dependência circular no bootstrap;
- novos controllers sem necessidade;
- credenciais de infraestrutura dentro do cluster sem justificativa;
- sobreposição de ownership;
- complexidade desnecessária no estágio atual.

---

## 4. Pontos deliberadamente não resolvidos

Este estudo não define:

- backend remoto definitivo;
- configuração do Object Storage;
- implementação do apply;
- mecanismo exato de bootstrap Kubernetes;
- módulos Terraform;
- política de testes;
- Policy as Code;
- gestão completa de secrets;
- backup/DR;
- runbooks;
- upgrades;
- implementação de drift detection.

Esses pontos dependem da arquitetura escolhida e devem ser tratados em issues próprias.

---

## 5. Resultado final

> **O APAE-INFRA adotará GitHub Actions + Terraform para a infraestrutura fundacional e ArgoCD para a reconciliação dos recursos Kubernetes. O Git continuará sendo a fonte da verdade dos dois domínios. Terraform Operator e Crossplane permanecem como possibilidades futuras caso novos requisitos justifiquem sua adoção.**
