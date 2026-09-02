# 8. Observabilidade

[← Voltar ao índice](README.md)

O repositório possui infraestrutura destinada à observabilidade utilizando ferramentas como Prometheus, Grafana e Loki.

As aplicações executadas em produção devem seguir algumas práticas básicas para facilitar monitoramento e diagnóstico.

---

## 8.1 Logs

Aplicações containerizadas devem preferencialmente enviar logs para:

```text
stdout
stderr
```

Evitar depender exclusivamente de arquivos de log armazenados dentro do container.

Containers podem ser destruídos e recriados, portanto arquivos locais não devem ser considerados armazenamento permanente de logs.

---

## 8.2 Identificação

Logs e métricas devem permitir identificar, quando possível:

* Aplicação;
* Ambiente;
* Serviço;
* Instância ou Pod;
* Tipo de evento.

---

## 8.3 Métricas

Aplicações devem expor métricas quando houver suporte e necessidade operacional.

Essas métricas podem posteriormente ser coletadas por ferramentas como Prometheus.

---

## 8.4 Dashboards

Dashboards devem apresentar informações relevantes para operação dos ambientes, evitando painéis sem finalidade clara.

Exemplos:

* Consumo de CPU;
* Consumo de memória;
* Disponibilidade;
* Quantidade de erros;
* Latência;
* Reinicializações de Pods.

---
