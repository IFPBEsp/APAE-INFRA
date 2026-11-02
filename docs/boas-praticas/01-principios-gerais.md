# 1. Princípios gerais

[← Voltar ao índice](README.md)

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
