# Bootstrap, atualização e recuperação do ArgoCD

## 1. Objetivo

Documentar os procedimentos de instalação, atualização, validação, backup e recuperação do ArgoCD no cluster k3s da APAE.

A instalação e as atualizações do ArgoCD são realizadas exclusivamente pelo Ansible, conforme a issue #91.

A coordenação de janelas de manutenção e contingência da VPS permanece no escopo da issue #117.

## 2. Responsabilidades

| Componente | Responsável |
| --- | --- |
| Instalação do Helm | Ansible |
| Instalação e atualização do ArgoCD | Ansible |
| Configuração administrativa e RBAC | Ansible |
| AppProjects e Application raiz | Ansible |
| Applications filhas | ArgoCD |
| Recursos Kubernetes dos produtos | ArgoCD |
| Infraestrutura fundacional | Terraform |

Os manifestos da instalação do ArgoCD não devem ser incluídos em nenhuma Application reconciliada pelo próprio ArgoCD.

## 3. Pré-requisitos

- Cluster k3s instalado e operacional.
- Acesso SSH autorizado à VPS.
- Usuário Ansible com permissões administrativas necessárias.
- Kubeconfig local disponível em `/etc/rancher/k3s/k3s.yaml`.
- API Kubernetes acessível localmente pela VPS.
- Ansible e coleção `kubernetes.core` disponíveis no controlador.
- Arquivo Ansible Vault disponível e descriptografável.
- Versões do Helm, helm-diff, chart e ArgoCD fixadas.

O kubeconfig administrativo não deve ser transferido para o GitHub Actions.

## 4. Bootstrap inicial

A execução deve utilizar o inventário de produção e o playbook `ansible/playbooks/argocd.yml`.

Antes da execução, verificar:

1. Estado do cluster k3s.
2. Disponibilidade da API Kubernetes.
3. Capacidade de memória e CPU da VPS.
4. Existência de backup válido do cluster, quando aplicável.
5. Disponibilidade do Ansible Vault.
6. Compatibilidade entre as versões do Helm, chart e ArgoCD.

Executar o playbook somente após essas verificações.

O fluxo esperado é:

1. Validar os pré-requisitos.
2. Instalar o Helm versionado.
3. Instalar o helm-diff.
4. Instalar o ArgoCD pelo chart oficial.
5. Aguardar os componentes e CRDs.
6. Configurar a senha administrativa.
7. Validar o Secret administrativo.
8. Remover o Secret da senha inicial.
9. Aplicar os AppProjects e a Application raiz.
10. Validar a saúde e a sincronização do ArgoCD.

## 5. Verificações de saúde

Após a instalação, verificar:

- Release Helm no estado `deployed`.
- Application Controller disponível.
- API Server disponível.
- Repository Server disponível.
- Redis disponível.
- CRDs de Application, AppProject e ApplicationSet estabelecidos.
- Ausência de reinicializações anormais.
- Disponibilidade da interface administrativa pelo túnel autorizado.
- Application raiz reconhecida pelo ArgoCD.
- Applications filhas reconciliadas conforme suas políticas.

O bootstrap não deve ser considerado concluído apenas porque o Helm finalizou sem erros.

## 6. Backup antes de atualizações

Antes de atualizar o ArgoCD:

1. Confirmar a existência de um backup recuperável do datastore k3s.
2. Preservar a configuração versionada da release Helm.
3. Registrar as versões atualmente instaladas.
4. Registrar a revisão Git usada pelo bootstrap.
5. Confirmar a disponibilidade do Vault e das credenciais necessárias.
6. Preservar os objetos de bootstrap administrados pelo Ansible.
7. Confirmar que o procedimento de recuperação do k3s está disponível.

O backup do datastore k3s e a recuperação do cluster devem seguir os procedimentos definidos na documentação da issue #90.

Não incluir senhas, tokens, kubeconfigs ou conteúdo de Secrets em evidências compartilhadas.

## 7. Atualização do ArgoCD

As atualizações devem ser realizadas alterando explicitamente as versões fixadas nos defaults da role.

Procedimento:

1. Consultar a documentação de compatibilidade do chart e da aplicação.
2. Ler as notas de versão e identificar mudanças incompatíveis.
3. Atualizar os valores versionados.
4. Validar a renderização dos manifests Helm.
5. Revisar alterações em CRDs, RBAC e recursos Kubernetes.
6. Confirmar backup anterior à atualização.
7. Executar o playbook Ansible.
8. Validar a saúde dos componentes.
9. Confirmar a persistência da senha administrativa.
10. Verificar o estado das Applications existentes.
11. Reexecutar o playbook para avaliar a idempotência.

Atualizações não devem utilizar automaticamente a versão mais recente do chart.

## 8. Recuperação

### 8.1 Falha na instalação ou atualização

Se ocorrer falha:

1. Interromper novas alterações no cluster.
2. Identificar a etapa que falhou.
3. Consultar o estado da release Helm e dos componentes.
4. Verificar se o rollback automático foi executado.
5. Conferir a saúde do cluster.
6. Avaliar a necessidade de retornar à versão anterior.
7. Registrar o incidente e sua resolução.

### 8.2 Recuperação dos objetos de bootstrap

Os arquivos `project.yaml`, `project-infra.yaml` e `app-of-apps.yaml` são administrados pelo Ansible.

Se esses recursos forem removidos ou alterados indevidamente, a recuperação deverá ser realizada pela reexecução controlada do playbook.

Não recuperar esses objetos por meio de uma Application reconciliada pelo próprio ArgoCD.

### 8.3 Recuperação após perda do cluster

A recuperação depende da disponibilidade de um backup válido do k3s e das configurações versionadas do APAE-INFRA.

Após restaurar ou reprovisionar o cluster:

1. Validar a saúde do k3s.
2. Confirmar a restauração dos dados e Secrets necessários.
3. Verificar a disponibilidade da API Kubernetes.
4. Recuperar ou reinstalar o ArgoCD pelo Ansible, conforme o estado do cluster.
5. Restaurar os objetos de bootstrap administrados pelo Ansible.
6. Validar as credenciais e o RBAC.
7. Verificar o estado das Applications.
8. Confirmar que os workloads estão reconciliados com o Git.

A reinstalação do ArgoCD não substitui a recuperação de dados persistentes dos produtos.

## 9. Idempotência

O playbook deve ser executado novamente após uma instalação bem-sucedida.

A segunda execução não deverá:

- Reinstalar o Helm sem necessidade.
- Atualizar o chart sem alteração de versão ou valores.
- Redefinir a senha administrativa com o mesmo hash.
- Recriar AppProjects sem necessidade.
- Modificar a Application raiz sem alteração de configuração.
- Reiniciar componentes desnecessariamente.

Alterações observadas deverão ser investigadas e corrigidas antes de considerar o critério de idempotência atendido.

## 10. Segurança

- Não expor publicamente a interface administrativa do ArgoCD no bootstrap inicial.
- Utilizar acesso administrativo via port-forward autorizado.
- Armazenar o hash administrativo em Ansible Vault.
- Não incluir credenciais em texto claro no Git.
- Não divulgar Secrets em logs ou artefatos.
- Utilizar acesso Git somente leitura.
- Aplicar permissões mínimas nos AppProjects.
- Manter separados os recursos administrados pelo Ansible e pelo ArgoCD.

## 11. Evidências

Registrar evidências sanitizadas de:

- Execução bem-sucedida do Ansible.
- Versões instaladas.
- Estado da release Helm.
- Saúde dos componentes.
- Disponibilidade dos CRDs.
- Configuração dos AppProjects.
- Application raiz.
- Sincronização da Application de teste.
- Segunda execução idempotente.
- Procedimento de recuperação validado.

## 12. Evoluções futuras

A arquitetura prevê clusters independentes para desenvolvimento e produção, cada um com sua própria VPS e instância do ArgoCD.

Essa separação não integra o escopo inicial da issue #91.

O bootstrap atual acompanha a branch `main` do APAE-INFRA, enquanto a futura separação dos ambientes deverá restringir a descoberta das Applications de cada cluster.

As decisões relativas à promoção de imagens entre homologação e produção permanecem na issue #106.
