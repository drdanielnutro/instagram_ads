# QA Manual – Plano v3 (Fase 5)

Este registro consolida os cenários manuais solicitados na Fase 5 do plano de validação determinística.

## 1. JSON Válido (Flag On)
- **Procedimento**: execução dos agentes `FinalAssemblyGuardPre`, `FinalAssemblyNormalizer` e `FinalDeliveryValidatorAgent` com variações válidas (vide teste `tests/integration/pipeline/test_deterministic_flow.py`).
- **Resultado**: estado final com `deterministic_final_validation.grade = "pass"`, `semantic_visual_review.grade = "pass"` e `image_assets_review.grade = "skipped"`; persistência grava payload normalizado.

## 2. JSON Inválido (Flag On)
- **Procedimento**: execução de `FinalDeliveryValidatorAgent` com payloads malformados (string não JSON) e com duplicidades/CTAs inválidas (`tests/unit/validators/test_final_delivery_validator.py`).
- **Resultado**: `deterministic_final_validation.grade = "fail"`, `deterministic_final_validation_failed = True`, motivo registrado em `delivery_audit_trail` e meta de falha gerada.

## 3. Fallback StoryBrand Engajado
- **Procedimento**: simulação via guard determinístico sem snippets `VISUAL_DRAFT` (`tests/unit/agents/test_final_assembly_guard.py`) que força bloqueio antes da montagem.
- **Resultado**: `deterministic_final_validation.grade = "fail"` com `source = "guard"`, pipeline escalado conforme auditoria.

## 4. Fluxo Legado (Flag Off)
- **Procedimento**: verificação estrutural e limpeza do estado determinístico no pipeline legado (`tests/integration/pipeline/test_flag_toggle.py`).
- **Resultado**: agente `ResetDeterministicValidationState` remove chaves determinísticas e garante caminho legado sem efeitos residuais.

> Todos os cenários foram reproduzidos localmente através das suítes automatizadas adicionadas nesta fase. Não há dependência de serviços externos.
