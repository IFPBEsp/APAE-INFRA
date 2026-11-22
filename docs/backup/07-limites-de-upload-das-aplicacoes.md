# 07 — Limites de upload das aplicações

[← Índice](README.md)

## Escopo e evidências

Pesquisa de código em 06/11/2026, pelas branches padrão indexadas do GitHub, seguida de leitura dos arquivos nos commits abaixo. São limites e integrações definidos no código, não medição de arquivos existentes nem comprovação de configurações em produção. Variáveis, perfis e proxies podem alterar o limite efetivo.

| Produto | Limite encontrado | Destino/dependência identificada | Referência |
| --- | --- | --- | --- |
| APAE Geral | Backend: `max-file-size: 10MB`, `max-request-size: 50MB`; validador de arquivo padrão `10 * 1024 * 1024` bytes; frontend declara 10 MiB | Configuração PostgreSQL e MinIO | [application.yaml](https://github.com/IFPBEsp/APAE/blob/a7cfd5e150375f96dd0f805ad122511f99a84a24/apps/api/src/main/resources/application.yaml), [validador](https://github.com/IFPBEsp/APAE/blob/a7cfd5e150375f96dd0f805ad122511f99a84a24/apps/api/src/main/java/br/org/apae/api/documents/interfaces/validations/ValidFileSize.java), [frontend](https://github.com/IFPBEsp/APAE/blob/a7cfd5e150375f96dd0f805ad122511f99a84a24/apps/apae/src/lib/constants.ts) |
| APAE Atendimento | Backend: arquivo 50MB e requisição 50MB; helper frontend compara o primeiro arquivo com `50 * 1024 * 1024` bytes | Implementações MinIO e S3; serviço S3 é ativado por perfil `prod`, sem comprovar fornecedor efetivo | [application.properties](https://github.com/IFPBEsp/APAE-atendimento/blob/a2c18a97cc39d84ba645cb0b4375d37d28b703c5/backend/atendimento/src/main/resources/application.properties), [helper frontend](https://github.com/IFPBEsp/APAE-atendimento/blob/a2c18a97cc39d84ba645cb0b4375d37d28b703c5/frontend/atendimento-app/src/services/validarTamanhoArquivo.ts), [S3Service](https://github.com/IFPBEsp/APAE-atendimento/blob/a2c18a97cc39d84ba645cb0b4375d37d28b703c5/backend/atendimento/src/main/java/br/org/apae/atendimento/services/storage/s3/S3Service.java) |
| Gestão Escolar | Não localizado limite explícito multipart no arquivo de configuração nem resultados de `MultipartFile` na busca indexada; não concluir que suporta 50 MB ou que não possui arquivos | Configuração PostgreSQL e MinIO presente; uso efetivo precisa ser confirmado | [application.properties](https://github.com/IFPBEsp/APAE-gestao-escolar/blob/75ea3c81faf4fffc096bd8bf6b51dbf376091228/api/src/main/resources/application.properties) |
| Site Comemorativo | Rota POST de TimelinePost exige imagem não vazia, sem teto explícito no handler; modal limita a um arquivo, sem validação de tamanho | Rota envia bytes para Vercel Blob; banco guarda URL | [rota POST](https://github.com/IFPBEsp/apae-site-comemorativo/blob/ad197271db2bea0fd058f718bc0be0fa6308d9b1/src/app/api/TimelinePost/route.ts), [modal](https://github.com/IFPBEsp/apae-site-comemorativo/blob/ad197271db2bea0fd058f718bc0be0fa6308d9b1/src/app/components/media-crud-modal/MediaCrudModal.tsx) |

A busca não é auditoria exaustiva de todos os endpoints, branches ou overrides. O helper frontend do Atendimento verifica apenas o primeiro arquivo recebido; sua existência não prova aplicação universal em todos os formulários. O código do Comemorativo também contém referências de atualização/exclusão a caminhos locais `/uploads`; inventariar eventual conteúdo legado em vez de presumir migração integral para Blob.

## Consequência para NGINX Gateway Fabric

A lembrança de suporte próximo de 50 MB é consistente com o Atendimento e com o limite de requisição do Geral. Porém, 50 MB por requisição não equivale a 50 MB por arquivo em todos os produtos.

No Atendimento, igualar `max-file-size` e `max-request-size` a 50MB deixa o arquivo de tamanho máximo sem margem para campos e cabeçalhos multipart. Para assegurar arquivo de 50 MiB, o squad deve manter o limite por arquivo e aprovar um limite maior para o corpo completo; o Gateway precisa permitir pelo menos esse corpo. O valor exato depende dos metadados e da quantidade permitida de arquivos. Não definir um teto global ilimitado nem elevar os limites sem essa decisão.

A documentação oficial do [NGINX Gateway Fabric](https://docs.nginx.com/nginx-gateway-fabric/traffic-management/client-settings/) apresenta `ClientSettingsPolicy` com `spec.body.maxSize`, aplicável a Gateway ou HTTPRoute. Confirmar API/schema na versão selecionada; preferir política específica de rota quando necessário. No repositório local, não foi encontrada política YAML de tamanho de corpo em `kubernetes/` ou `argocd/` nesta revisão. A configuração permanece proposta, não implementada.

O [estudo de NGINX](../nginx/04-comunicacao-aplicacoes-e-observabilidade.md#20-uploads) já exige considerar overhead multipart. A aplicação e todos os saltos HTTP devem ser testados: no Geral, também há rotas intermediárias Next.js. Aceitação pelo Gateway não assegura aceitação pelo backend.

## Impacto no dimensionamento dos backups

Tamanho máximo por arquivo é um dado de planejamento; não informa quantidade, média ou taxa diária de uploads. É possível obter limite por código, mas o volume real exige inventário do storage. Usar bytes para comparar: 50 MiB são 52.428.800 bytes, enquanto 10 GB decimais são 10.000.000.000 bytes.

| Arquivos distintos de 50 MiB | Conteúdo bruto aproximado |
| --- | --- |
| 20 | 1,05 GB |
| 100 | 5,24 GB |
| 190 | 9,96 GB |
| 200 | 10,49 GB |

Isso considera uma única cópia dos arquivos, sem bancos, datastore, versões antigas, metadados ou folga. Com a margem proposta de 7 GB para planejar uso gratuito, cerca de 133 arquivos de 50 MiB já ocupariam praticamente toda essa margem, antes dos outros componentes. São cenários, não contagem de arquivos existentes.

Arquivos imutáveis e idênticos não precisam ocupar novamente seu tamanho inteiro em cada snapshot restic, mas arquivos novos, substituídos ou removidos e ainda retidos aumentam o espaço. Não multiplicar automaticamente todos os uploads pela quantidade de seleções de dumps, nem presumir redução de JPEG/PDF já comprimidos. Para objeto externo, backup do banco contendo apenas a URL não protege os bytes da imagem/anexo.

Separar bucket de dados ativos e repositório de backup, com credenciais próprias. Se ambos estiverem na mesma conta R2, seus consumos compartilham a franquia; dados ativos e backups no mesmo provedor também mantêm um domínio de falha comum.

## Encaminhamentos

- #107: incorporar estes limites ao inventário e estimar quantidade/média/crescimento por produto; manter tamanho real pendente até haver medição.
- Implementação de entrada HTTP: alinhar arquivo/corpo no Atendimento, limitar explicitamente Comemorativo e definir necessidade real na Gestão Escolar; configurar Gateway por mecanismo suportado.
- #108: testar backups de objetos MinIO/S3/Blob e restauração coordenada com referências no banco; medir bytes físicos retidos.
- Teste HTTP: enviar arquivo abaixo, exatamente no limite de bytes e acima dele, incluindo metadados/múltiplos arquivos quando aceitos; identificar qual camada rejeitou. Não usar documentos reais no teste.
