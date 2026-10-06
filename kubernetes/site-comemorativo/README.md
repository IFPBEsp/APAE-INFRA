# Site Comemorativo — Manifests Base

Este diretório contém os manifests base do **APAE Site Comemorativo**, seguindo o padrão Kustomize adotado no projeto `APAE-INFRA`.

O serviço representa a aplicação do repositório [`apae-site-comemorativo`](https://github.com/IFPBEsp/apae-site-comemorativo).

---

## Estado atual

O serviço **ainda não é implantável** no estado atual.

No momento da criação destes manifests:

- O repositório `apae-site-comemorativo` não possui workflows de CI (`.github/workflows/`) e **não publica imagem no GitHub Container Registry (GHCR)**.
- O objetivo desta entrega é manter a especificação declarativa pronta e padronizada no repositório GitOps, aguardando a disponibilização da imagem.

Por esse motivo, o `Deployment` foi configurado com:

```yaml
replicas: 0
```

Isso garante que o Kubernetes mantenha os recursos registrados sem tentar instanciar Pods de uma imagem inexistente, evitando falhas de `ImagePullBackOff`.

---

## Mapeamento Operacional

As portas, variáveis e configurações foram levantadas diretamente a partir do `Dockerfile`, `docker-compose.yml` e `DOCKER.md` do repositório original:

| Configuração | Valor | Origem | Destino K8s |
| :--- | :--- | :--- | :--- |
| **Porta interna** | `3000` | `Dockerfile` / `docker-compose.yml` | `Deployment` (`containerPort`) e `Service` (`port`/`targetPort`) |
| **Roteamento de path** | `/site-comemorativo` | `next.config.ts` (`basePath`) | Probes (`startup`, `readiness`, `liveness`) |
| **Usuário do container** | `65532:65532` | `Dockerfile` (Distroless non-root) | `securityContext` (`runAsUser`, `runAsGroup`) |
| **Variáveis não sensíveis** | `NODE_ENV`, `PORT`, `HOSTNAME` | `Dockerfile` / `docker-compose.yml` | `ConfigMap` (`site-comemorativo-config`) |

---

## Dependências para Ativação Futura

Para que este serviço possa ser ativado com réplicas ativas (`replicas: 1` ou superior), são necessárias as seguintes etapas externas:

1. **Pipeline de CI e Publicação de Imagem**:
   - Criação de workflow no GitHub Actions do repositório `apae-site-comemorativo` para build e publicação da imagem em `ghcr.io/ifpbesp/apae-site-comemorativo`.
   - Fornecimento dos build arguments (`--build-arg`) obrigatórios consumidos durante o `pnpm build`:
     - `NEXT_PUBLIC_BASE_PATH`: caminho base da aplicação (ex.: `/site-comemorativo`);
     - `NEXT_PUBLIC_URL_APAE`: URL base da aplicação principal da APAE.
2. **Gestão de Segredos (Secrets)**:
   - Definição da estratégia de Secrets para injetar as credenciais sensíveis identificadas no `docker-compose.yml`:
     - `DATABASE_URL` (conexão com o PostgreSQL);
     - `JWT_SECRET`;
     - `BLOB_READ_WRITE_TOKEN`.
3. **Recurso de Banco de Dados e Migrations**:
   - Provisionamento do banco PostgreSQL (tratado como dependência externa);
   - Definição do mecanismo de execução das migrations do Prisma (`pnpm exec prisma migrate deploy`), por exemplo via Kubernetes `Job` ou `initContainer`.
4. **Ingress / Roteamento**:
   - Definição das regras de Ingress no escopo da issue de comunicação entre repositórios.
