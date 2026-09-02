# 12. Decisões arquiteturais

[← Voltar ao índice](README.md)

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
