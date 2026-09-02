# 10. Rollback

[← Voltar ao índice](README.md)

Alterações devem considerar, quando aplicável, uma estratégia de rollback.

Para aplicações containerizadas, isso pode significar voltar para uma imagem anterior.

Exemplo:

```text
1.4.0
↓ problema
1.3.0
```

Entretanto, rollback da aplicação não garante rollback de todos os componentes do sistema.

---

## 10.1 Banco de dados

Alterações de banco de dados devem receber atenção especial.

Voltar para uma versão anterior da aplicação não necessariamente desfaz migrações já aplicadas ao banco.

Exemplo:

```text
Aplicação 1.4.0
        ↓
Migração de banco
        ↓
Novo schema

Rollback aplicação
1.4.0 → 1.3.0

        ≠

Rollback automático do banco
```

Migrações devem ser projetadas considerando:

* Compatibilidade entre versões;
* Possibilidade de reversão;
* Backup;
* Risco de perda de dados.

---
