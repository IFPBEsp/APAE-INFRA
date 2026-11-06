# Estratégia de backup e recuperação

**Issue:** [#107](https://github.com/IFPBEsp/APAE-INFRA/issues/107). **Status:** proposta para revisão do time. **Data de referência:** 05/11/2026. Nenhum backup, restauração ou acesso à VPS foi executado nesta entrega documental.

## Leitura e artefatos

1. [Estratégia, provedor e comparação de armazenamento](01-estrategia-e-armazenamento.md).
2. [Inventário, métodos, frequência e objetivos](02-matriz-de-protecao.md).
3. [Operação, segurança e recuperação](03-operacao-e-recuperacao.md).
4. [Plano de teste de restauração](04-plano-de-testes.md).
5. [Aprovações e pendências de implementação](05-aprovacoes-e-pendencias.md).
6. [Validação documental, dimensionamento e ficha de inventário](06-validacao-e-dimensionamento.md).
7. [Limites de upload e integrações das aplicações](07-limites-de-upload-das-aplicacoes.md).

## Proposta para deliberação

Adotar restic com criptografia no cliente e bucket privado R2 Standard como destino primário externo à VPS. Planejar início na franquia gratuita com retenção curta de 7 dias e cenário de referência de aproximadamente 5 GB retidos, conforme premissas do documento 06. Não há dados de produção; a estimativa fundamenta o estudo e será validada no piloto da #108. Definir resposta ao crescimento antes da produção. Usar ferramentas nativas para gerar backups consistentes dos bancos e do datastore antes do envio. Um snapshot de máquina, se disponível, é complementar.

Avaliar Backblaze B2 como alternativa ao destino primário ou segunda cópia independente diária, aproveitando a franquia de 10 GB se o histórico retido couber nos limites. Comparar com GCP Coldline para uma cópia de longo prazo em conjuntos autossuficientes com retenção mínima proposta de 100 dias. A escolha da segunda camada não está aprovada nem implementada. A proposta inicial com apenas um destino externo deixa risco residual de exclusão ou comprometimento da conta de backup; o time deve decidir sobre a segunda cópia antes da entrada em produção.

## Limites e dependências

- A [#86 e seu levantamento](../terraform/06-conclusao-e-proximos-passos.md) estabelecem operações HostGator pelo Portal/suporte, Ansible para host/k3s/bootstrap e ArgoCD para recursos Kubernetes atribuídos às Applications.
- A [#87](https://github.com/IFPBEsp/APAE-INFRA/issues/87) trata do state Terraform, separado deste repositório de backups. Sua recuperação pode ser necessária para recursos externos, mas não restaura dados das aplicações.
- A [#90](https://github.com/IFPBEsp/APAE-INFRA/issues/90) deve fixar versão e datastore do k3s; a [#91](https://github.com/IFPBEsp/APAE-INFRA/issues/91), o bootstrap ArgoCD; a [#93](https://github.com/IFPBEsp/APAE-INFRA/issues/93), as chaves e o fluxo de Secrets.
- A [#108](https://github.com/IFPBEsp/APAE-INFRA/issues/108) implementará e homologará backups, alertas e restauração. Comandos desta documentação são modelos operacionais que precisam de parâmetros e teste isolado, não scripts prontos para produção.
- Não há inventário remoto confirmado. Ausência de PVC nos manifests base não comprova ausência de dados persistentes. Serviços externos também precisam de plano de recuperação.

## Critérios de aceite da issue #107

| Critério | Evidência documental | Situação |
| --- | --- | --- |
| Capacidades e limitações do provedor | Documento 01, com separação entre evidência pública e confirmação contratual | Documentado; confirmações específicas pendentes |
| Dados, dependências e material de restauração | Matriz no documento 02 | Levantamento inicial; inventário operacional pendente |
| Ferramentas, destino, criptografia e acesso | Documentos 01 e 03 | Propostos |
| Responsáveis, frequência, retenção e RPO/RTO aprovados | Documentos 02 e 05 | Aguardando aprovação nominal do time |
| Recuperação e teste documentados | Documentos 03 e 04 | Propostos; teste não executado |
| Revisão e pendências identificadas | Documento 05 | Pendências registradas; revisão não realizada |

Não encerrar a issue como estratégia aprovada apenas pela existência destes arquivos. Registrar decisões e revisores após a discussão do time.
