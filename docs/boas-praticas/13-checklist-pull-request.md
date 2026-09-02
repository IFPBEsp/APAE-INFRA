# 13. Checklist antes do Pull Request

[← Voltar ao índice](README.md)

Antes de abrir um Pull Request, verificar quando aplicável:

## Segurança

* Nenhum segredo ou credencial foi adicionado;
* Nenhum dado sensível aparece em arquivos ou logs;
* ConfigMaps não contêm dados sensíveis;
* Credenciais permanentes foram evitadas quando existe alternativa mais segura.

## Terraform

* `terraform fmt -check` executado;
* `terraform validate` executado;
* `terraform plan` analisado quando aplicável;
* Arquivos de state não foram adicionados;
* Providers possuem versões definidas;
* `.terraform.lock.hcl` está atualizado quando aplicável;
* Nenhuma alteração destrutiva passou despercebida;
* O state não foi editado manualmente.

## Docker

* Imagem possui versão definida;
* `latest` não é utilizado para produção;
* A imagem não contém segredos;
* Container não executa como root sem justificativa;
* O build contém somente os arquivos necessários;
* Tags de produção não estão sendo sobrescritas;
* Multi-stage build foi utilizado quando aplicável;
* Healthcheck foi considerado quando aplicável.

## Kubernetes / ArgoCD

* Requests e limits foram definidos quando aplicável;
* Probes foram configuradas quando aplicável;
* `startupProbe` foi considerada para aplicações com inicialização lenta;
* As probes possuem parâmetros compatíveis com o comportamento real da aplicação;
* Namespace correto utilizado;
* O namespace `default` não está sendo utilizado sem justificativa;
* `securityContext` foi considerado;
* ConfigMaps e Secrets estão sendo utilizados corretamente;
* Alterações de recursos gerenciados pelo ArgoCD foram realizadas através do Git;
* Políticas de `selfHeal` e `prune` foram consideradas quando aplicável.

## GitHub Actions

* `permissions:` utiliza apenas os privilégios necessários;
* Segredos não são expostos nos logs;
* As actions utilizadas possuem versão definida;
* Actions de terceiros foram revisadas;
* Actions de terceiros utilizadas em workflows sensíveis estão preferencialmente fixadas por SHA completo;
* Alterações de versão ou SHA de Actions foram revisadas antes do merge;
* OIDC foi considerado quando aplicável;
* Workflows reutilizáveis foram considerados quando houver etapas repetidas.

## Observabilidade

* Logs são enviados para `stdout/stderr` quando aplicável;
* A aplicação pode ser identificada nos logs;
* Métricas foram consideradas quando necessárias;
* Health checks estão disponíveis quando aplicável.

## Alterações destrutivas

* Recursos que serão removidos ou substituídos foram identificados;
* Impactos estão descritos no PR;
* Estratégia de recuperação foi considerada;
* Riscos de perda de dados foram analisados.

## Rollback

* Existe estratégia de rollback quando necessária;
* Alterações de banco foram consideradas separadamente;
* Rollback da aplicação não está sendo tratado como rollback automático do banco.

## Geral

* Alteração possui escopo claro;
* Documentação foi atualizada quando necessário;
* PR está vinculado à issue correspondente;
* Decisões arquiteturais relevantes foram documentadas quando necessário.

---
