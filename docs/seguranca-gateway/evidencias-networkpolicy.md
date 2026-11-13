# Evidências de NetworkPolicy — issue #114

Em 11/11/2026, os logs do k3s registraram Flannel com VXLAN e a inicialização
do controlador de NetworkPolicy `v2.6.3-k3s1`. O `iptables` continha regras
`KUBE-ROUTER`.

O teste usou um servidor HTTP atrás de um Service ClusterIP na porta
`8080/TCP` e dois pods clientes no namespace `issue-114-netpol-test`.

| Etapa | Cliente permitido | Cliente bloqueado |
| --- | --- | --- |
| Antes das políticas | `ok` | `ok` |
| Política de entrada no servidor | `ok` | `Connection refused`, código 1 |
| Após remover a política de entrada | — | `ok` |
| Política de saída no cliente bloqueado, usando o IP do Service | `ok` | `Connection refused`, código 1 |
| Após remover a política de saída | — | `ok` |

O namespace temporário foi excluído ao final. A validação dos fluxos dos
produtos e do Gateway será registrada após a ativação dos workloads.
