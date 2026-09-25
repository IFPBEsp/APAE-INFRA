# Decisão arquitetural

## 1. Resumo

Após avaliar:

- GitHub Actions + Terraform;
- ArgoCD + Terraform Operator;
- ArgoCD + Crossplane;
- arquitetura híbrida;

a recomendação para o estágio atual do `APAE-INFRA` é:

> **Utilizar GitHub Actions como mecanismo de automação do Terraform para infraestrutura fundacional e manter ArgoCD responsável pela reconciliação dos recursos Kubernetes.**

Terraform Operator e Crossplane permanecem como alternativas futuras, condicionadas ao surgimento de requisitos que justifiquem sua complexidade.

---

## 2. Arquitetura

```text
                         GitHub
                           │
                     APAE-INFRA
                           │
                 Pull Request / Review
                           │
               ┌───────────┴────────────┐
               │                        │
          terraform/               kubernetes/
               │                        │
       GitHub Actions                 ArgoCD
               │                        │
      fmt / validate / plan             │
               │                        │
            approval                    │
               │                        │
             apply                      │
               │                        │
               ▼                        ▼
        infraestrutura             Kubernetes
         fundacional                   │
               │                       ▼
               │                 Aplicações APAE
               ▼
          VPS / rede /
      firewall / bootstrap
```

---

## 3. Fonte da verdade

Git será a fonte da verdade para os dois domínios:

```text
Git
├── Terraform
└── Kubernetes
```

A diferença está no reconciliador/executor:

```text
Terraform
→ GitHub Actions

Kubernetes
→ ArgoCD
```

Isso mantém GitOps sem transformar ArgoCD em executor universal.

---

## 4. Responsabilidades

### Terraform

Responsável pela infraestrutura fundacional externa ao cluster.

Exemplos conceituais:

```text
VPS
rede
firewall externo
bootstrap do host
bootstrap Kubernetes
bootstrap mínimo do ArgoCD
```

O mecanismo exato de bootstrap não faz parte desta decisão.

### GitHub Actions

Responsável por automatizar:

```text
fmt
validate
plan
aprovações
apply
```

conforme workflows que serão definidos posteriormente.

### ArgoCD

Responsável pela reconciliação dos recursos Kubernetes depois que o cluster estiver disponível.

### Git

Responsável por armazenar o estado desejado versionado e servir de origem das mudanças revisadas.

---

## 5. Por que não executar Terraform diretamente pelo ArgoCD

A abordagem não foi escolhida porque:

1. ArgoCD é orientado à reconciliação de recursos Kubernetes;
2. infraestrutura fundacional existe antes do ArgoCD;
3. surgiria problema de bootstrap;
4. Terraform possui state e locking próprios;
5. GitHub Actions já cobre parte significativa do fluxo;
6. um executor Terraform dentro do cluster ampliaria RBAC, secrets e manutenção;
7. não existe requisito atual de reconciliação contínua que compense a complexidade adicional.

---

## 6. Por que não adotar Terraform Operator agora

Terraform Operator é uma alternativa tecnicamente válida.

Ele passa a ser mais interessante quando houver:

- muitas stacks Terraform;
- adoção estratégica de HCP Terraform;
- necessidade real de reconciliação contínua;
- necessidade de controlar runs Terraform via recursos Kubernetes;
- múltiplos times solicitando infraestrutura.

Essas necessidades não foram identificadas como requisito atual da APAE.

---

## 7. Por que não adotar Crossplane agora

Crossplane é mais aderente a um cenário de Platform Engineering.

Ele passa a agregar valor quando houver:

- self-service;
- múltiplos times;
- criação frequente de ambientes;
- APIs próprias de infraestrutura;
- compositions reutilizáveis;
- providers maduros para os provedores utilizados.

No estágio atual, esse modelo adicionaria complexidade antes que exista o problema que ele resolveria.

---

## 8. Remote State como pré-requisito

Não deve existir automação de `terraform apply` em CI sem uma estratégia adequada de state remoto.

A ordem proposta é:

```text
definir backend
 ↓
validar locking
 ↓
validar isolamento por ambiente
 ↓
somente então
 ↓
automatizar apply
```

Contabo Object Storage permanece candidato e deverá passar por PoC.

---

## 9. Drift

A arquitetura não utilizará inicialmente reconciliação automática contínua da infraestrutura fundacional.

A estratégia proposta é:

```text
plan periódico
 ↓
drift detectado
 ↓
alerta
 ↓
análise
 ↓
correção via Git
```

Isso preserva Git como fonte da verdade e reduz risco de self-healing destrutivo sobre a infraestrutura que mantém o próprio cluster.

---

## 10. Evolução futura

A arquitetura não bloqueia uma futura evolução:

```text
GitHub Actions + Terraform
→ infraestrutura fundacional

ArgoCD
→ Kubernetes

ArgoCD + Operator/Crossplane
→ infraestrutura complementar futura
```

A adição deve ocorrer somente quando sustentada por um requisito concreto.

---

## 11. Critérios que motivariam reavaliação

A decisão deve ser revisitada caso ocorram:

- múltiplos clusters;
- muitos ambientes dinâmicos;
- vários times consumindo infraestrutura;
- necessidade de self-service;
- forte crescimento do número de stacks;
- adoção de HCP Terraform;
- necessidade comprovada de reconciliação contínua;
- evolução para plataforma interna;
- providers Crossplane adequados ao ambiente utilizado.

---

## 12. Resultado

A arquitetura escolhida busca o equilíbrio entre:

```text
GitOps
+
segurança
+
simplicidade
+
auditabilidade
+
evolução futura
```

sem introduzir componentes adicionais antes de existir necessidade operacional.
