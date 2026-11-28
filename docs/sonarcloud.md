# Análise Estática com SonarQube Cloud (SonarCloud)

> **Repositório mantenedor:** [`IFPBEsp/APAE-INFRA`](https://github.com/IFPBEsp/APAE-INFRA)
> **Documentação técnica dos workflows:** [Workflows Reutilizáveis de Análise Estática](workflows/reusable-sonarqube.md)
> **Issues relacionadas:** #172 (SonarCloud) e #34 (SonarQube self-hosted)

## 1. Contexto e Objetivo

A issue #34 prevê a adoção do SonarQube self-hosted para análise estática dos repositórios de produto da APAE. Como o servidor destinado à hospedagem da instância encontra-se indisponível no momento, adotou-se o **SonarQube Cloud (SonarCloud)** como solução imediata e sem dependência de infraestrutura própria, aproveitando que todos os repositórios da organização `IFPBEsp` são públicos.

Esta configuração entrega:

- histórico contínuo de qualidade, dívida técnica e cobertura;
- **decoração automática de Pull Requests** diretamente no GitHub;
- bloqueio automático de merge via **Quality Gate**;
- visibilidade de métricas de cobertura para acompanhamento a cada virada de sprint;
- compatibilidade de interface nos workflows para migração futura ao SonarQube self-hosted (#34).

---

## 2. Configuração da Organização e Permissões

### 2.1. Criação e Vínculo com o GitHub

1. Acesse [SonarCloud](https://sonarcloud.io) utilizando uma conta com privilégio de **Owner** na organização `IFPBEsp` no GitHub.
2. Crie a organização no SonarCloud vinculada à organização GitHub `IFPBEsp` (chave sugerida: `ifpbesp`).
3. Durante a instalação da **SonarCloud GitHub App**, selecione **Only select repositories** e habilite **exclusivamente os quatro repositórios de produto**:
   - `IFPBEsp/APAE`
   - `IFPBEsp/APAE-gestao-escolar`
   - `IFPBEsp/APAE-atendimento`
   - `IFPBEsp/apae-site-comemorativo`

> [!IMPORTANT]
> Não instale a GitHub App no `APAE-INFRA` nem em outros repositórios não-produto, seguindo o princípio do menor privilégio.

### 2.2. Acesso Administrativo (DevOps e QA)

Para garantir governança compartilhada entre infraestrutura e qualidade:

- Membros das squads **DevOps** e **QA** devem possuir permissão administrativa na organização `ifpbesp` do SonarCloud (**Administration > Permissions** e grupos correspondentes):
  - **DevOps:** administração da organização, criação/ajuste de projetos, gestão de tokens de integração e acompanhamento da saúde das pipelines.
  - **QA:** administração de **Quality Gates**, **Quality Profiles**, regras de análise e definição dos critérios de aprovação/cobertura das sprints.
- Registre no próprio controle de membros do SonarCloud (ou equipe GitHub sincronizada) quais usuários/grupos possuem o papel **Administer Organization** e **Administer Quality Gates**, evitando dependência de uma única conta pessoal.

---

## 3. Projetos, Monorepo e Desativação da Análise Automática

### 3.1. Projetos por Aplicação (Suporte a Monorepo)

Repositórios com mais de uma aplicação devem ter **um projeto SonarCloud distinto por aplicação**, configurados via **Setup a monorepo** durante o import no SonarCloud:

| Repositório | Aplicação | Diretório | Stack | Project Key Sugerida |
| --- | --- | --- | --- | --- |
| `IFPBEsp/APAE` | Backend API | `apps/api` | Java 21 / Maven | `IFPBEsp_APAE_api` |
| `IFPBEsp/APAE` | Frontend Web | `apps/apae` | Node 22 / TS | `IFPBEsp_APAE_frontend` |
| `IFPBEsp/APAE-gestao-escolar` | Backend | Subdiretório backend | Java / Maven | `IFPBEsp_APAE-gestao-escolar_backend` |
| `IFPBEsp/APAE-gestao-escolar` | Frontend | Subdiretório frontend | Node / TS | `IFPBEsp_APAE-gestao-escolar_frontend` |
| `IFPBEsp/APAE-atendimento` | Backend | `backend/atendimento` | Java / Maven | `IFPBEsp_APAE-atendimento_backend` |
| `IFPBEsp/APAE-atendimento` | Frontend | `frontend/atendimento-app` | Node / TS | `IFPBEsp_APAE-atendimento_frontend` |
| `IFPBEsp/apae-site-comemorativo` | Portal / Frontend | `.` | Node 22 / TS | `IFPBEsp_apae-site-comemorativo` |

*(Caso um repositório adote chaves geradas automaticamente pelo SonarCloud no formato `<org>_<projeto>`, basta informar a chave exata gerada no input `project-key` do workflow chamador.)*

### 3.2. Desativação Obrigatória da Análise Automática

Em **cada projeto** criado no SonarCloud:

1. Acesse **Administration > Analysis Method**.
2. Desative **Automatic Analysis** (marque como **Off**).
3. Selecione o método **With GitHub Actions**.

A desativação da Análise Automática é obrigatória pelos seguintes motivos:

- A análise automática do SonarCloud conflita com análises enviadas via GitHub Actions (gerando corridas e comentários duplicados no PR).
- A análise automática **não processa relatórios de cobertura** gerados no CI (JaCoCo XML e LCOV) nem executa compilação Maven para análise profunda de bytecode Java.

### 3.3. Branch Principal

Garanta que a **Main Branch** de cada projeto no SonarCloud esteja alinhada com a branch principal de desenvolvimento/integração utilizada no repositório (`dev` ou `main`, conforme o fluxo adotado pelo time). A definição correta da *Main Branch* é indispensável para o cálculo correto de *New Code* e *Quality Gate* nos Pull Requests.

---

## 4. Gestão do `SONAR_TOKEN` e Boas Práticas de Segredos

Seguindo [Boas Práticas — Gestão de Segredos e Credenciais](boas-praticas/02-segredos-e-credenciais.md):

- **Nunca** versionar tokens em `pom.xml`, `sonar-project.properties`, workflows YAML ou scripts.
- O `SONAR_TOKEN` deve ser armazenado exclusivamente em **GitHub Actions Secrets**:
  - **Opção recomendada (menor privilégio):** gerar um *Project Analysis Token* por projeto (ou token de análise da organização) e cadastrar `SONAR_TOKEN` em **Settings > Secrets and variables > Actions** de cada um dos quatro repositórios de produto; ou
  - **Alternativa centralizada:** cadastrar `SONAR_TOKEN` como **Organization Secret** na `IFPBEsp` com política **Selected repositories** restrita apenas a `APAE`, `APAE-gestao-escolar`, `APAE-atendimento` e `apae-site-comemorativo`.
- **Relação com Terraform (#88):** atualmente o módulo Terraform em [`terraform/environments/github`](../terraform/environments/github/README.md) gerencia apenas *Branch Protection*, *Labels* e *Environments*, com a GitHub App restrita às permissões de `Administration`, `Issues`, `Environments` e `Metadata`. Portanto, o provisionamento de `SONAR_TOKEN` é mantido fora do estado Terraform até que a gestão de *Actions Secrets* seja formalmente incorporada ao escopo da #88.

---

## 5. Quality Gate e Decoração de Pull Request

### 5.1. Plano Gratuito / OSS e Definição com QA

Para repositórios públicos no SonarCloud:

- Repositórios públicos open-source contam com análise ilimitada de linhas de código, análise de branches e decoração de PR sem custo.
- No plano **OSS / Free para projetos públicos**, caso a organização tenha criação de Quality Gates customizadas habilitada, a squad de QA pode definir uma Quality Gate específica para a APAE. Caso a conta esteja restrita ao plano Free padrão sem permissão de criação de Quality Gates customizadas, utiliza-se a Quality Gate padrão **`Sonar way`**, registrando essa decisão no projeto.
- A Quality Gate **`Sonar way`** já implementa a metodologia **Clean as You Code**, avaliando estritamente **New Code** (código alterado/adicionado no PR ou período):
  - Cobertura em código novo >= **80%**
  - Linhas duplicadas em código novo <= **3%**
  - **0** novos problemas (*issues*) abertos em confiabilidade, segurança e manutenibilidade (conceito **A**)
  - **100%** dos *Security Hotspots* em código novo revisados

> [!NOTE]
> Em repositórios que ainda não possuem cobertura consolidada no código legado (ou em transição como o `apae-site-comemorativo`), o foco em **New Code** evita que débitos antigos bloqueiem entregas atuais, enquanto força que todo código novo entre testado e limpo. Caso a cobertura em código novo precise de uma rampa gradual inicial (ex.: 50% -> 80%), isso deve ser validado com QA no painel do SonarCloud.

### 5.2. Bloqueio de CI e Decoração de PR

- **Bloqueio de CI:** ambos os workflows reutilizáveis passam `-Dsonar.qualitygate.wait=true`. Se a Quality Gate retornar `ERROR` (`FAILED`), o job no GitHub Actions falha e impede o merge quando configurado como *required status check* na branch protection.
- **Decoração de PR:** com a GitHub App do SonarCloud instalada e o workflow disparado em `pull_request`, o SonarCloud publica automaticamente:
  - um *Check Run* (`SonarCloud Code Analysis`) com o status da Quality Gate;
  - um comentário resumo diretamente no Pull Request com métricas de *New Code* (bugs, vulnerabilidades, code smells, cobertura e duplicações) e link direto para os achados.

---

## 6. Interpretação dos Resultados

No painel do SonarCloud e no comentário do PR, os indicadores seguem estas definições:

| Métrica | O que avalia | Como agir quando reprova |
| --- | --- | --- |
| **Reliability (Bugs)** | Falhas lógicas, nulos não tratados, vazamentos de recursos, erros de runtime prováveis | Corrigir antes do merge; todo bug novo degrada o rating abaixo de `A` |
| **Security (Vulnerabilities)** | Vulnerabilidades exploráveis no código (injeção, desserialização insegura, exposição de dados) | Correção obrigatória; avaliar em conjunto com os achados do [Semgrep SAST](workflows/reusable-sast-semgrep.md) |
| **Maintainability (Code Smells)** | Complexidade ciclomática alta, código morto, duplicação estrutural, violações de boas práticas | Refatorar o trecho novo ou justificar falso positivo com revisão no SonarCloud |
| **Security Hotspots** | Trechos sensíveis à segurança que exigem revisão humana (ex.: regex complexa, criptografia, permissões) | Acessar o hotspot no SonarCloud e marcar como *Safe* (com justificativa) ou *Fixed* |
| **Coverage** | Percentual de linhas e condições cobertas por testes automatizados (JaCoCo XML / LCOV) | Adicionar testes unitários/integração para cobrir as novas linhas adicionadas no PR |
| **Duplications** | Blocos de código idênticos ou quase idênticos repetidos | Extrair helpers, componentes ou funções compartilhadas |

### Diferença entre *New Code* e *Overall Code*

- **New Code:** alterações introduzidas no PR ou desde o período de referência configurado. É o alvo principal da Quality Gate (*Clean as You Code*).
- **Overall Code:** fotografia completa do repositório inteiro (incluindo código legado). Utilizada para acompanhar a evolução histórica e a taxa global de cobertura nas reuniões de virada de sprint.

---

## 7. Acompanhamento na Virada de Sprint

Como os repositórios da organização `IFPBEsp` são públicos, os dashboards do SonarCloud são **acessíveis publicamente** sem necessidade de licença por usuário de visualização.

### 7.1. Dashboard e Badges

- **Painel consolidado da organização:** acesse `https://sonarcloud.io/organizations/ifpbesp/projects` durante a revisão de sprint para visualizar lado a lado a cobertura geral, cobertura em código novo, status da Quality Gate e dívida técnica de todas as aplicações.
- **Badges no README:** cada projeto disponibiliza badges dinâmicos (Coverage e Quality Gate Status) em **Project Information > Get project badges**.

### 7.2. Extração Automatizada para Relatório de Sprint

Para extrair as taxas exatas de cobertura (`coverage`, `line_coverage`, `branch_coverage`, `new_coverage` e `alert_status`) de todos os projetos via API pública do SonarCloud (para projetos públicos, não requer autenticação):

```bash
projects=(
  "IFPBEsp_APAE_api"
  "IFPBEsp_APAE_frontend"
  "IFPBEsp_APAE-gestao-escolar_backend"
  "IFPBEsp_APAE-gestao-escolar_frontend"
  "IFPBEsp_APAE-atendimento_backend"
  "IFPBEsp_APAE-atendimento_frontend"
  "IFPBEsp_apae-site-comemorativo"
)

for key in "${projects[@]}"; do
  echo "=== ${key} ==="
  curl -fsSL "https://sonarcloud.io/api/measures/component?component=${key}&metricKeys=alert_status,coverage,line_coverage,branch_coverage,new_coverage" \
    | python3 -m json.tool
done
```

Sugere-se registrar os valores extraídos (`coverage` geral e `new_coverage` da sprint) na ata ou issue de fechamento da sprint junto com o link do dashboard do projeto.

---

## 8. Migração Futura para o SonarQube Self-Hosted (#34)

A arquitetura parametrizada garante transição direta quando o servidor self-hosted da issue #34 voltar a ficar disponível:

1. Provisionar o servidor SonarQube self-hosted e criar os projetos equivalentes para as aplicações da APAE.
2. Gerar os novos tokens na instância self-hosted e atualizar o secret `SONAR_TOKEN` nos repositórios de produto.
3. Nos arquivos `.github/workflows/sonar.yml` dos repositórios consumidores:
   - Informar `sonar-host-url: "https://<host-sonarqube-interno>"` (ou cadastrar o secret `SONAR_HOST_URL`);
   - Remover ou definir `organization: ""`;
   - Ajustar `project-key` apenas se as chaves no servidor self-hosted forem diferentes.
4. Desinstalar ou desativar a integração dos repositórios na organização `ifpbesp` do SonarCloud após validar a primeira execução estável no self-hosted.

Nenhuma lógica de build, cobertura ou espera de Quality Gate dos workflows reutilizáveis no `APAE-INFRA` precisa ser reescrita para essa transição.
