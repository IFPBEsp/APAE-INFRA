# Bootstrap, Terraform State, locking e drift

Este documento apresenta os aspectos arquiteturais relacionados ao bootstrap da infraestrutura, ao gerenciamento do Terraform State, ao controle de concorrência (locking) e à detecção de drift.

O estudo inicial foi realizado na issue [#59 — Estudar arquitetura GitOps para provisionamento com Terraform e ArgoCD](https://github.com/IFPBEsp/APAE-INFRA/issues/59).

Posteriormente, a issue [#87 — Configurar backend remoto do state do Terraform com lock](https://github.com/IFPBEsp/APAE-INFRA/issues/87) definiu e implementou o HCP Terraform Free como solução para armazenamento remoto do state.

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

O backend remoto do Terraform também precisa estar disponível independentemente da infraestrutura que será provisionada.

Por esse motivo, a solução de armazenamento do state deve permanecer fora da VPS HostGator e do cluster Kubernetes, evitando dependências circulares durante o processo de bootstrap.

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

A issue #59 não definiu quem gerenciará cada um deles.

Essa categoria poderá ser reavaliada futuramente para Terraform Operator, Crossplane ou Terraform tradicional.

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

O backend remoto deve oferecer, no mínimo:

- persistência;
- controle de acesso;
- consistência;
- recuperação;
- isolamento por ambiente;
- suporte adequado a locking.

A HashiCorp recomenda o uso de remote state em automações e destaca a importância do locking para evitar condições de corrida (*race conditions*).

### Decisão da issue #87

Foi escolhido o **HCP Terraform Free** como solução de gerenciamento remoto do Terraform State.

A escolha considera:

- armazenamento centralizado do state;
- locking nativo;
- histórico de versões do state;
- gerenciamento de workspaces;
- integração com Terraform CLI;
- integração com GitHub Actions;
- menor complexidade operacional.

O HCP Terraform permanece independente da VPS HostGator e do cluster Kubernetes.

As execuções do Terraform continuam sendo realizadas localmente ou pelo GitHub Actions, utilizando o HCP Terraform para gerenciamento remoto do state.

---

## 6. State por ambiente

A estrutura conceitual é:

```text
dev  → state independente
hml  → state independente
prod → state independente
```

O requisito arquitetural é:

> **Uma execução de um ambiente não pode alterar o state de outro ambiente.**

### Separação por workspaces

A issue #87 definiu a utilização de workspaces independentes no HCP Terraform.

| Ambiente | Workspace | Situação |
| --- | --- | --- |
| `dev` | `apae-infra-dev` | Configurado e validado |
| `hml` | `apae-infra-hml` | Planejado |
| `prod` | `apae-infra-prod` | Planejado |

Cada ambiente deverá possuir seu próprio diretório Terraform e um workspace remoto independente.

Estrutura prevista:

```text
terraform/
├── environments/
│   ├── dev/
│   │   └── backend.tf
│   ├── hml/
│   │   └── backend.tf
│   └── prod/
│       └── backend.tf
└── modules/
```

Inicialmente, apenas o ambiente `dev` foi configurado.

Os ambientes `hml` e `prod` deverão ser implementados conforme a evolução da infraestrutura.

---

## 7. Avaliação das alternativas de backend remoto

Durante o estudo arquitetural da issue #59, a Contabo Object Storage foi identificada como uma possível solução para armazenamento remoto do Terraform State.

A Contabo oferece Object Storage compatível com S3, e o Terraform possui backend S3 com suporte a endpoints customizados.

O backend S3 também permite locking por lockfile por meio da configuração:

```hcl
use_lockfile = true
```

Entretanto, a compatibilidade de API S3 não garante automaticamente a compatibilidade operacional completa com todos os mecanismos de locking do Terraform.

Por esse motivo, a adoção de serviços S3 compatíveis exige validação específica.

### 7.1. Alternativas consideradas na issue #87

| Alternativa | Vantagens | Considerações |
| --- | --- | --- |
| HCP Terraform Free | Locking nativo, histórico de state e integração direta com Terraform CLI | Dependência da plataforma HCP e limites do plano gratuito |
| AWS S3 | Locking via lockfile e versionamento de objetos | Exige configuração adicional de bucket e permissões |
| Cloudflare R2 | Armazenamento compatível com S3 e possibilidade de baixo custo | Exige validação operacional do locking |
| Backblaze B2 | Armazenamento compatível com S3 e suporte a versionamento | Compatibilidade com locking não comprovada |
| Contabo Object Storage | Alternativa S3 compatível | Necessidade de prova de conceito para locking |

### 7.2. Decisão

O HCP Terraform Free foi escolhido por disponibilizar gerenciamento nativo do state e locking, reduzindo a necessidade de configurar mecanismos adicionais de controle de concorrência.

A solução também apresenta integração direta com o Terraform CLI e GitHub Actions, simplificando sua adoção no estágio atual do projeto.

As alternativas de armazenamento compatível com S3 permanecem como possibilidades para reavaliação futura.

---

## 8. Locking

Duas operações simultâneas sobre o mesmo state podem causar condições de corrida e inconsistências.

O desenho considera duas camadas de controle:

```text
GitHub Actions concurrency
          +
Terraform backend locking
```

### GitHub Actions

`concurrency` reduz execuções paralelas indesejadas no workflow.

### Terraform

O backend remoto deve impedir operações concorrentes incompatíveis sobre o mesmo state.

As duas proteções são complementares.

### Locking no HCP Terraform

O HCP Terraform oferece mecanismos nativos de locking para proteger o state.

Durante a issue #87, foi realizada uma validação funcional do bloqueio administrativo do workspace `apae-infra-dev`.

O workspace foi bloqueado manualmente, impedindo uma execução de `terraform plan`.

Após o desbloqueio, o mesmo comando foi executado com sucesso.

Os resultados detalhados estão registrados na seção 14.

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

ArgoCD trabalha continuamente comparando *desired state* e *live state*.

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

> **Drift de infraestrutura fundacional deve ser detectado automaticamente e analisado antes da correção.**

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

Porque:

- o bootstrap precisa existir fora do cluster;
- Terraform State possui ciclo de vida próprio;
- locking pertence ao domínio Terraform/backend;
- drift pode ser detectado sem introduzir Operator ou Crossplane.

A adoção do HCP Terraform reforça essa separação, mantendo o armazenamento do state fora da infraestrutura provisionada.

---

## 14. Implementação do backend remoto — Issue #87

### 14.1. Objetivo

A issue [#87 — Configurar backend remoto do state do Terraform com lock](https://github.com/IFPBEsp/APAE-INFRA/issues/87) tem como objetivo implementar o requisito arquitetural estabelecido na issue #59: utilizar um backend remoto com locking antes da automação do `terraform apply`.

A implementação inicial utiliza o HCP Terraform Free para gerenciamento remoto do state do ambiente `dev`.

### 14.2. Arquitetura implementada

```text
GitHub
  │
  ▼
GitHub Actions
  │
  ▼
Terraform CLI
  │
  ▼
HCP Terraform
  │
  ├── apae-infra-dev
  ├── apae-infra-hml (planejado)
  └── apae-infra-prod (planejado)
```

O Terraform CLI é responsável pelas operações de infraestrutura.

O HCP Terraform gerencia o armazenamento remoto do state e o locking.

O ArgoCD permanece responsável pela reconciliação dos recursos Kubernetes, sem executar Terraform diretamente.

### 14.3. Organização e workspace

Foi criada a seguinte organização no HCP Terraform:

```text
ifpb-esp-apae
```

Workspace configurado:

```text
apae-infra-dev
```

Configurações utilizadas:

- Workflow: CLI-Driven;
- Execution Mode: Local;
- State remoto gerenciado pelo HCP Terraform;
- Locking nativo do HCP Terraform;
- Histórico de versões do state fornecido pela plataforma.

O modo de execução local permite executar Terraform no ambiente de desenvolvimento ou no GitHub Actions, mantendo o state centralizado no HCP Terraform.

### 14.4. Configuração do Terraform

Arquivo:

```text
terraform/environments/dev/backend.tf
```

Conteúdo:

```hcl
terraform {
  required_version = "~> 1.13.0"

  cloud {
    organization = "ifpb-esp-apae"

    workspaces {
      name = "apae-infra-dev"
    }
  }
}
```

A configuração utiliza o bloco `cloud`, responsável por conectar o Terraform CLI ao HCP Terraform.

A versão utilizada nos testes foi o Terraform `1.13.5`, alinhada à versão configurada no GitHub Actions.

O HCP Terraform fornece locking nativo, não sendo necessário configurar `use_lockfile` ou outros mecanismos de bloqueio no arquivo.

### 14.5. Autenticação local

A autenticação local é realizada pelo Terraform CLI.

Comando:

```bash
terraform login
```

O comando inicia o procedimento de autenticação no HCP Terraform.

O token gerado deve permanecer armazenado localmente, sem ser incluído no repositório.

Cada integrante autorizado deverá utilizar credenciais próprias ou credenciais aprovadas pela equipe.

### 14.6. Inicialização do backend remoto

A inicialização é executada a partir da raiz do repositório:

```bash
terraform -chdir=terraform/environments/dev init
```

Resultado obtido:

```text
Initializing HCP Terraform...
Initializing provider plugins...

HCP Terraform has been successfully initialized!
```

Esse resultado confirmou a conexão entre o Terraform CLI e o HCP Terraform.

O comando `terraform init` deve ser executado ao configurar um novo ambiente ou após alterações relevantes nas configurações de backend.

Para a configuração `cloud`, o procedimento normal não utiliza a opção `-reconfigure`.

### 14.7. Autenticação no GitHub Actions

Para permitir a autenticação no HCP Terraform durante as execuções do CI, foi configurado o seguinte secret exclusivamente no ambiente `terraform-plan` do GitHub Actions:

```text
TF_TOKEN_app_terraform_io
```

O Terraform CLI reconhece essa variável de ambiente para autenticação em `app.terraform.io`.

O workflow disponibiliza o token somente nas etapas `Terraform Init for plan` e `Terraform Plan`. Exemplo de utilização no escopo de uma etapa:

```yaml
- name: Terraform Init for plan
  env:
    TF_TOKEN_app_terraform_io: ${{ secrets.TF_TOKEN_app_terraform_io }}
  run: terraform init -input=false
```

As credenciais devem permanecer fora do repositório. O secret não deve ser duplicado no nível do repositório nem disponibilizado por um secret da organização acessível a este repositório.

#### Aprovação obrigatória antes da execução autenticada

O ambiente `terraform-plan` foi configurado em **Settings → Environments** com as seguintes regras:

- **Required reviewers**: aprovação de um mantenedor antes de iniciar o job;
- **Prevent self-review**: quem iniciou a execução não pode aprová-la;
- **Allow administrators to bypass configured protection rules**: desativado.

Essas regras são configurações do GitHub e não são criadas pela declaração `environment: terraform-plan` no YAML. Armazenar um secret em um ambiente sem regras não exige aprovação para disponibilizá-lo.

Antes de aprovar cada execução, o responsável deve revisar o código correspondente do PR, incluindo alterações no workflow, módulos, providers e fontes de dados. O `terraform plan` pode executar código do PR, por exemplo por meio de `data "external"`, e esse código pode acessar o token e o state. Limitar a variável às etapas autenticadas reduz sua exposição, mas não isola o token do código executado pelo plan.

PRs de forks não executam o job autenticado. Para PRs de branches do próprio repositório, a revisão obrigatória do ambiente controla a liberação da credencial. A aprovação de uma execução anterior não dispensa a revisão e a aprovação de uma nova execução.

A validação operacional dessa proteção deve confirmar que uma nova execução fica aguardando em **Review deployments**, antes do job autenticado, e só prossegue após a aprovação de outro mantenedor. Esse teste deve ser realizado após configurar ou alterar as regras do ambiente.

Referência: [GitHub — Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).

Para utilização permanente no CI, recomenda-se:

- utilizar tokens de equipe com permissões mínimas;
- limitar o acesso aos workspaces necessários;
- manter as regras de aprovação do ambiente `terraform-plan`;
- evitar disponibilizar credenciais a código não revisado;
- realizar a rotação das credenciais quando necessário.

### 14.8. Validação no GitHub Actions

Durante os testes da issue #87, foi utilizado um workflow temporário, já removido:

```text
.github/workflows/terraform-backend-check.yml
```

O workflow temporário executava:

```bash
terraform init -input=false
terraform validate -no-color
```

A execução foi concluída com sucesso no GitHub Actions, confirmando que o runner consegue autenticar-se no HCP Terraform e inicializar o backend remoto.

Também foram realizados testes de integração com o workflow existente:

```text
.github/workflows/terraform-validate.yml
```

Após os ajustes necessários, a pipeline de validação passou com sucesso, incluindo a execução do `terraform plan`.

Evidência:

[Pull Request #101 — Configurar backend remoto do state do Terraform com lock](https://github.com/IFPBEsp/APAE-INFRA/pull/101)

Após a conclusão dos testes, o workflow temporário foi removido, mantendo apenas a pipeline principal `.github/workflows/terraform-validate.yml` para validação do Terraform.

### 14.9. Validação do locking

Foi realizado um teste funcional de bloqueio e desbloqueio do workspace `apae-infra-dev`.

#### Teste 1 — Workspace bloqueado

O workspace foi bloqueado manualmente no HCP Terraform.

Em seguida, foi executado:

```bash
terraform -chdir=terraform/environments/dev plan -lock-timeout=10s
```

Resultado:

```text
Acquiring state lock. This may take a few moments...

Error: Error acquiring the state lock

Error message: workspace already locked
(lock ID: "ifpb-esp-apae/apae-infra-dev")
```

O Terraform não conseguiu adquirir o lock enquanto o workspace estava bloqueado.

Isso demonstrou que a operação respeita o mecanismo de bloqueio do HCP Terraform.

#### Teste 2 — Workspace desbloqueado

Após liberar o workspace no HCP Terraform, foi executado:

```bash
terraform -chdir=terraform/environments/dev plan
```

Resultado:

```text
No changes. Your infrastructure matches the configuration.

Terraform has compared your real infrastructure against your
configuration and found no differences, so no changes are needed.
```

O Terraform conseguiu executar o `plan` normalmente após o desbloqueio.

#### Conclusão

Os testes confirmaram o funcionamento do bloqueio administrativo e do desbloqueio do workspace no HCP Terraform.

Não foi realizado um teste específico com duas operações concorrentes tentando adquirir simultaneamente o mesmo lock.

Nenhum `terraform apply` ou `terraform destroy` foi necessário para a validação.

### 14.10. Histórico, backup e recuperação do state

O HCP Terraform oferece histórico de versões do Terraform State, permitindo consultar versões anteriores e apoiar procedimentos de recuperação.

O histórico de versões mantido pela plataforma constitui o mecanismo inicial de recuperação adotado pelo projeto.

Recomendações:

1. Restringir o acesso aos workspaces aos integrantes autorizados.
2. Manter states independentes para `dev`, `hml` e `prod`.
3. Consultar o histórico antes de qualquer procedimento de recuperação.
4. Não armazenar arquivos de state no Git.
5. Tratar versões exportadas do state como informações sensíveis.
6. Realizar restaurações somente após análise do impacto sobre a infraestrutura existente.
7. Documentar operações de recuperação realizadas.

Nesta etapa, não foi implementado backup independente fora do HCP Terraform.

A necessidade de backups externos poderá ser reavaliada conforme os requisitos de continuidade e recuperação da infraestrutura.

### 14.11. Proteção de arquivos locais

O `.gitignore` foi atualizado para impedir o versionamento acidental de arquivos locais e potencialmente sensíveis do Terraform.

Configurações adicionadas:

```gitignore
# Terraform
**/.terraform/
*.tfstate
*.tfstate.*
*.tfplan
*.tfvars
*.tfvars.json
*.tfbackend
crash.log
crash.*.log
```

O arquivo `backend.tf` deve ser versionado normalmente, desde que não contenha credenciais.

Arquivos de configuração com informações sensíveis não deverão ser incluídos no repositório.

### 14.12. Próximos passos

A implementação inicial contempla o ambiente `dev`.

Como evolução futura, estão previstos:

- configuração dos workspaces `hml` e `prod`;
- utilização de credenciais de equipe com privilégios mínimos;
- validação adicional de locking com operações concorrentes;
- testes periódicos de recuperação do state;
- avaliação de backup independente do HCP Terraform;
- automação controlada de `terraform apply`;
- detecção periódica de drift.

A configuração do backend remoto não autoriza automaticamente a execução de `terraform apply` em produção.

---

## 15. Referências

- [HashiCorp — Running Terraform in Automation](https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform)
- [HashiCorp — HCP Terraform](https://developer.hashicorp.com/terraform/cloud-docs)
- [HashiCorp — Terraform Settings](https://developer.hashicorp.com/terraform/language/terraform)
- [HashiCorp — State Locking](https://developer.hashicorp.com/terraform/language/state/locking)
- [HashiCorp — S3 Backend](https://developer.hashicorp.com/terraform/language/backend/s3)
- [Terraform Provider Contabo](https://registry.terraform.io/providers/contabo/contabo/latest/docs)
- [Issue #59 — Estudar arquitetura GitOps](https://github.com/IFPBEsp/APAE-INFRA/issues/59)
- [Issue #87 — Backend remoto do Terraform](https://github.com/IFPBEsp/APAE-INFRA/issues/87)
- [PR #101 — Implementação do backend remoto](https://github.com/IFPBEsp/APAE-INFRA/pull/101)
