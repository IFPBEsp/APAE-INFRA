# 9. Alterações destrutivas

[← Voltar ao índice](README.md)

Mudanças de infraestrutura que possam causar:

```text
destroy
delete
replace
recreate
```

devem ser explicitamente destacadas no Pull Request.

O revisor deve ser capaz de identificar claramente:

* Qual recurso será afetado;
* Qual ambiente será impactado;
* Por que a alteração é necessária;
* Se existe risco de indisponibilidade;
* Se existe risco de perda de dados;
* Qual é a estratégia de recuperação.

No Terraform, alterações destrutivas devem receber atenção especial durante a revisão do:

```bash
terraform plan
```

---
