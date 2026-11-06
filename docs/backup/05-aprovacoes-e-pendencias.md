# 05 — Aprovações e pendências

[← Índice](README.md)

A [revisão documental de 06/11/2026](06-validacao-e-dimensionamento.md) registra verificações técnicas, cálculo conservador de capacidade e ficha de inventário. Não equivale à aprovação do time.

## Registro de decisões do time

Esta seção deve ser atualizada com evidência real de revisão, sem inferir aprovação a partir do merge da documentação. Nenhuma pessoa foi designada automaticamente como operadora de plantão.

| Decisão | Proposta | Aprovação, responsável nominal e data |
| --- | --- | --- |
| Destino primário | R2 Standard privado com restic; B2 avaliado como alternativa | Pendente |
| Orçamento | Medir piloto e aprovar teto, inclusive excedente e restauração | Pendente |
| Segunda cópia | Comparar B2 diário (meta proposta de 26h; uma diária por 7 dias) com Coldline mensal (100 dias) | Pendente; decidir risco de operar com um único destino externo |
| RPO/RTO e retenção | Matriz do documento 02 | Pendente: Infra, squads e gestor dos dados |
| Prioridade de produtos | Ordem de retomada definida pelo gestor | Pendente |
| Operação | Titular Infra e suplente, com cobertura/escala explícita | Pendente: registrar nomes e substituição |
| Validação funcional | Um titular e suplente por produto | Pendente |
| Custódia | Dois responsáveis, cofre institucional independente | Pendente |
| Alertas | E-mail do grupo e canal alternativo, detector externo | Pendente: endereços em registro privado e serviço selecionado |
| Localização e tratamento de dados | Bucket privado, cifragem e avaliação institucional | Pendente: localização aprovada e regras de retenção |
| Recuperação HostGator | Portal/suporte, sem dependência de snapshot | Pendente: protocolo, procedimento e prazo |
| Revisão da estratégia #107 | Revisão técnica Infra, squads e gestor | Pendente: link do PR/ata, revisores e data |

Retenção técnica proposta não determina prazo institucional de guarda de documentos. Conciliar obrigação de preservação e solicitação de exclusão com o gestor dos dados antes de aprovar política; registrar também como dados excluídos serão tratados após uma restauração.

## Backlog para implementação

Itens abaixo são critérios propostos para detalhar a [issue #108](https://github.com/IFPBEsp/APAE-INFRA/issues/108), sem criar ou alterar issues automaticamente.

| Item | Dependência e função responsável | Evidência de conclusão |
| --- | --- | --- |
| Confirmar recuperação do provedor | Infra/HostGator | Protocolo, passos sem SSH, impacto em IP/disco e prazo conhecido |
| Fechar inventário por produto | Squads | Motores, versões, paths/PVCs, blobs externos, tamanhos e responsáveis |
| Fixar datastore e versão k3s | #90 / Infra | Escolha registrada e um ramo do runbook homologado |
| Definir recuperação dos Secrets | #93 / custodiantes | Chaves e fontes recuperáveis fora do cluster, inclusive versões antigas |
| Homologar bootstrap controlado | #91 / Infra | ArgoCD reconstruído sem liberar escrita antes dos dados |
| Provisionar destino e acessos | Infra e administrador da conta | Bucket privado, MFA, tokens restritos e teste de leitura/exclusão |
| Implantar pipeline no host | Infra / Ansible | Timers com timezone, locks, timeouts, staging protegido, dumps e retomada em falha |
| Validar retenção real | Infra | Capturas intradiárias preservadas; dry-run revisado; prune e check sem conflito |
| Implantar observabilidade externa | Observabilidade | Falha e ausência do host detectadas; mensagens recebidas por titular e suplente |
| Validar estimativa inicial na implementação | Infra | Cenários do documento 06 revistos com piloto de 14 dias, operações, duração e orçamento |
| Implantar segunda cópia, se aprovada | Infra com administração independente | B2 ou Coldline escolhido; conjunto completo restaurável sem R2, retenção própria, alertas e credencial ausente da VPS |
| Executar testes isolados | Infra, custodiantes e squads | Relatório do documento 04, desvios corrigidos e RPO/RTO medidos |
| Publicar runbook operacional parametrizado | Infra | Caminhos, versões, comandos homologados e contatos privados localizáveis |

## Condições para encerrar #107

- [ ] Time revisou os documentos e registrou decisões, revisores e data.
- [ ] Inventário identifica cada dependência de dados conhecida; lacunas têm responsável e prazo.
- [ ] Capacidade de recuperação HostGator está confirmada ou sua incerteza foi explicitamente aceita, com alternativa de reconstrução.
- [ ] Destino primário, custo, criptografia, acesso e risco de exclusão foram aprovados.
- [ ] Responsáveis nominais, suplentes, frequência, retenção, prioridade e RPO/RTO foram aprovados.
- [ ] Canal e serviço de alerta externo foram escolhidos.
- [ ] Plano de recuperação/teste foi revisado e backlog #108 foi acordado.

A #107 entrega a estratégia aprovada. A execução dos testes e implantação pertencem à #108; não marcar esses resultados como realizados nesta etapa. As lacunas acima impedem afirmar que toda a estratégia já foi validada, mas não impedem revisar e melhorar esta proposta.
