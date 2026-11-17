# ADR 004 — Escolha da ferramenta de SCA e política de exceções

## Status

Aceito

## Contexto

Os repositórios de aplicação da APAE (`APAE`, `APAE-gestao-escolar`, `APAE-atendimento` e `apae-site-comemorativo`) utilizam diferentes ecossistemas de dependências:

- **Maven (`pom.xml`)**: Java / Spring Boot (`APAE/apps/api`, `APAE-gestao-escolar/api`, `APAE-atendimento/backend/atendimento`);
- **pnpm (`pnpm-lock.yaml`)**: Node.js / TypeScript (`APAE/apps/apae`, `APAE-atendimento/frontend/atendimento-app`, `apae-site-comemorativo`);
- **npm (`package-lock.json`)**: Node.js / JavaScript (`APAE-gestao-escolar/app`).

Atualmente, a única verificação de vulnerabilidades existente nos repositórios é o scan de vulnerabilidades de imagens Docker com Trivy no pipeline de build e publicação (`docker-build-publish-image.yml` — issue #35), que é executado apenas **após o merge** na branch de release e sobre a imagem OCI final.

Com isso:

1. Uma dependência vulnerável introduzida por um desenvolvedor em um Pull Request só é detectada após o PR já ter sido aprovado e mergeado.
2. A falha é reportada tardiamente, bloqueando a publicação da imagem em produção e exigindo correções emergenciais em branches principais.

Para aplicar a prática de *Shift-Left Security* (antecipação de verificações de segurança), é necessário introduzir um workflow reutilizável de **SCA (Software Composition Analysis)** executado preventivamente durante o ciclo de vida dos Pull Requests.

Issue relacionada:

```text
APAE-INFRA#68 — [CI] Criar workflow reutilizável de verificação de dependências vulneráveis (SCA) para os repositórios da APAE
```

## Opções Consideradas

### 1. Trivy em modo Filesystem (`fs`) via `aquasecurity/trivy-action`

- **Prós**:
  - Já padronizado e adotado na organização APAE no workflow reutilizável de imagens (`docker-build-publish-image.yml`), garantindo consistência na base de dados de CVEs e políticas de severidade.
  - Suporte nativo e maduro aos manifestos e lockfiles dos três ecossistemas em escopo (`pom.xml`, `pnpm-lock.yaml`, `package-lock.json`).
  - Geração nativa de relatórios no formato SARIF compatíveis com a aba *Security* do GitHub (*Code Scanning*).
  - Suporte nativo a arquivo de exceções versionado (`.trivyignore`), com capacidade de especificar justificativas e prazos de validade (`exp:YYYY-MM-DD`).
  - Execução independente de APIs externas proprietárias ou serviços pagos.
  - Suporte a filtros como `--ignore-unfixed` e níveis de severidade configuráveis (`HIGH,CRITICAL`).
- **Contras**:
  - Por analisar o filesystem completo, reporta todas as vulnerabilidades existentes no diretório alvo, e não apenas o delta incremental do diff do PR (embora anote os arquivos modificados no PR via SARIF).

### 2. GitHub Dependency Review Action (`actions/dependency-review-action`)

- **Prós**:
  - Projetada especificamente para PRs do GitHub; analisa o diff e destaca apenas as dependências adicionadas ou alteradas no PR.
  - Gratuita para repositórios públicos.
- **Contras**:
  - Depende do GitHub Dependency Graph estar processando perfeitamente os manifestos na nuvem do GitHub.
  - Não exporta SARIF diretamente para a aba *Security -> Code Scanning Alerts* com a mesma riqueza e independência que o Trivy.
  - Mecanismo de supressão de vulnerabilidades (`allow-ghsas`) não suporta nativamente expiração por data no próprio arquivo de configuração.
  - Divergência de ferramentas e bancos de vulnerabilidades entre o scan de dependências em PR e o scan de imagens Docker em post-merge.

### 3. Google OSV-Scanner (`google/osv-scanner-action`)

- **Prós**:
  - Focado exclusivamente em banco de dados OSV.dev de código aberto.
  - Suporta lockfiles comuns.
- **Contras**:
  - Ferramenta adicional a ser mantida, quebrando a padronização já estabelecida com Trivy no APAE-INFRA.
  - Menor ecossistema de integrações pré-configuradas para Step Summaries e geração SARIF em comparação ao Trivy.

## Decisão

Adotar o **Trivy em modo Filesystem (`scan-type: 'fs'`)** via action oficial `aquasecurity/trivy-action` como ferramenta oficial de SCA para os repositórios da APAE.

A arquitetura do workflow reutilizável compreende:

1. **Verificação nos Pull Requests**: Análise estática dos manifestos e lockfiles Maven, pnpm e npm no diretório informado pelo chamador.
2. **Severidade e bloqueio**: Política padrão bloqueando o PR em severidades `HIGH,CRITICAL`, ignorando vulnerabilidades sem correção disponível (`ignore-unfixed: true`), alinhada com o scan de imagem já vigente.
3. **Publicação na aba Security (SARIF)**: Geração de arquivo SARIF e upload via `github/codeql-action/upload-sarif`, permitindo visualização integrada dos alertas na aba *Security* do GitHub e anotações nos arquivos do PR.
4. **Step Summary e Bloqueio**: Exibição da tabela detalhada no resumo da execução do GitHub Actions (`GITHUB_STEP_SUMMARY`) e encerramento com `exit-code: 1` quando houver violações não tratadas.
5. **Política de Exceções**: Adoção do arquivo `.trivyignore` versionado na raiz do repositório da aplicação, com formato padronizado contendo ID da vulnerabilidade, data limite de expiração (`exp:YYYY-MM-DD`) e justificativa técnica.

## Consequências

### Positivas

- **Consistência**: Toda a organização APAE utiliza a mesma engine de segurança (Trivy), evitando discrepâncias entre o que passa no PR e o que é bloqueado na publicação da imagem.
- **Shift-Left**: Vulnerabilidades são barradas antes do merge na branch principal.
- **Rastreabilidade de Exceções**: Exceções são registradas via Git, revisadas em PR, com prazo determinado e expiração automática controlada pelo Trivy.
- **Visibilidade Centralizada**: Resultados acessíveis tanto no log do PR quanto na aba de segurança nativa do GitHub.

### Negativas / Mitigações

- Repositórios legados com vulnerabilidades preexistentes podem ter PRs bloqueados caso essas dependências estejam no caminho analisado.  
  *Mitigação*: Uso do mecanismo de `.trivyignore` com prazos pré-acordados e tickets de débito técnico criados para atualização gradativa com Renovate (#84).
