# Checklist – Campos Obrigatórios StoryBrand Fallback

> Convenção de status: `[ ]` pendente • `[>]` em andamento • `[x]` concluído

## Frontend (Wizard)
- [x] Atualizar `WIZARD_INITIAL_STATE` para incluir campos vazios padronizados.
- [x] Tornar `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo` obrigatórios em `WIZARD_STEPS`.
- [x] Ajustar componentes `CompanyInfoStep.tsx` e `GenderTargetStep.tsx` com UX de obrigatoriedade.
- [x] Remover fallback `sexo_cliente_alvo: neutro` de `formatSubmitPayload` e atualizar review.
- [x] Atualizar testes de utilitários/front (`wizard.utils.test.ts`, `steps.test.tsx`).

## Backend (helpers/user_extract_data.py)
- [x] Revisar prompt/base para aceitar apenas masculino/feminino.
- [x] Atualizar few-shots removendo casos “neutro/misto”.
- [x] Remover defaults automáticos e validar que os três campos são obrigatórios.
- [x] Fazer `_normalize_sexo` retornar apenas masculino/feminino ou vazio para erro.
- [x] Criar testes garantindo erro quando campos faltam ou quando “neutro” é informado (`tests/unit/test_user_extract_data.py`).

## API `/run_preflight`
- [x] Ajustar testes (`tests/unit/test_preflight.py`) para esperar 422 quando faltar dado obrigatório.
- [ ] (Opcional) Revisar logs/telemetria pós-validação se necessário.

## QA / Documentação
- [ ] Executar `make lint` e `make test` com `VITE_ENABLE_NEW_FIELDS=true`.
- [ ] Atualizar README/docs externos se necessário (ex.: remover menção a gênero neutro).
- [ ] Validar manualmente o wizard com flag ativa (UX + payload enviado).

> Atualize este checklist conforme os itens forem verificados e sincronize com o plano `aprimoramento_plano_storybrand_v2.md`.
