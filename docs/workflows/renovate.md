# Padronização de dependências com Renovate

## Objetivo

Utilizar o Renovate para identificar novas versões de dependências e abrir Pull Requests de atualização nos repositórios da organização IFPBEsp.

A configuração compartilhada fica centralizada no repositório `IFPBEsp/APAE-INFRA`, evitando a duplicação de regras entre os projetos.

Implementação relacionada à issue #84.

## Decisão técnica

Foi escolhido o **Renovate GitHub App** em vez do Dependabot.

A escolha considera a necessidade de compartilhar configurações entre repositórios e personalizar agrupamentos, agendamentos, limites de Pull Requests e atualizações de referências fixadas por SHA ou digest.

A instalação do GitHub App depende de autorização administrativa na organização IFPBEsp.

## Dependências atendidas

O preset contempla os seguintes ecossistemas:

- Maven: dependências e plugins Java.
- pnpm: pacotes JavaScript e TypeScript.
- Docker: imagens base dos Dockerfiles.
- GitHub Actions: versões e SHAs das Actions.
- Terraform: providers e módulos.

O Renovate utiliza os arquivos de dependências encontrados em cada repositório para identificar as atualizações aplicáveis.

## Política inicial

- Verificação semanal, utilizando o fuso horário `America/Fortaleza`.
- Limite de cinco Pull Requests comuns abertos simultaneamente por repositório.
- Limite de dois Pull Requests comuns criados por hora.
- Agrupamento de atualizações menores por ecossistema.
- Atualizações major permanecem separadas, salvo regras específicas.
- Automerge desativado inicialmente.
- Revisão humana e checks de CI antes do merge.
- Preservação das referências imutáveis quando aplicável, incluindo digests Docker e SHAs de GitHub Actions.

Atualizações de segurança podem receber tratamento especial conforme as regras do Renovate e os limites configurados.

## Configuração compartilhada

O arquivo `default.json`, localizado na raiz do APAE-INFRA, contém o preset compartilhado.

Cada repositório consumidor deve possuir um arquivo `renovate.json` na raiz com o seguinte conteúdo:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "local>IFPBEsp/APAE-INFRA"
  ]
}
```

O preset é lido a partir da branch padrão do APAE-INFRA, atualmente `dev`.

Caso o repositório APAE-INFRA seja privado, a instalação do Renovate deve possuir permissão de leitura para acessar o preset.

## Processo de adesão

1. Solicitar autorização para instalação do Renovate GitHub App na organização IFPBEsp.
2. Garantir acesso do Renovate ao APAE-INFRA e aos repositórios consumidores necessários.
3. Incorporar o `default.json` à branch padrão do APAE-INFRA.
4. Criar `renovate.json` no repositório consumidor.
5. Validar a configuração.
6. Verificar o Dependency Dashboard e os primeiros Pull Requests propostos.
7. Confirmar que os checks de CI e as políticas de revisão funcionam corretamente.

## Segurança

O Renovate não deve realizar automerge durante a adoção inicial.

As atualizações são propostas por Pull Requests para permitir análise das alterações, dos resultados da CI e dos riscos de compatibilidade.

O Renovate não substitui a verificação de vulnerabilidades da issue #68. As duas automações são complementares: a SCA identifica vulnerabilidades e o Renovate propõe atualizações de dependências.

O Renovate também não substitui a automação GitOps da issue #82, responsável pelas referências das imagens de aplicações nos overlays Kubernetes. O preset desativa as atualizações das imagens `ghcr.io/ifpbesp/**` em todos os gerenciadores, incluindo Docker Compose e Kustomize, evitando propostas de tags ou digests que concorram com essa automação. As demais imagens Docker continuam sendo atualizadas pelo Renovate.

## Validação inicial

A adesão deverá ser comprovada em pelo menos um repositório de aplicação, conforme os critérios de aceite da issue #84.

O teste será considerado concluído quando o Renovate conseguir ler o preset compartilhado e detectar dependências ou gerar propostas de atualização, sem realizar merges automaticamente.
