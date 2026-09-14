# 14. Estimativa de esforço (escala de Fibonacci)

[← Voltar ao índice](README.md)

As issues do board (projeto "Infra - 2026.2") são pontuadas usando a sequência de Fibonacci: `1, 2, 3, 5, 8, 13, 21`.

O objetivo não é medir tempo (horas ou dias), e sim o esforço relativo entre issues. Quanto maior o número, maior a complexidade, o volume de trabalho ou a incerteza em relação a uma issue já conhecida. O espaçamento crescente entre os valores é intencional: força escolher entre "parecida com uma de 5" ou "claramente maior, então é 8", em vez de tentar diferenciar precisão que não existe entre, por exemplo, 6 e 7.

## 14.1 Significado de cada valor

| Pontos | Esforço/complexidade |
|---|---|
| 1 | Trivial. Mudança pontual, sem investigação necessária (ex.: corrigir um texto, ajustar uma variável). |
| 2 | Pequeno. Escopo claro, poucas etapas, baixo risco. |
| 3 | Moderado. Mais de uma etapa ou arquivo envolvido, mas sem incerteza relevante. |
| 5 | Considerável. Múltiplas etapas, alguma investigação ou dependência externa. |
| 8 | Grande. Escopo amplo ou com partes ainda não totalmente claras; normalmente candidata a ser dividida em issues menores. |
| 13 | Muito grande. Alta incerteza ou múltiplas dependências; forte candidata a ser quebrada antes de entrar em execução. |
| 21 | Extremamente grande ou incerta. Não deve permanecer nesse tamanho: a issue precisa ser detalhada e dividida antes de ser estimada de novo. |

## 14.2 Exemplos de issue por pontuação

Os exemplos abaixo são fictícios, criados apenas para ilustrar a escala. Não correspondem a issues reais do board.

| Pontos | Exemplo de issue | Por que essa pontuação |
|---|---|---|
| 1 | "[DOCS] Corrigir link quebrado no README" | Basta localizar e trocar a URL, sem investigação. |
| 2 | "[CHORE] Adicionar variável de ambiente faltante no manifest do serviço de notificações" | Escopo já conhecido, uma única alteração pontual. |
| 3 | "[CI] Adicionar cache de dependências no workflow de testes" | Mexe em mais de um step do workflow, mas sem incerteza sobre o resultado. |
| 5 | "[CHORE] Criar manifests Kubernetes base para o serviço de agendamento" | Múltiplas etapas (Deployment, Service, ConfigMap) e depende de levantar portas e variáveis reais. |
| 8 | "[CI] Criar pipeline reutilizável de scan de vulnerabilidades para imagens Docker" | Escopo amplo, com decisões de design ainda em aberto (severidade que bloqueia, gatilho de execução). |
| 13 | "[FEAT] Migrar a estratégia de gestão de segredos para um cofre externo (Vault ou Sealed Secrets)" | Alta incerteza, múltiplos serviços afetados e dependência de uma ferramenta ainda não adotada. |
| 21 | "[FEAT] Provisionar toda a infraestrutura base (Terraform, cluster Kubernetes e ArgoCD) do zero" | Escopo grande demais para estimar com confiança. Deveria ser quebrada em issues menores antes de pontuar. |

## 14.3 Onde registrar a pontuação

O board não possui um campo numérico dedicado à estimativa. A pontuação é registrada como **label da issue**, usando os labels `1`, `2`, `3`, `5`, `8`, `13` ou `21` (já criados no repositório, cada um com a descrição `Fibonacci: {descrição da pontuação}`). O label aparece na coluna `Labels` do board, junto dos demais labels da issue (área, tipo, etc.):

```text
Labels da issue: infra, documentation, 5
```

Cada issue deve ter no máximo um label de pontuação. Se o escopo mudar significativamente após a estimativa inicial, o label deve ser atualizado para refletir o novo entendimento.

## 14.4 Orientações para estimar

* Comparar a issue com outras já pontuadas no board, usando os labels existentes como referência, já que a pontuação é relativa, não absoluta;
* Estimar o card como um todo, não cada critério de aceite separadamente;
* Quando a issue for muito incerta para caber em 1–13, preferir quebrá-la em issues menores a atribuir 21;
* Issues sem critérios de aceite claros são difíceis de estimar com precisão; vale revisar a descrição antes de pontuar.

Atualmente a atribuição da pontuação é centralizada em uma única pessoa responsável, para evitar divergência de critério enquanto a prática está sendo consolidada. Este guia deve ser usado como referência comum à medida que mais pessoas passarem a estimar issues.

## 14.5 Referências

* [Planning Poker](https://blog.runrun.it/planning-poker/): técnica de estimativa ágil que popularizou o uso da série de Fibonacci para pontuar esforço relativo.

---
