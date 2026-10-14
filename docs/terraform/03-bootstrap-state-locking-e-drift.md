# Bootstrap, Terraform State, locking e drift

Esses quatro pontos influenciam diretamente a escolha arquitetural e, por isso, fazem parte do escopo da issue #59.

---

## 1. Bootstrap

### Problema

A infraestrutura necessária para executar ArgoCD precisa existir antes do ArgoCD.

Fluxo:

```text
infraestrutura
 ↓
VPS
 ↓
Kubernetes
 ↓
ArgoCD
```

Se ArgoCD fosse responsável por executar o Terraform que cria essa mesma cadeia, surgiria uma dependência circular:

```text
ArgoCD
 ↓
Terraform
 ↓
Kubernetes
 ↓
ArgoCD
```

Isso torna inadequado colocar toda a infraestrutura fundacional sob responsabilidade do ArgoCD.

---

## 2. Infraestrutura fundacional

Para este estudo, infraestrutura fundacional é tudo aquilo necessário para que a plataforma Kubernetes exista.

Exemplos conceituais:

```text
VPS
rede
firewall externo
endereçamento
configuração inicial do host
Kubernetes
storage básico
bootstrap do ArgoCD
```

A responsabilidade recomendada para essa camada é Terraform.

O mecanismo exato de instalação do Kubernetes não é definido nesta issue.

---

## 3. Infraestrutura gerenciada pelo cluster

Depois que Kubernetes e ArgoCD existem, ArgoCD pode reconciliar recursos do cluster:

```text
Applications
Deployments
Services
Ingress
ConfigMaps
NetworkPolicies
Operators
Observabilidade
```

Essa separação evita que duas ferramentas tentem administrar o mesmo domínio.

---

## 4. Infraestrutura complementar

Alguns recursos podem ser classificados no futuro como infraestrutura complementar:

```text
DNS
buckets
databases externas
filas
recursos específicos das aplicações
```

A issue #59 não define quem gerenciará cada um deles.

Ela apenas registra que essa categoria pode ser reavaliada futuramente para Terraform Operator, Crossplane ou Terraform tradicional.

---

## 5. Terraform State

Terraform State representa a relação entre a configuração declarada e os recursos gerenciados.

Em automação, o state não deve depender do filesystem efêmero do runner.

Arquitetura necessária:

```text
GitHub Actions
      ↓
Terraform
      ↓
Remote Backend
      ↓
Terraform State
```

### Requisitos do backend

O backend escolhido posteriormente deve oferecer, no mínimo:

- persistência;
- controle de acesso;
- consistência;
- recuperação;
- isolamento por ambiente;
- suporte adequado a locking.

A HashiCorp recomenda remote state em automação e destaca o valor de locking para evitar race conditions.

---

## 6. State por ambiente

A estrutura conceitual é:

```text
dev  → state independente
hml  → state independente
prod → state independente
```

A implementação pode usar chaves, buckets ou backends separados.

A decisão exata pertence a uma issue posterior.

O requisito arquitetural é:

> **uma execução de um ambiente não pode alterar o state de outro ambiente.**

---

## 7. Contabo Object Storage como candidato

A Contabo oferece Object Storage compatível com S3 e o Terraform possui backend S3 com suporte a endpoint customizado.

O backend S3 do Terraform também permite locking por lockfile usando:

```hcl
use_lockfile = true
```

Entretanto, compatibilidade de API não deve ser tratada automaticamente como garantia de compatibilidade operacional completa.

Portanto, a decisão desta issue é apenas:

> **Contabo Object Storage é candidato a backend remoto e deverá ser validado em uma prova de conceito antes da adoção.**

A PoC e a configuração do backend ficam fora do escopo.

---

## 8. Locking

Duas operações simultâneas sobre o mesmo state podem causar race conditions.

O desenho precisa considerar duas camadas de controle:

```text
GitHub Actions concurrency
          +
Terraform backend locking
```

### GitHub Actions

`concurrency` reduz execuções paralelas indesejadas no workflow.

### Terraform

O backend deve impedir mutações simultâneas do mesmo state.

As duas proteções são complementares.

---

## 9. Drift

Drift ocorre quando o estado real diverge da configuração esperada.

Exemplo:

```text
Git
firewall = A

infraestrutura real
firewall = B
```

Isso pode acontecer após:

- alteração manual;
- mudança no painel do provedor;
- exclusão de recurso;
- mudança emergencial;
- alteração fora do workflow Terraform.

---

## 10. Pipeline versus reconciliação contínua

ArgoCD trabalha continuamente comparando desired state e live state.

Terraform executado em pipeline normalmente funciona assim:

```text
commit
 ↓
plan
 ↓
apply
 ↓
fim
```

Essa é a principal diferença operacional entre a alternativa GitHub Actions + Terraform e abordagens baseadas em controllers.

---

## 11. Estratégia de drift proposta

O reconciliation loop contínuo não é obrigatório para infraestrutura fundacional.

É possível adicionar detecção periódica:

```text
schedule
 ↓
terraform plan -detailed-exitcode
 ↓
0 → sem diferença
1 → erro
2 → diferença detectada
```

Ao detectar drift:

```text
drift
 ↓
alerta
 ↓
análise
 ↓
mudança via Git
 ↓
PR
 ↓
apply controlado
```

---

## 12. Detectar versus corrigir automaticamente

Para infraestrutura fundacional, o estudo recomenda separar:

```text
detecção automática
```

de:

```text
correção automática
```

Um Pod é um recurso normalmente descartável.

Uma VPS que hospeda o cluster pode não ser.

Portanto, para o estágio atual:

> **drift de infraestrutura fundacional deve ser detectado automaticamente e analisado antes da correção.**

A implementação do workflow de drift é assunto de issue posterior.

---

## 13. Impacto na decisão arquitetural

Os quatro pontos analisados favorecem uma separação clara:

```text
Terraform + GitHub Actions
→ infraestrutura fundacional

ArgoCD
→ recursos Kubernetes
```

porque:

- o bootstrap precisa existir fora do cluster;
- Terraform State possui ciclo de vida próprio;
- locking pertence ao domínio Terraform/backend;
- drift pode ser detectado sem introduzir Operator ou Crossplane.

---

## 14. Referências

- HashiCorp — Running Terraform in Automation  
  <https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform>

- HashiCorp — S3 Backend  
  <https://developer.hashicorp.com/terraform/language/backend/s3>

- Terraform Provider Contabo  
  <https://registry.terraform.io/providers/contabo/contabo/latest/docs>
