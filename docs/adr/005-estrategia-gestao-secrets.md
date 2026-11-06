# ADR 005 — Estratégia de Gestão de Secrets no Cluster Kubernetes

## Status

Aceito.

## Contexto

Os manifestos Kubernetes base dos repositórios de produto (`apae-geral`, `apae-gestao-escolar`, `apae-atendimento` e `apae-site-comemorativo`) foram estruturados sem valores sensíveis em texto puro, atendendo aos princípios estabelecidos na issue [#37](https://github.com/IFPBEsp/APAE-INFRA/issues/37) e em [`docs/boas-praticas/02-segredos-e-credenciais.md`](../boas-praticas/02-segredos-e-credenciais.md). Com isso, variáveis essenciais para a inicialização dos serviços (como senhas de banco de dados, `JWT_SECRET`, tokens de API e credenciais de storage S3/MinIO) foram intencionalmente postergadas.

Para habilitar a execução real das aplicações mantendo a conformidade com o paradigma **GitOps** (onde o Git é a única fonte da verdade e o cluster é reconciliado continuamente pelo ArgoCD), faz-se necessária a definição de uma estratégia declarativa de segredos.

Além do alinhamento ao GitOps, a infraestrutura possui restrições orçamentárias e de hardware severas: o cluster opera em uma **VPS single-node (HostGator NVMe 4: 2 vCPU e 4 GB de RAM)** rodando **k3s**. Soluções pesadas ou com dependência de servidores complexos de cofre comprometem diretamente a estabilidade do nó.

## Alternativas Avaliadas

Foram avaliadas três abordagens consolidadas no ecossistema cloud-native:

| Critério | Sealed Secrets (Bitnami) | SOPS com age (Mozilla) | External Secrets Operator (ESO) |
| :--- | :--- | :--- | :--- |
| **Arquitetura no GitOps** | Nativa. Gera CRDs `SealedSecret` versionados no Git. O controller dentro do cluster descriptografa em `Secret` nativo. | Cifra arquivos YAML no Git. Exige plugin/CMP customizado no ArgoCD Repo Server para descriptografar antes do apply. | Sincroniza segredos de provedores externos (AWS Secrets Manager, GCP SM, Vault) para `Secrets` K8s. |
| **Consumo de Recursos (VPS 4 GB)** | **Muito Baixo** (~15 a 30 MB de RAM, <0.05 vCPU). Controller em Go enxuto e estático. | **Quase Nulo** no cluster em repouso; consome CPU no Repo Server a cada sync do ArgoCD. | **Moderado/Alto** (~100 a 250 MB de RAM) para o operador, mais o consumo do Vault se for self-hosted (+500 MB). |
| **Complexidade Operacional** | **Baixa**. O desenvolvedor necessita apenas do utilitário CLI `kubeseal` e do certificado público (offline). | **Média**. Gerenciamento de chaves privadas age distribuídas entre devs, CI e montadas no container do ArgoCD. | **Alta**. Exige gerenciar serviços externos de cofre ou arcar com custos adicionais de nuvem externa. |
| **Segurança e Superfície de Ataque** | A chave privada reside exclusivamente no cluster (`kube-system`). Apenas chave pública é compartilhada. | A chave privada age precisa residir descriptografada no pod `argocd-repo-server`. | Depende de credenciais de longa duração ou federação OIDC com o provedor de nuvem. |
| **Integração com ArgoCD** | Imediata e transparente. ArgoCD trata `SealedSecret` como qualquer recurso K8s nativo. | Complexa. Exige Sidecars de Config Management Plugin (CMP) ou substituição de binários do ArgoCD. | Transparente para o ArgoCD, mas introduz reconciliação assíncrona entre ESO e o provedor externo. |

## Decisão

Adotar o **Sealed Secrets (Bitnami)** como ferramenta padrão de gestão e entrega de segredos para os clusters da APAE gerenciados pelo APAE-INFRA.

### Justificativas:

1. **Eficiência para o Hardware (VPS 4 GB RAM)**: O controller consome recursos mínimos em repouso e não exige a execução de instâncias dedicadas de servidores de cofre (ex: HashiCorp Vault).
2. **Integração GitOps "Zero-Touch" no ArgoCD**: O ArgoCD não precisa de plugins customizados, sidecars de descriptografia ou chaves privadas montadas no `argocd-repo-server`. O manifesto `SealedSecret` é comitado no Git como qualquer outro manifesto Kubernetes e aplicado diretamente pelo ArgoCD.
3. **Criptografia Assimétrica Segura**: Os desenvolvedores e pipelines utilizam apenas a **chave pública** (certificado `.pem`) para criptografar os dados via CLI `kubeseal`. Ninguém fora do cluster possui capacidade de descriptografar o conteúdo comitado.
4. **Isolamento por Escopo**: Por padrão, adota-se o escopo `strict`, garantindo que um segredo cifrado para determinado recurso e namespace não possa ser descriptografado em outro namespace ou sob outro nome, prevenindo vazamentos entre tenants.

## Papel no Fluxo GitOps

```text
[Desenvolvedor / CI]
        │
        ▼ (Gera Secret K8s local em memória/temporário)
[kubeseal CLI] ◄── [Certificado Público do Cluster]
        │
        ▼ (Cifra assimetricamente)
[SealedSecret YAML]
        │
        ▼ (git commit & push)
[Repositório Git: APAE-INFRA]
        │
        ▼ (Reconciliação declarativa)
[ArgoCD]
        │
        ▼ (Aplica o recurso customizado SealedSecret)
[Kubernetes API]
        │
        ▼ (Detecta evento e descriptografa usando a Chave Privada)
[Sealed Secrets Controller]
        │
        ▼ (Cria/Atualiza)
[Secret K8s Nativo] ◄── [Consumido via envFrom / secretKeyRef pelos Pods]
```

## Governança, Rotação e Backup de Chaves

1. **Backup da Chave Mestra**:
   - O par de chaves mestras do controller reside em um `Secret` no namespace `kube-system` com o label `sealedsecrets.bitnami.com/sealed-secret-key=active`.
   - Um backup criptografado desse `Secret` deve ser mantido de forma segura e offline pelos mantenedores da infraestrutura (fora do Git público), garantindo recuperação em caso de reinstalação total do cluster (Disaster Recovery).
2. **Rotação de Chaves**:
   - O Sealed Secrets Controller suporta rotação automática e periódica de certificados de criptografia.
   - Chaves privadas antigas são mantidas no cluster para leitura e descriptografia contínua de segredos antigos, enquanto a nova chave passa a ser a ativa para novas cifragens.
3. **Escopo Obrigatório**:
   - Todos os manifestos devem utilizar o escopo `strict` (padrão) para evitar que segredos sejam reaproveitados indevidamente entre serviços ou namespaces.

