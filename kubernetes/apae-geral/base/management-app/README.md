# management-app

O `management-app` faz parte do repositório APAE em:

```text
apps/management-app
```

Os manifests base são mantidos neste diretório para preservar a estrutura esperada da aplicação no Kubernetes.

## Estado atual

O serviço ainda não é implantável.

No momento da criação destes manifests:

- não existe Dockerfile para o `management-app`;
- não existe imagem publicada no GHCR;
- o serviço não está presente nos `docker-compose.yml` utilizados como fonte operacional para esta issue;
- portanto, não há porta de container, variáveis de ambiente ou health checks confirmados por essas fontes.

Por esse motivo, nenhuma configuração operacional não confirmada será assumida neste diretório.

## Porta

O serviço não está presente nos `docker-compose.yml` usados como fonte desta issue.

A porta `3000` declarada no `Service` foi obtida da documentação atual do próprio
`management-app`, que executa a aplicação Next.js em `localhost:3000`.

Esse valor deverá ser revalidado quando o Dockerfile e a imagem de produção forem
criados.

## Dependência

Antes que este serviço possa ser implantado, é necessário:

1. criar e validar o Dockerfile do `management-app`;
2. publicar a imagem em registry;
3. definir a porta utilizada pela imagem;
4. levantar as variáveis de ambiente necessárias;
5. definir um mecanismo de health check, quando aplicável;
6. atualizar estes manifests com os valores confirmados.

Até que essas etapas sejam concluídas, o `management-app` deve ser considerado não implantável.
