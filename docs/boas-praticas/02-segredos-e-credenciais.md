# 2. Gestão de segredos e credenciais

[← Voltar ao índice](README.md)

Segredos e credenciais nunca devem ser armazenados em texto plano no repositório.

Isso inclui:

* Tokens de acesso e chaves de API;
* Senhas e credenciais de banco de dados;
* Chaves privadas (SSH, RSA, JWT private keys);
* Credenciais de provedores de nuvem e buckets (S3 / MinIO);
* Tokens de acesso ao Kubernetes ou ArgoCD.

---

## 2.1 Armazenamento no GitHub Actions

Quando uma credencial for necessária exclusivamente em uma esteira de automação (CI/CD), deve ser utilizado o mecanismo de **Secrets do GitHub Actions** (ou Environments protegidos para deploys em produção):

```yaml
env:
  DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
```

Nunca utilizar:

```yaml
env:
  DEPLOY_TOKEN: "token-real-da-aplicacao"
```

Arquivos contendo valores sensíveis devem ser mantidos fora do controle de versão via `.gitignore`:

```text
.env
*.pem
*.key
credentials.json
terraform.tfstate
terraform.tfstate.*
```

---

## 2.2 ConfigMap vs Secret no Kubernetes

No Kubernetes, a separação de responsabilidades entre recursos deve ser estritamente respeitada:

```text
ConfigMap  → configurações não sensíveis (portas, URLs públicas, flags de log)
Secret     → informações sensíveis (senhas, segredos JWT, tokens de banco de dados)
```

O fato de um recurso ser do tipo `Secret` não significa que ele possa ser commitado diretamente no Git. No padrão GitOps, **arquivos `kind: Secret` com valores em texto plano ou base64 nunca devem ser versionados**.

---

## 2.3 Estratégia GitOps: Sealed Secrets (Bitnami)

Conforme definido na [ADR 005](../adr/005-estrategia-gestao-secrets.md), o projeto adota o **Bitnami Sealed Secrets** como solução oficial para versionamento seguro de credenciais no GitOps.

### Como Funciona o Fluxo

1. **Criptografia Assimétrica**: O cluster k3s possui um controller (`sealed-secrets-controller`) que detém uma **chave privada**. A respectiva **chave pública** é disponibilizada publicamente para a equipe de desenvolvimento.
2. **Cifragem Offline / Segura**: O desenvolvedor utiliza a ferramenta de linha de comando `kubeseal` junto com o certificado público para transformar um `Secret` do Kubernetes em um `SealedSecret`.
3. **Commit no Git**: O manifesto `SealedSecret` contém apenas valores cifrados irreversíveis sem a chave privada e pode ser comitado com total segurança no Git.
4. **Reconciliação e Descriptografia**: O **ArgoCD** aplica o `SealedSecret` no cluster, onde o controller intercepta o recurso, valida o escopo, descriptografa o conteúdo usando a chave privada e cria o recurso nativo `Secret` correspondente em tempo de execução no namespace da aplicação.

```text
[Secret Local (Texto Puro)]
           │
           ▼ kubeseal --cert pub-cert.pem
[SealedSecret (Cifrado)] ───► Git Commit & Push ───► ArgoCD Sync
                                                           │
                                                           ▼ (Cluster K8s)
                                                 [Sealed Secrets Controller]
                                                           │
                                                           ▼
                                                [Secret K8s em Memória/etcd]
                                                           │
                                                           ▼
                                                [Pod da Aplicação via envFrom]
```

### Instalação do utilitário `kubeseal` (Cliente)

Para Linux x86_64:

```bash
KUBESEAL_VERSION="0.28.0"
curl -OL "https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz"
tar -xvzf "kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz" kubeseal
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
rm "kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz" kubeseal
```

### Obtenção da Chave Pública do Cluster

Caso tenha acesso direto ao cluster com `kubectl`:

```bash
kubeseal --fetch-cert \
  --controller-name=sealed-secrets-controller \
  --controller-namespace=kube-system > pub-sealed-secrets.pem
```

Alternativamente, a chave pública pode ser compartilhada no repositório de documentação ou canal seguro da equipe.

### Criação e Cifragem de um Secret

* Crie o manifesto `Secret` tradicionalmente (apenas na sua estação local, **nunca faça commit deste arquivo**):

```bash
kubectl create secret generic api-secrets \
  --namespace=apae \
  --from-literal=SPRING_DATASOURCE_PASSWORD='senha_super_secreta' \
  --from-literal=JWT_SECRET='chave_jwt_super_longa_e_segura_32_bytes' \
  --dry-run=client -o yaml > /tmp/temp-secret.yaml
```

* Criptografe o manifesto gerando o `SealedSecret`:

```bash
kubeseal --format=yaml \
  --cert=pub-sealed-secrets.pem \
  --scope=strict \
  < /tmp/temp-secret.yaml > kubernetes/apae-geral/base/api/sealedsecret.yaml

# Remova imediatamente o arquivo com segredos em texto puro da estação local
rm -f /tmp/temp-secret.yaml
```

* Inclua o `sealedsecret.yaml` no `kustomization.yaml` do componente e realize o commit no Git.

---

## 2.4 Escopo de Segurança (`Scope`)

O `kubeseal` suporta três escopos de criptografia. No APAE-INFRA, a regra mandatória é o escopo **strict**:

* **`strict` (Obrigatório)**: O segredo é cifrado com base no **nome do Secret** e no **Namespace**. Ele não pode ser descriptografado se for renomeado ou movido para outro namespace, prevenindo reaproveitamento inadvertido ou ataques de privilege escalation entre aplicações.
* `namespace-wide` *(não recomendado)*: Pode ser descriptografado por qualquer Secret no mesmo namespace.
* `cluster-wide` *(proibido)*: Pode ser descriptografado com qualquer nome em qualquer namespace.

---

## 2.5 Procedimentos Operacionais: Backup e Rotação

### Backup da Chave Mestra (Disaster Recovery)

A chave mestra privada que descriptografa todos os segredos gerados pelo controller reside no namespace `kube-system`:

```bash
# Exportar par de chaves mestras ativas
kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secret-key -o yaml > master-sealed-secrets-backup.yaml
```

> [!CAUTION]
> O arquivo `master-sealed-secrets-backup.yaml` contém a **chave privada**. Ele nunca deve ser comitado no Git. Deve ser armazenado em cofre seguro offline pelos administradores de infraestrutura da VPS.

### Procedimento de Restauração em caso de reconstrução do cluster

```bash
kubectl apply -f master-sealed-secrets-backup.yaml
kubectl rollout restart deployment sealed-secrets-controller -n kube-system
```

### Rotação de Chaves

O controller rotaciona sua chave de cifragem periodicamente (por padrão a cada 30 dias).

* Quando uma chave é rotacionada, a chave privada anterior **não é excluída**: ela permanece armazenada no cluster para que `SealedSecrets` antigos continuem funcionando perfeitamente sem interrupção de serviço.
* Novos segredos criados após a rotação passam a ser cifrados com a nova chave pública.
* Para re-cifrar segredos legados com a nova chave ativa, utilize a funcionalidade de re-encryption do `kubeseal` (`kubeseal --re-encrypt`).

---

## 2.6 Ocorrência de Segredo Commitado por Engano

Caso uma credencial real seja commitada acidentalmente em texto puro:

1. **Revogar e rotacionar imediatamente** a credencial comprometida no serviço de origem (banco, bucket, etc.);
2. **Gerar uma nova credencial** e cifrá-la via `kubeseal`;
3. Remover o arquivo sensível do repositório;
4. Reescrever o histórico do Git quando aplicável (ex.: `git filter-repo` ou BFG Repo-Cleaner) ou invalidar permanentemente a chave antiga;
5. Notificar a equipe de infraestrutura e segurança.

Apenas remover o segredo em um commit posterior **não é suficiente**, pois ele permanece gravado no histórico de commits do repositório.
