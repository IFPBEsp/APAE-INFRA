# 04 — Plano de teste de restauração

[← Índice](README.md)

## Objetivo e preparação

Demonstrar recuperação sem acesso à VPS original e medir as metas da matriz. Teste de integridade ou download bem-sucedido não é evidência suficiente de recuperação funcional. **Status: plano proposto, nenhuma execução realizada.**

A #108 deve preparar uma VPS/VM separada, com recursos comparáveis e rede isolada. Namespace diferente no cluster de produção não é isolamento de desastre. Usar dados sintéticos inicialmente; dados reais exigem acesso restrito, cifragem, autorização institucional e descarte registrado. Bloquear saída por padrão, permitindo apenas destinos indispensáveis; usar DNS privado, mail sink e mocks de integrações. Não publicar rotas ou emitir mensagens reais. Credencial de teste deve ter leitura dos backups, sem poder apagar produção.

Registrar volume, banda, hardware, versões, commit, snapshot, custos previstos e teto de duração. Obter acesso ao cofre com o suplente antes de iniciar. Congelar prune durante o ensaio e nunca interromper a VPS de produção para simular sua perda.

## Casos e resultados esperados

| ID | Cenário | Execução e evidência exigida |
| --- | --- | --- |
| T01 | Perda completa da VPS | Recuperar pelo documento 03, sem ler o host original; demonstrar cluster, Secrets, bancos, arquivos e fluxos funcionais |
| T02 | Datastore efetivamente escolhido | Restaurar SQLite ou etcd ou externo na versão fixada; validar token, API, nós, recursos e acesso administrativo |
| T03 | Consistência de negócio | Criar registros/anexos sentinela antes e depois do ponto de captura; validar vínculo banco/arquivo, contagens e checksums no conjunto recuperado |
| T04 | Exclusão/corrupção recente | Recuperar um conjunto mais antigo em ambiente vazio e demonstrar ausência da corrupção; medir perda adicional |
| T05 | Falha de backup | Simular credencial inválida e erro de dump em ambiente de teste; nenhum conjunto parcial pode ser declarado sucesso; alerta chega ao canal correto |
| T06 | Ausência de execução | Parar apenas o timer de teste e simular VPS ausente; detector externo alerta sem depender do cluster |
| T07 | Custódia e rotação | Suplente recupera senha, token e chaves sem o titular; restaurar backup anterior à rotação com o material correto |
| T08 | Retenção e permissões | Em bucket descartável, ensaiar dry-run, prune/check, bloqueio de acesso público e limites reais de cada credencial; não apagar objetos de produção |
| T09 | Corrupção no repositório | Em cópia descartável, alterar/remover objeto de teste e comprovar detecção de integridade e escalonamento |
| T10 | Coldline, se aprovado | Recuperar conjunto autossuficiente sem R2; medir retrieval, transferência, tempo e custo; validar retenção de 100 dias |
| T11 | Reconstrução por GitOps | Cluster vazio, sem datastore antigo; restaurar chaves, bootstrap, volumes e dados, validando que Git sozinho não é tratado como backup |
| T12 | Controle de recursos | Medir pausa de escrita, CPU/RAM/disco e duração de backup/restauração sob volume representativo; comprovar margem no host |
| T13 | B2, se aprovado | Recuperar snapshots sem R2 nem VPS original; validar manifesto, retenção, permissões, alerta de cópia ausente, meta de 26h e custo de download/checks |

Para serviços ainda não implantados, registrar `não executado — dependência pendente`, sem declarar aprovação. Não testar motores hipotéticos como se fossem usados em produção.

## Medição e aceite

Registrar `t0` como início simulado da interrupção, `tp` como ponto consistente recuperado e `tf` como liberação funcional. `RPO observado = t0 - tp`; `RTO observado = tf - t0`. Cronometrar também detecção, obtenção do host, download, datastore, bancos, volumes e validação. Se a obtenção do host for simulada, informar tempo excluído e não declarar o RTO global comprovado.

Aceitar somente se os componentes obrigatórios do manifesto forem recuperados, checksums e validações de negócio passarem, acesso público e integrações reais permanecerem bloqueados durante o teste, alertas chegarem ao titular/suplente e as metas aprovadas forem atendidas. Falhas geram correção e novo ensaio do cenário afetado; não transformar meta em aprovação retroativa.

## Frequência e relatório

Executar ensaio completo antes da produção e trimestralmente; mensalmente, restaurar amostra de banco e arquivo. Repetir cenários afetados após troca de datastore, versão principal, storage, ferramenta de Secrets, chaves ou procedimento de backup. Check semanal e leitura mensal seguem documento 03.

Modelo de relatório, sem dados pessoais ou segredos:

| Campo | Preenchimento na execução |
| --- | --- |
| Data, executor e revisor | Pendente |
| Cenários e componentes | Pendente |
| Ambiente isolado e controles de rede | Pendente |
| Commit, versões, snapshot e manifesto | Pendente |
| Volume e banda medidos | Pendente |
| t0, tp, tf e tempos por etapa | Pendente |
| RPO/RTO alvo e observado | Pendente |
| Checksums, contagens e fluxos validados | Pendente |
| Alertas recebidos e confirmação | Pendente |
| Custo previsto/real e limites | Pendente |
| Resultado, desvios e ações com responsável/prazo | Pendente |
| Descarte dos dados e ambiente, revogação das credenciais | Pendente |

Guardar evidências sensíveis em local institucional restrito, referenciando no PR apenas relatório sanitizado. Remover ambiente e dados de teste, revogar credenciais temporárias e verificar que timers de produção continuam ativos após o ensaio.
