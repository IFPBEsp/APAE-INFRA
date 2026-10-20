# Decisão arquitetural

**Status:** proposta atualizada pela issue #86, pendente de validação do time. O [levantamento e a matriz de responsabilidades](06-conclusao-e-proximos-passos.md) detalham as evidências e pendências da VPS HostGator.

## 1. Resumo

Após avaliar:

- GitHub Actions + Terraform;
- ArgoCD + Terraform Operator;
- ArgoCD + Crossplane;
- arquitetura híbrida;

a recomendação para o estágio atual do `APAE-INFRA` é:

> **Utilizar GitHub Actions para executar Terraform sobre recursos externos com API/provider validado e Ansible sobre o host, k3s e bootstrap do ArgoCD. Manter ArgoCD responsável pela reconciliação dos recursos Kubernetes atribuídos às suas Applications.**

Terraform Operator e Crossplane permanecem como alternativas futuras, condicionadas ao surgimento de requisitos que justifiquem sua complexidade.

---

## 2. Arquitetura

```text
Git → Pull Request / Review
├── GitHub Actions → Terraform → GitHub / DNS e backend quando suportados
├── GitHub Actions → Ansible   → host / k3s / bootstrap do ArgoCD
└── ArgoCD                    → Applications filhas / recursos Kubernetes

Portal/suporte HostGator → operações da VPS; integração Terraform dispensada nesta etapa
```

---

## 3. Fonte da verdade

Git será a fonte da verdade para os três domínios:

```text
Git
├── Terraform
├── Ansible
└── Kubernetes
```

A diferença está no reconciliador/executor:

```text
Terraform / Ansible
→ GitHub Actions

Kubernetes
→ ArgoCD
```

Isso mantém GitOps sem transformar ArgoCD em executor universal.

---

## 4. Responsabilidades

### Terraform

Responsável por recursos externos com integração validada: configurações dos repositórios GitHub (issue #88), infraestrutura do backend remoto (issue #87) e DNS quando houver API/provider adequado à zona autoritativa.

Por decisão registrada em 17/10/2026, a integração Terraform com a VPS HostGator, rede, volumes, firewall do provedor e snapshots não será adotada nesta etapa. As operações do provedor serão realizadas pelo Portal/suporte. A existência de API/provider permanece não confirmada, mas sua investigação não é requisito para concluir a issue #86; a configuração da VPS existente será realizada pelo Ansible via SSH. DNS e backend de state serão avaliados independentemente. A identificação OCI do produto não comprova acesso à conta Oracle necessária ao provider `oracle/oci`.

Providers Helm e Kubernetes foram avaliados para bootstrap, mas não serão adotados para esse fim nesta VPS. Não haverá provisioners SSH Terraform para configurar o host.

### Ansible

Responsável pelo sistema operacional, usuários, SSH, pacotes, serviços e firewall local, instalação/manutenção do k3s e instalação/manutenção inicial do ArgoCD. AppProject de bootstrap e Application raiz ficam com Ansible enquanto estiverem excluídos da reconciliação, conforme o PR #80.

Transferir algum desses recursos ao ArgoCD exigirá uma decisão explícita e retirada da gestão anterior, sem dois responsáveis pelo mesmo objeto.

### GitHub Actions

Responsável por automatizar:

```text
fmt
validate
plan
aprovações
apply
```

e pelas validações/aprovações das execuções Ansible, conforme workflows que serão definidos posteriormente. GitHub Actions orquestra e não assume a propriedade dos recursos.

### ArgoCD

Responsável pela reconciliação dos recursos Kubernetes depois que o cluster estiver disponível.

Applications filhas, workloads, Gateway API, NGINX Gateway Fabric e cert-manager quando implementado pertencem ao ArgoCD. Não se presume autogerenciamento do próprio ArgoCD ou dos objetos excluídos da reconciliação.

O Terraform não deve continuar administrando os mesmos recursos Kubernetes que pertencem ao ArgoCD.

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

O backend deverá ser externo à VPS e ao k3s. Contabo Object Storage é apenas candidato histórico, sem seleção implícita; escolha e PoC de locking/recuperação pertencem à issue #87.

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
→ recursos externos com integração validada

Ansible + GitHub Actions
→ host, k3s e bootstrap

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
