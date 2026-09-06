# 4. Docker

[← Voltar ao índice](README.md)

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
