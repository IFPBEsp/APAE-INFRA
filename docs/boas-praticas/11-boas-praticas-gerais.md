# 11. Boas práticas gerais

[← Voltar ao índice](README.md)

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
