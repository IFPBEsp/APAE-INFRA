# 7. GitHub Actions

[← Voltar ao índice](README.md)

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
