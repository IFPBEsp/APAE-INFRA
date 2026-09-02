# 2. Gestão de segredos e credenciais

[← Voltar ao índice](README.md)

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
