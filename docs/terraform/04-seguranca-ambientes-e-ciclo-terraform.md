# Segurança, ambientes e ciclo Terraform

Este documento cobre apenas os aspectos de segurança e operação necessários para avaliar a arquitetura da issue #59.

Não define uma estratégia completa de segurança ou operação.

---

## 1. Princípio do menor privilégio

Terraform e ArgoCD devem usar identidades distintas.

```text
identidade Terraform
→ infraestrutura externa

identidade ArgoCD
→ Kubernetes
```

Isso limita o blast radius de cada componente.

ArgoCD não precisa possuir credenciais da Contabo apenas porque o projeto utiliza GitOps.

Terraform não precisa possuir privilégios permanentes sobre os workloads que ArgoCD administra.

---

## 2. Credenciais fora do Git

Nenhuma credencial deve ser versionada em:

```text
*.tf
*.tfvars
backend config
manifests
scripts
```

No desenho baseado em GitHub Actions, credenciais podem ser fornecidas através de mecanismos seguros do CI, como GitHub Secrets/Environments, até que uma estratégia de secret management mais ampla seja definida.

A escolha de Vault, External Secrets ou solução equivalente não faz parte da issue #59.

---

## 3. Terraform State como dado sensível

Terraform State pode conter valores derivados de recursos e configurações.

Por isso, o backend precisa possuir:

- acesso restrito;
- criptografia quando disponível;
- separação por ambiente;
- mecanismos de recuperação.

O state não deve ser publicado em artifacts ou commitado no Git.

---

## 4. Ciclo `plan` e `apply`

O fluxo recomendado em automação é:

```text
terraform init
      ↓
terraform plan
      ↓
review
      ↓
terraform apply
```

A pipeline atual já cobre parte desse ciclo no PR.

---

## 5. Plan especulativo

Um `terraform plan` realizado no PR é útil para revisão, mas pode ser especulativo.

Entre:

```text
PR plan
```

e:

```text
apply posterior
```

o estado real pode mudar.

Portanto, não se deve assumir que um plan antigo representa necessariamente a situação exata no momento do apply.

---

## 6. Saved plan

Terraform permite:

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

Isso é relevante para automação porque o `apply` executa as operações registradas naquele plan.

Porém, saved plans podem carregar dados sensíveis e exigem controle cuidadoso de:

- artifact;
- acesso;
- retenção;
- vínculo com commit;
- vínculo com ambiente.

A issue #59 registra o padrão como alternativa recomendada para estudo de implementação, mas não define ainda o pipeline final.

---

## 7. `-auto-approve`

`terraform apply -auto-approve` remove a confirmação interativa.

Isso não significa que produção precise ficar sem aprovação.

A aprovação deve acontecer no nível do workflow/plataforma:

```text
PR aprovado
 ↓
GitHub Environment
 ↓
reviewer autorizado
 ↓
job de apply
```

No estágio atual, o estudo recomenda aprovação humana para mudanças críticas e produção.

---

## 8. Mudanças destrutivas

Terraform pode propor:

```text
create
update
replace
destroy
```

Mudanças destrutivas aumentam o risco do `apply`.

Por isso, a arquitetura precisa preservar visibilidade sobre o plan antes de executar produção.

Uma política automatizada detalhada para bloquear `destroy` fica fora da issue #59.

---

## 9. Falhas parciais

Terraform não é uma transação global.

Um `apply` pode:

```text
criar recurso A
alterar recurso B
falhar ao criar recurso C
```

Nesse cenário, parte da infraestrutura já mudou.

O fluxo correto em nível conceitual é:

```text
falha
 ↓
preservar estado/logs
 ↓
novo terraform plan
 ↓
entender estado real
 ↓
corrigir configuração
 ↓
nova execução controlada
```

A existência desse comportamento reforça a necessidade de state remoto consistente e de não tratar Terraform como simples comando descartável.

---

## 10. Rollback

Rollback Terraform não é equivalente a rollback de aplicação.

```text
git revert
```

pode produzir uma nova configuração anterior, mas não garante recuperação de:

- dados;
- recursos destruídos;
- conteúdo de volumes;
- bancos;
- objetos externos.

Portanto:

```text
rollback de configuração
≠
recuperação de dados
```

A política completa de backup e disaster recovery fica fora do escopo.

---

## 11. Segurança comparada entre alternativas

### GitHub Actions + Terraform

Credenciais ficam no domínio da automação Terraform.

```text
GitHub Actions
 ↓
credencial Terraform
 ↓
Contabo
```

### Terraform Operator

Credenciais e permissões passam a existir também dentro do cluster ou no serviço conectado ao Operator.

### Crossplane

Providers precisam de credenciais para operar recursos externos a partir do cluster.

Isso aumenta o impacto potencial de comprometer o control plane.

A comparação não significa que Operators ou Crossplane sejam inseguros. Significa apenas que ampliam o domínio de credenciais e controles que precisam ser administrados.

---

## 12. Impacto na decisão

Para o estágio atual, a alternativa GitHub Actions + Terraform permite manter:

```text
credenciais de infraestrutura
```

fora do cluster e separadas das credenciais do ArgoCD.

Isso reforça a separação de responsabilidades proposta pelo estudo.

---

## 13. Referências

- HashiCorp — Running Terraform in Automation  
  <https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform>

- Terraform — `plan`  
  <https://developer.hashicorp.com/terraform/cli/commands/plan>

- Terraform — `apply`  
  <https://developer.hashicorp.com/terraform/cli/commands/apply>
