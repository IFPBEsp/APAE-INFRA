# Segurança, ambientes e ciclo Terraform

> Análise conceitual da issue #59. Para a VPS HostGator, consultar a [delimitação proposta na issue #86](06-conclusao-e-proximos-passos.md): Terraform para recursos externos suportados, Ansible para host/k3s/bootstrap e ArgoCD para recursos Kubernetes atribuídos às Applications. Menções a outros provedores são exemplos do estudo original.

Este documento cobre apenas os aspectos de segurança e operação necessários para avaliar a arquitetura da issue #59.

Não define uma estratégia completa de segurança ou operação.

As seções 13 a 15 descrevem os pipelines implementados na issue #89: apply com aprovação manual, detecção de drift e o procedimento de rollback.

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

A issue #59 registra o padrão como alternativa recomendada para estudo de implementação, mas não definia o pipeline final. O pipeline implementado está descrito na seção 13.

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

No estágio atual, o estudo recomenda aprovação humana para mudanças críticas e produção. Na implementação (issue #89), a aprovação é exigida pelo environment `production` do GitHub, conforme a seção 13.

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

Em uma infraestrutura baseada em uma única VPS, um destroy acidental pode afetar simultaneamente múltiplos sistemas hospedados no ambiente.

Por isso, a arquitetura deve possuir uma proteção mínima contra destruição de recursos críticos.

### prevent_destroy

O Terraform possui o mecanismo nativo prevent_destroy através do bloco lifecycle:

```text
resource "..." "..." {
  # ...

  lifecycle {
    prevent_destroy = true
  }
}
```

Essa proteção deve ser considerada para recursos críticos da infraestrutura fundacional, especialmente aqueles cuja destruição possa comprometer todo o ambiente.

O objetivo é impedir que um terraform plan ou terraform apply prossiga com a destruição acidental desses recursos enquanto a proteção estiver configurada.

Além disso, o fluxo deve preservar a visibilidade do terraform plan antes de executar mudanças em produção.

Uma política automatizada mais ampla para classificação, aprovação e bloqueio de todos os tipos de destroy fica fora da issue #59 e deverá ser tratada posteriormente.

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

## 13. Pipeline de apply com aprovação manual

A implementação do ciclo `plan` → `apply` está em `.github/workflows/terraform-apply.yml` (issue #89).

```text
push em main (terraform/**) ou workflow_dispatch
  ↓
environment: production — aprovação manual
  ↓
checkout → setup terraform → init → plan (saved plan) → apply
```

Pontos do fluxo:

- o `terraform init` conecta ao backend remoto HCP Terraform configurado na issue #87, que também fornece o lock do state;
- o `terraform plan` grava o plano em arquivo com `-out` e o `terraform apply` consome exatamente esse arquivo, sem recalcular o plan entre as etapas;
- a diretiva `concurrency` com `cancel-in-progress: false` garante apenas um apply por vez no ambiente, evitando corrida sobre o lock do state;
- a aprovação humana acontece no GitHub Environment `production` (Settings > Environments), antes da execução do job de apply.

---

## 14. Detecção de drift

A rotina de drift está em `.github/workflows/terraform-drift.yml` (issue #89):

```text
schedule (diário) ou workflow_dispatch
  ↓
terraform plan -detailed-exitcode
  ↓
0 → sem divergência
1 → erro no plan → o job reprova (exit 1)
2 → divergência detectada → o job emite ::warning:: e segue verde
```

Com código 2 o job não falha: ele publica um `::warning::` no Actions sinalizando a divergência (possível desvio entre dev e main, a validar conforme a issue #89). Só um erro real de `terraform plan` (código diferente de 0 e 2) reprova o job. A correção segue a estratégia da [seção 11 do documento 03](03-bootstrap-state-locking-e-drift.md):

```text
drift detectado
  ↓
análise
  ↓
mudança via Git (PR)
  ↓
apply controlado
```

Drift detecta divergências; não as corrige automaticamente. Correção automática fica fora do escopo atual.

---

## 15. Procedimento de rollback

Rollback de configuração é feito no Git, não por comando do Terraform:

```bash
git revert <commit-errado>
git push origin <branch>
```

Em seguida, abrir e mesclar o PR para a branch principal. O push em `main` com mudanças em `terraform/**` re-dispara o pipeline de apply, que exige aprovação manual no environment `production` antes de executar.

```text
git revert
  ↓
PR → merge em main
  ↓
pipeline de apply
  ↓
aprovação manual (production)
  ↓
apply reconcilia a infraestrutura
```

Como descrito na [seção 10](#10-rollback), `git revert` recupera a configuração anterior, mas não recupera dados nem recursos destruídos. Rollback de dados é responsabilidade da política de backup (issues #107 e #108).

---

## 16. Referências

- HashiCorp — Running Terraform in Automation  
  <https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform>

- Terraform — `plan`  
  <https://developer.hashicorp.com/terraform/cli/commands/plan>

- Terraform — `apply`  
  <https://developer.hashicorp.com/terraform/cli/commands/apply>
