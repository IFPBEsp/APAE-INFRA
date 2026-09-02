# 6. ArgoCD e GitOps

[← Voltar ao índice](README.md)

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
