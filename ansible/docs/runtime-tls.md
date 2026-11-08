# Renovação automática do TLS no modo Compose

Parte do [procedimento de alternância entre Compose e K3s](runtime-mode.md).

## Funcionamento

O timer `apae-compose-tls-renew.timer` consulta o certificado a cada hora,
com atraso aleatório de até dez minutos. Quando restam mais de dois dias de
validade, não interrompe o Nginx. Dentro dessa janela, consulta o Certbot,
que decide se deve emitir outro certificado conforme a configuração de renovação.

A emissão existente utiliza `standalone` e precisa da porta pública 80 livre.
Por isso, quando há tentativa de renovação, o script pausa apenas o container
`proxy-proxy-1`. As páginas e o endpoint público do MinIO ficam brevemente
indisponíveis. Ao terminar, inclusive em caso de erro ou timeout, tenta retomar
o proxy se ele estava rodando antes. PostgreSQL e MinIO não são parados,
recriados ou alterados por essa automação.

O certificado continua armazenado em `/opt/apae/letsencrypt`. O Nginx monta
esse diretório inteiro, preservando o funcionamento dos links de `live/`
para `archive/`. O reinício do proxy faz o Nginx carregar o certificado atualizado,
usado nas portas 443 e 9003.

### Coordenação com a alternância

- Timer e playbooks compartilham a trava `/run/lock/apae-runtime-mode`.
- O timer adia a execução quando há outra operação em andamento.
- Só executa no modo `compose` registrado, com o serviço K3s inativo.
- No modo `cluster`, a renovação deste certificado é adiada. Não altera o
  cluster nem substitui sua futura gestão de certificados.
- Ao ativar Compose, o playbook para o K3s, verifica as portas e executa a
  renovação antes de iniciar os sites. Um certificado vencido pode ser renovado
  nessa etapa; um arquivo ausente ou inválido exige recuperação manual.
- Após a renovação, o playbook exige pelo menos uma hora de validade antes
  de disponibilizar as aplicações.

O timer não agenda trocas entre Compose e cluster. Essa decisão continua manual.

## Instalar ou atualizar

Na máquina de administração, a partir do diretório `ansible/` do repositório:

```bash
ansible-playbook playbooks/configure-runtime-tls.yml --syntax-check
ansible-playbook playbooks/configure-runtime-tls.yml
```

O playbook instala os scripts, valida as unidades systemd e habilita o timer.
Não troca o ambiente ativo e não solicita uma renovação imediatamente.
Precisa de sudo, Docker, OpenSSL, curl, iproute2, procps, coreutils e systemd
na VPS, além da configuração existente do Certbot e da imagem local
`certbot/certbot:v5.8.0`. A imagem não é baixada automaticamente durante a renovação.

As variáveis ficam em `ansible/inventories/production/group_vars/production.yml`.
Depois de alterá-las, reaplique esse playbook para atualizar os scripts instalados.
Os playbooks de alternância exigem a instalação do núcleo de renovação.
Essas operações não suportam `--check`.

## Consultar e executar

Na VPS (substitua `192.0.2.10`, endereço de exemplo, pelo `ansible_host`
configurado no inventário local):

```bash
sudo systemctl list-timers apae-compose-tls-renew.timer --no-pager
sudo systemctl status apae-compose-tls-renew.service --no-pager
sudo journalctl -u apae-compose-tls-renew.service -n 100 --no-pager
sudo openssl x509 \
  -in /opt/apae/letsencrypt/live/192.0.2.10/fullchain.pem \
  -noout -dates
```

O serviço é `oneshot`: ficar inativo após uma execução bem-sucedida é esperado.
O timer deve permanecer ativo e habilitado. Falhas ficam registradas no journal;
o envio de alertas externos não faz parte desta implementação.

Para executar a mesma verificação do timer imediatamente:

```bash
sudo systemctl start apae-compose-tls-renew.service
```

Para executar manualmente no terminal, exigindo o modo Compose:

```bash
sudo /usr/local/sbin/apae-renew-compose-tls --renew
```

Para testar o desafio contra o ambiente de testes ACME sem substituir o
certificado de produção, em uma janela que permita a pausa do proxy:

```bash
sudo /usr/local/sbin/apae-renew-compose-tls --dry-run
```

Não execute diretamente `/usr/local/libexec/apae/renew-compose-tls`.
Esse núcleo pressupõe que o wrapper ou o playbook já adquiriu a trava.

Mensagens de resultado:

| Mensagem | Resultado |
| --- | --- |
| `TLS_UNCHANGED` | Certificado fora da janela ou mantido pelo Certbot. |
| `TLS_RENEWED` | Certificado atualizado. |
| `TLS_DRY_RUN_OK` | Simulação concluída sem substituir o certificado. |
| `TLS_ENDPOINT_OK` | HTTPS respondeu com certificado confiável após a operação. |
| `TLS_DEFERRED` | Timer adiou a tentativa por concorrência ou modo incompatível. |

Os logs detalhados do Certbot ficam em `/var/log/apae-certbot/`.

## Falhas e recuperação

Uma tentativa do Certbot tem limite de sete minutos. Timeout e sinais tratáveis
executam a limpeza do container temporário e a retomada do proxy. Desligamento
abrupto, `SIGKILL`, falha do Docker ou falha ao iniciar o Nginx podem impedir
essa recuperação; confira o journal e o estado real dos containers.

Se o proxy não tiver retornado:

```bash
sudo docker start proxy-proxy-1
sudo docker exec proxy-proxy-1 nginx -t
```

Um container `apae-certbot-renew` remanescente bloqueia novas tentativas.
Investigue se ainda há renovação ativa antes de removê-lo. A mesma regra vale
para a trava: não a remova enquanto houver playbook, wrapper ou Certbot ativo.
Uma trava deixada por execução interrompida pode ser removida com `rmdir`
somente após confirmar que não há operação em andamento.

Se o Certbot informar porta ocupada, DNS, conectividade ou desafio inválido,
resolva a causa antes de repetir. A porta 80 precisa ser acessível publicamente
durante o desafio. A automação não altera regras de firewall nem emite o
certificado inicial. Não use `--force-renewal` como verificação periódica.

## Validação local dos scripts

Na raiz do repositório, com Python, Jinja2, PyYAML, cryptography, Bash e OpenSSL:

```bash
python3 -m unittest discover -s tests -p test_runtime_tls.py -v
```

Os testes renderizam os templates em diretórios temporários e simulam Docker,
systemd e rede. Cobrem concorrência, certificado vencido, falha de renovação,
timeout, recuperação do proxy e preservação dos serviços de dados. Não acessam
a VPS nem substituem o teste real do desafio ACME.

### Evidências da instalação em 07/11/2026

- Vinte testes locais dos scripts passaram; `ansible-lint` dos três playbooks
  relacionados passou sem avisos ou violações.
- Instalação na VPS concluída; reaplicação alterou apenas aquisição e liberação
  da trava, mantendo scripts, unidades e timer sem mudanças.
- `--dry-run` concluiu o desafio ACME com sucesso e preservou o certificado
  de produção. O proxy voltou e o HTTPS foi validado pelo wrapper.
- Execução pelo serviço systemd terminou com `Result=success` e
  `ExecMainStatus=0`; timer ativo e habilitado.
- Os cinco endpoints configurados responderam HTTP 200 com validação TLS.
- IDs, horários de início e volumes de PostgreSQL e MinIO permaneceram iguais
  antes e depois do teste.

O certificado servido nessa validação vence em 13/11/2026 às 16:25:01 UTC.
Não foi forçada uma nova emissão de produção: o certificado ainda estava fora
da janela de renovação. O teste ACME utilizou o ambiente de testes do Certbot.
