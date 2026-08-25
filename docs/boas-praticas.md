# Boas Práticas do Repositório APAE-INFRA

Este documento define as boas práticas técnicas e operacionais adotadas no repositório **APAE-INFRA**.

O objetivo é manter a infraestrutura padronizada, segura, rastreável e reproduzível, reduzindo diferenças de implementação entre os contribuidores e evitando alterações manuais que possam gerar inconsistências entre o repositório e os ambientes provisionados.

As recomendações deste documento devem ser consideradas durante o desenvolvimento, revisão de Pull Requests e manutenção dos ambientes.

---

# 1. Princípios gerais

As alterações realizadas no repositório **APAE-INFRA** devem seguir alguns princípios fundamentais.

## 1.1 Infraestrutura como código

A infraestrutura deve ser definida, sempre que possível, através de código versionado no Git.

Alterações persistentes não devem depender de procedimentos manuais executados diretamente nos ambientes.

O objetivo é permitir que a infraestrutura seja:

* Reproduzível;
* Versionada;
* Auditável;
* Revisável;
* Automatizável.

---

## 1.2 Configuração declarativa

As ferramentas utilizadas devem descrever o **estado desejado** da infraestrutura sempre que possível.

Em vez de registrar apenas os comandos necessários para modificar um ambiente, o repositório deve representar como o ambiente deve estar configurado.

Exemplo conceitual:

```text
Estado desejado
        ↓
Git
        ↓
Automação
        ↓
Infraestrutura
```

---

## 1.3 Mudanças versionadas e revisáveis

Alterações de infraestrutura devem passar pelo Git e pelo fluxo de Pull Requests definido pelo projeto.

Evitar alterações persistentes realizadas diretamente nos ambientes sem que exista uma alteração correspondente no repositório.

---

## 1.4 Automação em vez de procedimentos manuais

Sempre que uma tarefa for recorrente, previsível e segura de automatizar, deve-se preferir sua execução por pipeline ou ferramenta de automação.

Procedimentos manuais aumentam o risco de:

* Erros humanos;
* Configurações inconsistentes;
* Falta de rastreabilidade;
* Diferenças entre ambientes.

---

## 1.5 Princípio do menor privilégio

Usuários, pipelines, aplicações e ferramentas devem receber somente as permissões necessárias para executar suas responsabilidades.

Evitar permissões administrativas quando permissões mais restritas forem suficientes.

---

## 1.6 Ambientes reproduzíveis

Os ambientes de `dev`, `hml` e `prod` devem seguir padrões equivalentes sempre que possível.

Diferenças entre ambientes devem ser declaradas explicitamente nas configurações correspondentes.

---

## 1.7 Git como fonte da verdade

Para recursos gerenciados por GitOps, o Git deve ser considerado a fonte da verdade do ambiente.

Alterações realizadas fora do Git podem causar divergência entre o estado desejado e o estado real da infraestrutura.

---

# 2. Gestão de segredos e credenciais

Segredos e credenciais nunca devem ser armazenados diretamente no repositório.

Isso inclui:

* Tokens de acesso;
* Senhas;
* Chaves de API;
* Chaves privadas;
* Credenciais de provedores de cloud;
* Credenciais de banco de dados;
* Arquivos contendo informações sensíveis;
* Tokens de acesso ao Kubernetes ou ArgoCD.

## 2.1 Armazenamento

Quando uma credencial for necessária em uma pipeline, deve ser utilizado o mecanismo de **Secrets do GitHub Actions** ou uma solução de gerenciamento de segredos aprovada pelo time.

Exemplo de utilização em GitHub Actions:

```yaml
env:
  TOKEN: ${{ secrets.EXAMPLE_TOKEN }}
```

Nunca utilizar:

```yaml
env:
  TOKEN: "token-real-da-aplicacao"
```

Também não devem ser commitados arquivos contendo valores sensíveis, como:

```text
.env
*.pem
*.key
credentials.json
terraform.tfstate
terraform.tfstate.*
```

Arquivos locais desse tipo devem ser adicionados ao `.gitignore` quando aplicável.

---

## 2.2 ConfigMap não é Secret

No Kubernetes, `ConfigMap` deve ser utilizado apenas para configurações não sensíveis.

Exemplo:

```text
ConfigMap
→ configuração não sensível

Secret
→ informação sensível
```

Tokens, senhas, chaves de API e outras credenciais não devem ser armazenados em `ConfigMaps`.

Da mesma forma, o fato de uma informação estar em um recurso Kubernetes do tipo `Secret` não significa que seja seguro armazenar seu valor diretamente no Git.

---

## 2.3 Segredo commitado por engano

Caso uma credencial seja commitada acidentalmente:

1. Revogar ou rotacionar imediatamente a credencial comprometida;
2. Gerar uma nova credencial;
3. Remover o segredo do repositório;
4. Verificar se o segredo também permanece no histórico do Git;
5. Avaliar a necessidade de remoção do conteúdo sensível do histórico;
6. Comunicar o ocorrido ao time responsável.

Apenas remover o segredo em um commit posterior **não é suficiente**, pois ele continua acessível no histórico do Git.

---

# 3. Terraform

O Terraform deve ser utilizado de forma declarativa e reproduzível.

A estrutura definida no repositório deve ser respeitada:

```text
terraform/
├── modules/
└── environments/
    ├── dev/
    ├── hml/
    └── prod/
```

Os módulos reutilizáveis devem permanecer em `terraform/modules/`, enquanto as configurações específicas de cada ambiente devem permanecer em `terraform/environments/`.

---

## 3.1 Nomenclatura

Os recursos devem utilizar nomes previsíveis e consistentes.

Sempre que aplicável, utilizar informações como:

```text
<projeto>-<ambiente>-<recurso>
```

Exemplo:

```text
apae-prod-network
apae-dev-storage
apae-hml-database
```

Evitar nomes genéricos como:

```text
server1
test
resource-new
```

---

## 3.2 Variables e Outputs

Valores que podem variar entre ambientes não devem ser fixados diretamente nos recursos.

Preferir:

```hcl
variable "environment" {
  type = string
}
```

em vez de valores duplicados em diversos arquivos.

Outputs devem ser utilizados para expor somente informações que serão consumidas por outros módulos, processos ou recursos.

Informações sensíveis não devem ser expostas desnecessariamente por outputs.

---

## 3.3 Providers e dependências

As versões dos providers utilizados pelo Terraform devem possuir restrições explícitas.

Exemplo:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

Isso evita que uma atualização inesperada de provider altere o comportamento da infraestrutura ou quebre pipelines existentes.

Quando gerado, o arquivo:

```text
.terraform.lock.hcl
```

deve ser mantido versionado no repositório.

Esse arquivo registra as versões efetivamente selecionadas dos providers e contribui para builds mais reproduzíveis.

---

## 3.4 State

O state do Terraform contém informações importantes sobre a infraestrutura e não deve ser versionado diretamente no Git.

Para ambientes compartilhados, deve ser utilizado um backend remoto adequado, permitindo centralização e controle do state.

Arquivos como:

```text
terraform.tfstate
terraform.tfstate.*
```

não devem ser commitados.

O state também não deve ser editado manualmente.

---

## 3.5 Locking do state

Quando o backend utilizado oferecer suporte, deve ser utilizado mecanismo de **locking** ou proteção equivalente contra alterações concorrentes.

O objetivo é impedir que duas execuções do Terraform tentem modificar o mesmo state simultaneamente.

Exemplo de situação que deve ser evitada:

```text
terraform apply A
        +
terraform apply B
        ↓
mesmo state
```

Alterações concorrentes podem causar inconsistências ou corrupção do estado da infraestrutura.

---

## 3.6 Validação

Antes de abrir ou aprovar um Pull Request contendo Terraform, executar:

```bash
terraform fmt -check
terraform validate
```

Sempre que possível, também deve ser gerado:

```bash
terraform plan
```

O resultado do `plan` deve ser revisado antes de qualquer `apply`.

O `terraform apply` não deve ser executado sem que as alterações planejadas sejam conhecidas e revisadas.

---

## 3.7 Terraform Plan

O `terraform plan` deve ser tratado como uma etapa importante do processo de revisão.

Durante a análise, verificar principalmente:

* Recursos criados;
* Recursos alterados;
* Recursos removidos;
* Recursos substituídos;
* Mudanças inesperadas.

Alterações destrutivas devem receber atenção especial.

---

## 3.8 Terraform Apply

Em ambientes compartilhados e principalmente em produção, deve-se evitar executar:

```bash
terraform apply
```

diretamente a partir da máquina pessoal de um contribuidor quando existir uma pipeline ou processo automatizado responsável pelo provisionamento.

O fluxo recomendado é:

```text
Alteração Terraform
        ↓
Pull Request
        ↓
terraform plan
        ↓
Revisão
        ↓
Merge
        ↓
Pipeline autorizada
        ↓
terraform apply
```

Essa abordagem melhora:

* Rastreabilidade;
* Controle de acesso;
* Auditoria;
* Reprodutibilidade.

---

# 4. Docker

As imagens Docker devem ser reproduzíveis, mínimas e versionadas.

---

## 4.1 Versionamento

Não utilizar a tag `latest` para imagens executadas em produção.

Evitar:

```text
apae-backend:latest
```

Preferir versões identificáveis:

```text
apae-backend:1.4.0
```

Também podem ser utilizados identificadores imutáveis relacionados ao commit:

```text
apae-backend:a73f2c1
```

A versão utilizada em produção deve permitir identificar qual código originou aquela imagem.

---

## 4.2 Imutabilidade das imagens

Uma tag utilizada para identificar uma versão de produção não deve posteriormente apontar para uma imagem diferente.

Por exemplo:

```text
apae-backend:1.4.0
```

deve representar sempre o mesmo artefato.

Não deve ocorrer:

```text
1.4.0 → imagem A

posteriormente

1.4.0 → imagem B
```

Caso seja necessária uma nova imagem, deve ser criada uma nova versão.

Exemplo:

```text
1.4.1
```

Essa prática aumenta a previsibilidade de deploys e rollbacks.

---

## 4.3 Imagens base

Utilizar preferencialmente imagens:

* Oficiais;
* Mantidas;
* Com versões explicitamente definidas;
* Com apenas os componentes necessários para execução da aplicação.

Evitar imagens base sem versão definida.

---

## 4.4 Multi-stage build

Quando aplicável, utilizar **multi-stage builds** para separar as ferramentas utilizadas durante a compilação da imagem utilizada em runtime.

Exemplo conceitual:

```text
Build
Maven + JDK + código
        ↓
      app.jar
        ↓
Runtime
JRE + app.jar
```

Isso evita levar ferramentas de compilação e arquivos desnecessários para a imagem final.

---

## 4.5 Usuário não-root

Containers não devem executar como `root` sem necessidade técnica justificada.

Quando possível, definir um usuário específico para execução da aplicação.

Exemplo:

```dockerfile
RUN addgroup --system app && adduser --system --ingroup app app

USER app
```

---

## 4.6 Healthcheck

Quando a aplicação oferecer um mecanismo adequado para verificar seu estado, deve-se utilizar health checks.

Exemplo conceitual:

```text
Aplicação
   ↓
Endpoint de saúde
   ↓
Healthcheck / Probe
```

Aplicações web podem, por exemplo, fornecer endpoints como:

```text
/health
/actuator/health
```

Esses mecanismos podem posteriormente ser utilizados por Docker, Kubernetes ou ferramentas de monitoramento.

---

## 4.7 Conteúdo da imagem

Não incluir na imagem:

* Segredos;
* Credenciais;
* Chaves privadas;
* Arquivos `.env` de produção;
* Arquivos temporários;
* Conteúdo desnecessário para execução.

Utilizar `.dockerignore` para reduzir o contexto do build.

---

# 5. Kubernetes

Os manifests Kubernetes devem seguir um padrão consistente e declarar explicitamente os recursos necessários para execução das aplicações.

A organização definida pelo repositório deve ser respeitada:

```text
kubernetes/
├── base/
└── overlays/
    ├── dev/
    ├── hml/
    └── prod/
```

As configurações comuns devem permanecer em `base`, enquanto diferenças específicas de cada ambiente devem permanecer nos respectivos `overlays`.

---

## 5.1 Requests e Limits

Workloads devem declarar `requests` e `limits` de CPU e memória sempre que aplicável.

Exemplo:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

`requests` representam os recursos considerados necessários para o agendamento do Pod.

`limits` estabelecem limites máximos de utilização.

Os valores devem ser definidos e posteriormente ajustados com base no comportamento real das aplicações.

---

## 5.2 Health checks

Aplicações devem utilizar probes quando forem capazes de fornecer endpoints ou mecanismos adequados de verificação.

### Readiness Probe

Indica quando a aplicação está pronta para receber tráfego.

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8080
```

### Liveness Probe

Permite identificar aplicações que deixaram de funcionar corretamente.

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
```

Os valores de timeout, período e quantidade de falhas devem ser definidos de acordo com o comportamento de cada aplicação.

### Startup Probe

Aplicações que possuem inicialização lenta devem considerar o uso de uma `startupProbe`.

A `startupProbe` verifica se a aplicação concluiu corretamente seu processo de inicialização antes que as demais verificações de saúde passem a atuar.

Exemplo:

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
```

Enquanto a `startupProbe` não indicar sucesso, as verificações de `liveness` e `readiness` não interferem na inicialização da aplicação.

Isso é especialmente útil para aplicações que:

* Possuem tempo de inicialização elevado;
* Executam carregamentos ou configurações durante o startup;
* Dependem de componentes que podem levar algum tempo para ficarem disponíveis;
* Poderiam ser reiniciadas prematuramente por uma `livenessProbe`.

Os valores de `failureThreshold`, `periodSeconds` e demais parâmetros devem ser definidos considerando o tempo esperado de inicialização de cada aplicação.

O objetivo não é simplesmente aumentar os tempos das probes, mas permitir que cada tipo de verificação represente corretamente uma fase do ciclo de vida da aplicação.

As três probes possuem responsabilidades diferentes e não devem ser utilizadas de forma intercambiável:

| Probe            | Responsabilidade                                                 |
| ---------------- | ---------------------------------------------------------------- |
| `startupProbe`   | Determinar se a aplicação terminou de inicializar                |
| `readinessProbe` | Determinar se a aplicação está pronta para receber tráfego       |
| `livenessProbe`  | Determinar se a aplicação continua saudável durante sua execução |

De forma resumida:

```text
Startup Probe
→ A aplicação terminou de iniciar?

Readiness Probe
→ A aplicação está pronta para receber tráfego?

Liveness Probe
→ A aplicação continua funcionando corretamente?
```

A configuração incorreta das probes pode causar comportamentos indesejados, como reinicializações desnecessárias ou envio de tráfego para aplicações que ainda não estão prontas.

Por esse motivo, os valores utilizados não devem ser copiados indiscriminadamente entre aplicações. Cada workload deve ser configurado considerando seu comportamento real.

---

## 5.3 Namespaces

Os recursos devem ser separados logicamente utilizando namespaces de acordo com a estratégia definida pelo projeto.

Exemplos:

```text
apae
atendimento
gestao-escolar
```

A separação por ambiente também deve respeitar a organização adotada para `dev`, `hml` e `prod`.

Recursos de aplicações diferentes não devem ser colocados arbitrariamente no namespace `default`.

---

## 5.4 Namespace default

Workloads das aplicações não devem ser implantados no namespace `default`, salvo quando existir uma justificativa técnica específica.

O uso de namespaces próprios facilita:

* Organização;
* Controle de acesso;
* Monitoramento;
* Identificação dos recursos;
* Aplicação de políticas específicas.

---

## 5.5 Security Context

Quando compatível com a aplicação, os Pods e containers devem possuir configurações de segurança explícitas.

Exemplo:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
```

Quando possível, capacidades Linux desnecessárias também devem ser removidas:

```yaml
securityContext:
  capabilities:
    drop:
      - ALL
```

Essas configurações reduzem o impacto de uma eventual vulnerabilidade dentro do container.

---

## 5.6 ConfigMaps e Secrets

Utilizar `ConfigMap` para configurações não sensíveis.

Exemplos:

* URLs públicas;
* Flags de configuração;
* Nomes de ambiente;
* Parâmetros não confidenciais.

Utilizar mecanismos apropriados de Secret para informações sensíveis.

Exemplos:

* Tokens;
* Senhas;
* Chaves de API;
* Credenciais de bancos.

Segredos não devem ser armazenados em texto puro no Git.

---

# 6. ArgoCD e GitOps

O Git deve ser considerado a **fonte da verdade** para recursos gerenciados através do ArgoCD.

O estado desejado das aplicações e da infraestrutura Kubernetes deve estar versionado no repositório.

O fluxo esperado é:

```text
Alteração necessária
        ↓
Alteração no Git
        ↓
Pull Request
        ↓
Revisão
        ↓
Merge
        ↓
ArgoCD
        ↓
Kubernetes
```

---

## 6.1 Alterações manuais

Não editar manualmente recursos Kubernetes gerenciados pelo ArgoCD.

Evitar alterações como:

```bash
kubectl edit deployment ...
```

quando o recurso possui seu estado desejado controlado pelo Git/ArgoCD.

Uma alteração manual pode criar **drift**, fazendo com que o estado real do cluster seja diferente do estado definido no repositório.

Toda mudança persistente deve ser realizada no Git e seguir o fluxo de revisão estabelecido pelo projeto.

---

## 6.2 Sincronização

Caso o ArgoCD indique um recurso como `OutOfSync`, a causa da divergência deve ser analisada antes de aplicar alterações manuais.

O objetivo é manter:

```text
Estado desejado no Git
        =
Estado executado no cluster
```

---

## 6.3 Self-healing

Quando habilitado, o recurso de `selfHeal` do ArgoCD pode restaurar automaticamente recursos que tenham sido modificados fora do Git.

Exemplo:

```text
Git
replicas: 2

Cluster alterado manualmente
replicas: 3

        ↓

ArgoCD detecta drift

        ↓

selfHeal

        ↓

replicas: 2
```

O uso de `selfHeal` deve estar alinhado à política de que mudanças persistentes devem passar pelo Git.

---

## 6.4 Prune

O `prune` permite remover do cluster recursos que deixaram de existir no estado desejado armazenado no Git.

Exemplo:

```text
Deployment removido do Git
        ↓
ArgoCD detecta diferença
        ↓
Prune
        ↓
Deployment removido do cluster
```

O uso de `prune` automático em produção deve ser definido conscientemente pelo time.

Recursos críticos não devem ser removidos automaticamente sem que os impactos da política adotada sejam compreendidos.

---

## 6.5 Organização

As configurações do ArgoCD devem seguir a estrutura definida para o repositório, mantendo uma `Application` para cada combinação necessária de aplicação e ambiente.

---

# 7. GitHub Actions

Os workflows devem seguir o princípio do **menor privilégio**.

---

## 7.1 Permissions

Declarar explicitamente as permissões necessárias para cada workflow ou job.

Exemplo:

```yaml
permissions:
  contents: read
```

Quando for necessário publicar uma imagem:

```yaml
permissions:
  contents: read
  packages: write
```

Evitar conceder `write` quando a pipeline necessita apenas de leitura.

---

## 7.2 Segredos

Segredos devem ser consumidos utilizando GitHub Secrets ou solução equivalente.

Nunca imprimir segredos em logs.

Evitar comandos ou configurações que possam expor tokens, senhas ou outras credenciais durante a execução da pipeline.

---

## 7.3 Actions utilizadas

Sempre que possível:

* Utilizar actions conhecidas e mantidas;
* Fixar versões das actions utilizadas;
* Evitar dependências desnecessárias;
* Reutilizar workflows quando vários processos executarem etapas equivalentes.

Exemplo:

```yaml
uses: actions/checkout@v4
```

---

## 7.4 Actions de terceiros

Antes de utilizar uma Action de terceiros, verificar:

* Reputação do projeto;
* Manutenção recente;
* Quantidade de usuários;
* Histórico de segurança;
* Permissões necessárias.

Em workflows sensíveis, pode-se considerar fixar a Action pelo SHA de um commit específico.

Exemplo:

```yaml
uses: organizacao/action@<commit-sha>
```

Isso reduz o risco de uma tag ser alterada posteriormente.

Para workflows sensíveis, deve-se **preferir a utilização do SHA completo do commit** ao referenciar Actions de terceiros.

Exemplo:

```yaml
uses: organizacao/action@8f4c2a1b7d4e5f6...
```

Uma referência baseada em SHA completo é imutável, garantindo que o workflow continuará executando exatamente o código que foi previamente revisado.

Referências baseadas somente em tags, como:

```yaml
uses: organizacao/action@v1
```

podem apontar para versões diferentes ao longo do tempo caso a tag seja atualizada pelo mantenedor.

Portanto:

```text
SHA completo
→ maior garantia de imutabilidade

Tag de versão
→ maior facilidade de atualização
```

Para pipelines com acesso a:

* Produção;
* Credenciais;
* Infraestrutura cloud;
* Container Registry;
* Kubernetes;
* Terraform;
* Segredos;

deve-se dar preferência à referência por SHA completo, especialmente para Actions de terceiros.

Actions oficiais ou amplamente utilizadas também devem possuir versão explicitamente definida e ser atualizadas de forma controlada através de Pull Requests.

---

## 7.5 OIDC

Quando o provedor utilizado oferecer suporte, preferir autenticação federada via **OpenID Connect (OIDC)** em vez de armazenar credenciais permanentes de cloud.

Evitar depender, quando possível, de credenciais de longa duração como:

```text
ACCESS_KEY
SECRET_ACCESS_KEY
```

O fluxo preferencial é:

```text
GitHub Actions
      ↓
OIDC
      ↓
Provedor Cloud
      ↓
Credencial temporária
```

Isso reduz o impacto de possíveis vazamentos de credenciais.

---

## 7.6 Responsabilidade da CI

Os workflows devem possuir responsabilidades claras.

Exemplos:

```text
Pull Request
↓
Lint
Testes
Validação
```

```text
Merge / Release
↓
Testes
Build
Docker Build
Security Scan
Publicação da imagem
```

Falhas em etapas obrigatórias devem impedir que uma alteração prossiga para as próximas fases do fluxo.

---

# 8. Observabilidade

O repositório possui infraestrutura destinada à observabilidade utilizando ferramentas como Prometheus, Grafana e Loki.

As aplicações executadas em produção devem seguir algumas práticas básicas para facilitar monitoramento e diagnóstico.

---

## 8.1 Logs

Aplicações containerizadas devem preferencialmente enviar logs para:

```text
stdout
stderr
```

Evitar depender exclusivamente de arquivos de log armazenados dentro do container.

Containers podem ser destruídos e recriados, portanto arquivos locais não devem ser considerados armazenamento permanente de logs.

---

## 8.2 Identificação

Logs e métricas devem permitir identificar, quando possível:

* Aplicação;
* Ambiente;
* Serviço;
* Instância ou Pod;
* Tipo de evento.

---

## 8.3 Métricas

Aplicações devem expor métricas quando houver suporte e necessidade operacional.

Essas métricas podem posteriormente ser coletadas por ferramentas como Prometheus.

---

## 8.4 Dashboards

Dashboards devem apresentar informações relevantes para operação dos ambientes, evitando painéis sem finalidade clara.

Exemplos:

* Consumo de CPU;
* Consumo de memória;
* Disponibilidade;
* Quantidade de erros;
* Latência;
* Reinicializações de Pods.

---

# 9. Alterações destrutivas

Mudanças de infraestrutura que possam causar:

```text
destroy
delete
replace
recreate
```

devem ser explicitamente destacadas no Pull Request.

O revisor deve ser capaz de identificar claramente:

* Qual recurso será afetado;
* Qual ambiente será impactado;
* Por que a alteração é necessária;
* Se existe risco de indisponibilidade;
* Se existe risco de perda de dados;
* Qual é a estratégia de recuperação.

No Terraform, alterações destrutivas devem receber atenção especial durante a revisão do:

```bash
terraform plan
```

---

# 10. Rollback

Alterações devem considerar, quando aplicável, uma estratégia de rollback.

Para aplicações containerizadas, isso pode significar voltar para uma imagem anterior.

Exemplo:

```text
1.4.0
↓ problema
1.3.0
```

Entretanto, rollback da aplicação não garante rollback de todos os componentes do sistema.

---

## 10.1 Banco de dados

Alterações de banco de dados devem receber atenção especial.

Voltar para uma versão anterior da aplicação não necessariamente desfaz migrações já aplicadas ao banco.

Exemplo:

```text
Aplicação 1.4.0
        ↓
Migração de banco
        ↓
Novo schema

Rollback aplicação
1.4.0 → 1.3.0

        ≠

Rollback automático do banco
```

Migrações devem ser projetadas considerando:

* Compatibilidade entre versões;
* Possibilidade de reversão;
* Backup;
* Risco de perda de dados.

---

# 11. Boas práticas gerais

## 11.1 Pull Requests pequenos

Preferir Pull Requests com escopo pequeno e claramente definido.

Evitar reunir alterações independentes em um único PR.

PRs menores:

* Facilitam revisão;
* Reduzem risco;
* Facilitam identificação de problemas;
* Simplificam rollback;
* Diminuem conflitos.

---

## 11.2 Revisão

Mudanças de infraestrutura devem passar por revisão antes do merge.

Alterações com impacto significativo devem apresentar informações suficientes para que o revisor compreenda:

* O que será alterado;
* Qual ambiente será afetado;
* Qual o impacto esperado;
* Como a alteração foi validada.

---

## 11.3 Documentação

Quando uma alteração modificar:

* Arquitetura;
* Estrutura de diretórios;
* Procedimentos;
* Pipelines;
* Processo de deploy;
* Convenções;

a documentação correspondente também deve ser atualizada.

Uma mudança não deve ser considerada completamente finalizada quando deixa a documentação do repositório inconsistente com o comportamento real da infraestrutura.

---

# 12. Decisões arquiteturais

Decisões arquiteturais relevantes devem ser documentadas quando necessário.

Sempre que possível, recomenda-se utilizar **Architecture Decision Records (ADR)**.

Uma possível estrutura é:

```text
docs/
└── adr/
    ├── 001-adocao-kubernetes.md
    ├── 002-adocao-argocd.md
    └── 003-estrategia-gitops.md
```

Um ADR deve registrar, de forma resumida:

```text
Contexto
↓
Alternativas consideradas
↓
Decisão
↓
Motivação
↓
Consequências
```

Exemplos de decisões que podem justificar um ADR:

* Kubernetes ou Docker Compose;
* Distribuição Kubernetes utilizada;
* Traefik ou NGINX;
* Estratégia de GitOps;
* Organização dos ambientes;
* Estratégia de observabilidade;
* Estratégia de armazenamento de secrets.

ADRs não precisam ser utilizados para decisões pequenas ou facilmente reversíveis.

---

# 13. Checklist antes do Pull Request

Antes de abrir um Pull Request, verificar quando aplicável:

## Segurança

* Nenhum segredo ou credencial foi adicionado;
* Nenhum dado sensível aparece em arquivos ou logs;
* ConfigMaps não contêm dados sensíveis;
* Credenciais permanentes foram evitadas quando existe alternativa mais segura.

## Terraform

* `terraform fmt -check` executado;
* `terraform validate` executado;
* `terraform plan` analisado quando aplicável;
* Arquivos de state não foram adicionados;
* Providers possuem versões definidas;
* `.terraform.lock.hcl` está atualizado quando aplicável;
* Nenhuma alteração destrutiva passou despercebida;
* O state não foi editado manualmente.

## Docker

* Imagem possui versão definida;
* `latest` não é utilizado para produção;
* A imagem não contém segredos;
* Container não executa como root sem justificativa;
* O build contém somente os arquivos necessários;
* Tags de produção não estão sendo sobrescritas;
* Multi-stage build foi utilizado quando aplicável;
* Healthcheck foi considerado quando aplicável.

## Kubernetes / ArgoCD

* Requests e limits foram definidos quando aplicável;
* Probes foram configuradas quando aplicável;
* `startupProbe` foi considerada para aplicações com inicialização lenta;
* As probes possuem parâmetros compatíveis com o comportamento real da aplicação;
* Namespace correto utilizado;
* O namespace `default` não está sendo utilizado sem justificativa;
* `securityContext` foi considerado;
* ConfigMaps e Secrets estão sendo utilizados corretamente;
* Alterações de recursos gerenciados pelo ArgoCD foram realizadas através do Git;
* Políticas de `selfHeal` e `prune` foram consideradas quando aplicável.

## GitHub Actions

* `permissions:` utiliza apenas os privilégios necessários;
* Segredos não são expostos nos logs;
* As actions utilizadas possuem versão definida;
* Actions de terceiros foram revisadas;
* Actions de terceiros utilizadas em workflows sensíveis estão preferencialmente fixadas por SHA completo;
* Alterações de versão ou SHA de Actions foram revisadas antes do merge;
* OIDC foi considerado quando aplicável;
* Workflows reutilizáveis foram considerados quando houver etapas repetidas.

## Observabilidade

* Logs são enviados para `stdout/stderr` quando aplicável;
* A aplicação pode ser identificada nos logs;
* Métricas foram consideradas quando necessárias;
* Health checks estão disponíveis quando aplicável.

## Alterações destrutivas

* Recursos que serão removidos ou substituídos foram identificados;
* Impactos estão descritos no PR;
* Estratégia de recuperação foi considerada;
* Riscos de perda de dados foram analisados.

## Rollback

* Existe estratégia de rollback quando necessária;
* Alterações de banco foram consideradas separadamente;
* Rollback da aplicação não está sendo tratado como rollback automático do banco.

## Geral

* Alteração possui escopo claro;
* Documentação foi atualizada quando necessário;
* PR está vinculado à issue correspondente;
* Decisões arquiteturais relevantes foram documentadas quando necessário.

---

# 14. Referências internas

* [Estrutura do repositório](estrutura-repositorio.md)
* [Padronização de mensagens de commit](padronizacao-commits.md)
* [Padronização de abertura de Pull Requests](padronizacao-pull-requests.md)
