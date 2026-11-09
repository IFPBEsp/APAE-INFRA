# Gitleaks e resposta a vazamento de segredos

> **Repositório mantenedor:** [`IFPBEsp/APAE-INFRA`](https://github.com/IFPBEsp/APAE-INFRA)
> **Issue de origem:** [APAE-INFRA #94](https://github.com/IFPBEsp/APAE-INFRA/issues/94)
> **Versão mínima suportada:** `v8.30.1`

Este documento descreve o uso do [Gitleaks](https://github.com/gitleaks/gitleaks) nos repositórios da APAE, o tratamento de falsos positivos e o procedimento de resposta a incidentes quando um segredo é commitado por engano.

## 1. O que é o Gitleaks

O Gitleaks é uma ferramenta de código aberto para detecção de segredos e credenciais em repositórios Git. Ele analisa arquivos, commits, branches e histórico em busca de padrões que indiquem chaves de API, tokens, senhas, chaves privadas, credenciais de banco de dados e outros dados sensíveis.

A ferramenta pode ser executada:

- localmente, antes de um commit;
- em pipelines de CI/CD, na validação de Pull Requests;
- sobre o histórico completo de um repositório.

### 1.1 Por que o Gitleaks é utilizado na APAE

O Gitleaks é adotado nos repositórios da APAE para:

- **Prevenir vazamentos:** identificar segredos antes que cheguem ao repositório remoto.
- **Reduzir o tempo de exposição:** detectar credenciais commitadas acidentalmente o mais cedo possível.
- **Padronizar a proteção:** aplicar a mesma política de detecção em todos os repositórios.
- **Preservar o histórico:** evitar que segredos permaneçam acessíveis em commits antigos.
- **Apoiar a revisão de código:** fornecer evidências objetivas durante o Pull Request.

A existência de um segredo no histórico do Git é um risco real: remover o valor em um commit posterior **não** o elimina dos commits anteriores, e qualquer pessoa com acesso ao repositório pode recuperá-lo. Por isso, a prevenção e a resposta rápida são essenciais.

## 2. Versão mínima suportada

A versão mínima suportada nos repositórios da APAE é o **Gitleaks `v8.30.1`** ou mais recente.

Versões anteriores a `v8.30.1` não são suportadas: os comandos modernos (`gitleaks git`) e os flags usados neste documento exigem essa versão. Ao atualizar a ferramenta, valide o comportamento em um repositório piloto antes de padronizar a nova versão nos demais projetos.

> **Aviso:** o pacote do `apt` do Ubuntu frequentemente vem desatualizado e pode entregar uma versão inferior a `v8.30.1`. Nesse caso, instale o binário oficial a partir dos [GitHub Releases](https://github.com/gitleaks/gitleaks/releases) (veja a seção 3.1, opção 2).

Para verificar a versão instalada:

```bash
gitleaks version
```

## 3. Instalação

### 3.1 Linux

#### Opção 1: gerenciador de pacotes APT

```bash
sudo apt update
sudo apt install gitleaks
```

A disponibilidade do pacote depende da distribuição e dos repositórios configurados. Caso o pacote não esteja disponível, utilize o binário oficial.

> **Aviso:** o pacote do `apt` do Ubuntu pode estar desatualizado e instalar uma versão anterior a `v8.30.1`. Verifique a versão com `gitleaks version` após a instalação; se ela for menor que a mínima suportada, desinstale o pacote e use a opção 2 (binário oficial do GitHub Releases).

#### Opção 2: binário oficial do GitHub

1. Acesse a página de [releases do Gitleaks](https://github.com/gitleaks/gitleaks/releases).
2. Baixe o arquivo compatível com a arquitetura do sistema, por exemplo `gitleaks_<versao>_linux_x64.tar.gz`.
3. Extraia o binário e mova-o para um diretório no `PATH`.

Exemplo:

```bash
curl -sSL -o gitleaks.tar.gz \
  https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz
tar -xzf gitleaks.tar.gz gitleaks
sudo install -m 0755 gitleaks /usr/local/bin/gitleaks
gitleaks version
```

Substitua `v8.30.1` pela versão `v8.x` desejada (sempre igual ou superior à mínima suportada). Sempre que possível, valide o checksum publicado na release antes de instalar o binário.

### 3.2 macOS

Com o [Homebrew](https://brew.sh/) instalado:

```bash
brew install gitleaks
```

Para atualizar:

```bash
brew upgrade gitleaks
```

### 3.3 Windows

#### Opção 1: Winget

```powershell
winget install Gitleaks.Gitleaks
```

#### Opção 2: Chocolatey

```powershell
choco install gitleaks
```

Após a instalação, confirme a versão em um novo terminal:

```powershell
gitleaks version
```

### 3.4 Verificação da instalação

Independentemente do sistema operacional, a saída de `gitleaks version` deve indicar uma versão `v8.30.1` ou superior.

## 4. Uso básico

> **Nota:** as versões modernas do Gitleaks (v8.19+) substituíram os comandos legados `gitleaks detect` e `gitleaks protect` pelo comando unificado `gitleaks git`. Todos os exemplos deste documento usam a sintaxe moderna.

### 4.1 Analisar o repositório atual

```bash
gitleaks git --source . --verbose
```

Esse comando analisa o histórico e os arquivos do repositório e exibe os achados no terminal. Para gerar um relatório:

```bash
gitleaks git --source . \
  --report-format json \
  --report-path gitleaks-report.json
```

O arquivo de relatório pode conter os segredos encontrados. Não o commite e remova-o após a análise.

### 4.2 Hook de pré-commit

O comando recomendado para hooks de pré-commit é:

```bash
gitleaks git --pre-commit --staged --redact --verbose
```

Ele verifica somente o que será incluído no próximo commit (`--staged`), oculta os valores sensíveis na saída (`--redact`) e exibe os detalhes de cada achado (`--verbose`).

Exemplo de hook em `.git/hooks/pre-commit`:

```bash
#!/bin/sh
exec gitleaks git --pre-commit --staged --redact --verbose
```

Torne o hook executável:

```bash
chmod +x .git/hooks/pre-commit
```

Também é possível configurar o hook por meio do [pre-commit](https://pre-commit.com/):

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks
        args: ["git", "--pre-commit", "--staged", "--redact", "--verbose"]
```

Caso o hook encontre achados, o commit é bloqueado até que o segredo seja removido ou a exceção seja registrada (seção 5).

### 4.3 Analisar um intervalo de commits

```bash
gitleaks git --source . --log-opts="origin/dev..HEAD" --verbose
```

Use essa opção em Pull Requests para verificar apenas os commits novos em relação à branch de destino.

### 4.4 Ocultar segredos na saída

Para evitar a exposição de valores sensíveis em logs de CI:

```bash
gitleaks git --source . --redact --verbose
```

## 5. Tratamento de falsos positivos

Um falso positivo ocorre quando o Gitleaks identifica um valor que parece um segredo, mas não é uma credencial real. Exemplos comuns incluem valores de exemplo, fixtures de teste, hashes públicos e identificadores sem poder de acesso.

### 5.1 Regra geral

Não desative regras globalmente nem enfraqueça a configuração para contornar um falso positivo. Prefira:

1. Confirmar que o valor **não** é uma credencial válida.
2. Corrigir o código ou o teste para não conter o padrão detectado, quando possível.
3. Se a exceção for legítima, registrar a exceção de forma pontual no arquivo `.gitleaksignore`.
4. Documentar a justificativa no Pull Request.

### 5.2 Arquivo `.gitleaksignore`

O arquivo `.gitleaksignore` fica na raiz do repositório e lista as ocorrências que devem ser ignoradas. Cada linha deve conter a **fingerprint** do achado, normalmente no formato:

```text
<commit>:<arquivo>:<regra>:<linha>
```

Exemplo:

```text
a1b2c3d4e5f6:docs/exemplos/config.md:generic-api-key:12
```

Para obter a fingerprint, execute o Gitleaks com `--verbose` e copie o identificador exibido para o achado. Também é possível obtê-la no relatório JSON gerado com `--report-format json`.

Fluxo recomendado:

1. Execute o Gitleaks e identifique o falso positivo.
2. Copie a fingerprint exata do achado.
3. Adicione a fingerprint ao `.gitleaksignore`, uma por linha.
4. Reexecute o Gitleaks para confirmar que o achado foi ignorado.
5. Inclua o `.gitleaksignore` no Pull Request junto com a justificativa.

> **Atenção:** a fingerprint é específica para o commit, arquivo, regra e linha. Alterações no arquivo ou no histórico podem gerar uma nova fingerprint. Evite usar curingas amplos que possam mascarar segredos reais.

### 5.3 Justificativa no Pull Request

Toda exceção adicionada ao `.gitleaksignore` deve ser justificada no Pull Request. A justificativa deve conter:

- a fingerprint ou o achado ignorado;
- o motivo pelo qual o valor não é um segredo real;
- a evidência de que o valor é público, fictício ou sem poder de acesso;
- a confirmação de que a exceção é pontual e não enfraquece a política geral.

Exemplo de justificativa:

```text
Falso positivo: a fingerprint <fingerprint> corresponde a uma chave de exemplo
em docs/exemplos/config.md. O valor é fictício, não é usado por nenhum ambiente
e não concede acesso a nenhum recurso. Exceção pontual registrada no
.gitleaksignore.
```

O revisor deve avaliar a justificativa antes do merge. Exceções sem justificativa ou com abrangência excessiva devem ser recusadas.

## 6. Guia de resposta a incidentes (vazamento real)

Se um segredo real for commitado por engano, trate o caso como incidente de segurança. A ordem das ações importa: **rotacionar a credencial é sempre a primeira prioridade**.

### 6.1 Passo 1: rotacionar ou revogar a credencial imediatamente

1. Acesse o provedor responsável pela credencial (GitHub, cloud, banco de dados, serviço de e-mail, etc.).
2. **Revogue** a credencial comprometida, quando possível.
3. **Gere uma nova credencial** e atualize os locais autorizados, como Secrets do GitHub Actions ou o gerenciador de segredos aprovado.
4. Confirme que a credencial antiga não possui mais acesso.
5. Verifique os logs do provedor em busca de uso indevido durante o período de exposição.

Não aguarde a limpeza do histórico para rotacionar. Enquanto a credencial antiga for válida, o segredo continua explorável, mesmo que o commit seja removido.

### 6.2 Passo 2: remover o segredo do código

1. Remova o valor sensível do arquivo atual.
2. Substitua por uma referência ao mecanismo de segredos, como `${{ secrets.NOME }}` em GitHub Actions.
3. Adicione o arquivo ao `.gitignore`, quando aplicável.
4. Faça um novo commit com a correção.

Se o segredo foi incluído no último commit e ainda não foi enviado ao remoto, é possível corrigir o commit localmente com `git commit --amend` antes do push.

Se o segredo já foi enviado ao remoto, remover o valor em um novo commit **não é suficiente**: o valor permanece acessível no histórico.

### 6.3 Passo 3: limpar o histórico, se necessário

A limpeza do histórico deve ser feita **depois** da rotação da credencial. Ela reescreve commits e exige coordenação com todos que possuem clones do repositório.

Antes de iniciar:

- comunique o time e combine a janela de manutenção;
- confirme que a credencial já foi revogada;
- faça backup do repositório;
- verifique se há branches e tags que também precisam ser limpas.

#### Remover um arquivo de todo o histórico com `git filter-repo`

```bash
git filter-repo --path caminho/do/arquivo --invert-paths
```

#### Substituir um valor específico no histórico

Crie um arquivo de substituição, por exemplo `replacements.txt`:

```text
segredo-real==>***REMOVED***
```

Execute:

```bash
git filter-repo --replace-text replacements.txt
```

Após a reescrita:

1. Revise o histórico e os arquivos resultantes.
2. Execute novamente o Gitleaks sobre o histórico completo.
3. Envie as alterações com `git push --force-with-lease`.
4. Solicite que todos atualizem ou recriem seus clones.
5. Remova branches e tags antigas que ainda contenham o segredo.

> **Atenção:** plataformas como o GitHub podem manter objetos inacessíveis por algum tempo. Em casos de exposição relevante, avalie acionar o suporte da plataforma e considerar a credencial permanentemente comprometida.

### 6.4 Passo 4: comunicar e registrar o incidente

1. Comunique o ocorrido ao time responsável e, se necessário, ao responsável de segurança.
2. Registre o que foi exposto, o período de exposição, as ações tomadas e as evidências.
3. Verifique se o segredo foi reutilizado em outros repositórios ou ambientes.
4. Avalie a necessidade de abrir uma issue de acompanhamento ou um ADR.
5. Atualize procedimentos e automações para evitar recorrência.

### 6.5 Checklist rápido

- [ ] Credencial revogada ou rotacionada no provedor.
- [ ] Nova credencial armazenada apenas em local seguro.
- [ ] Segredo removido do código atual.
- [ ] Histórico limpo, quando necessário.
- [ ] Gitleaks executado novamente sem achados.
- [ ] Time comunicado e incidente registrado.
- [ ] Clones e branches antigas tratados.

## 7. Referências

- [Gitleaks — projeto oficial](https://github.com/gitleaks/gitleaks)
- [Gitleaks — releases](https://github.com/gitleaks/gitleaks/releases)
- [Gitleaks — documentação de configuração](https://github.com/gitleaks/gitleaks#configuration)
- [git filter-repo](https://github.com/newren/git-filter-repo)
- [Boas práticas de segredos e credenciais do APAE-INFRA](../boas-praticas/02-segredos-e-credenciais.md)

---

**Manutenção:** este documento deve ser revisado sempre que a versão mínima do Gitleaks, a política de exceções ou o procedimento de resposta a incidentes forem alterados.
