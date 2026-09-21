# 4. Docker

[← Voltar ao índice](README.md)

As imagens Docker devem ser reproduzíveis, mínimas e versionadas.

---

## 4.1 Versionamento e rastreabilidade

As imagens Docker devem seguir a política central de identificação e rastreabilidade definida em:

[Política de tags de imagens Docker](16-politica-tags-imagens-docker.md)

Como regra geral:

- o digest OCI (`image@sha256:<digest>`) é a referência canônica e imutável;
- `sha-<short-sha>` é utilizado para rastreabilidade entre imagem e commit;
- `vX.Y.Z` pode ser utilizado para releases;
- `latest` não deve ser utilizado em deployments, rollback, auditoria ou GitOps.

---

## 4.2 Imutabilidade das imagens

A identidade técnica definitiva de uma imagem é o digest OCI.

Tags são referências mutáveis no registry e devem seguir as regras definidas na
[política de versionamento e rastreabilidade](16-politica-tags-imagens-docker.md).

Tags baseadas em commit e versões de release não devem ser sobrescritas para apontar para conteúdos diferentes.

---

## 4.3 Imagens base

Utilizar preferencialmente imagens:

- Oficiais;
- Mantidas;
- Com versões explicitamente definidas;
- Com apenas os componentes necessários para execução da aplicação.

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

- Segredos;
- Credenciais;
- Chaves privadas;
- Arquivos `.env` de produção;
- Arquivos temporários;
- Conteúdo desnecessário para execução.

Utilizar `.dockerignore` para reduzir o contexto do build.

---
