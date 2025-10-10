# Cenário B — Somente personagem aprovado

- **Upload:** `character.png` (3.2 MB, `image/png`). Descrição do usuário: "Cliente sorridente com jaleco azul".
- **SafeSearch:** aprovado (`medical=LIKELY` registrado; demais campos `VERY_UNLIKELY`).
- **Cache:** `resolve_reference_metadata` retornou ID `char-512` com labels `clinician`, `smile`, `professional`.
- **Agente:** `image_assets_review.grade = "pass"`; `character_reference_used=True`, `product_reference_used=False`.

## Prompts gerados

| Estágio | Prompt após reidratação |
| --- | --- |
| Atual | `Emotion: despair | Maintain the same dermatologist with blue lab coat, capture pre-treatment frustration.` |
| Intermediário | `Emotion: determined | Same person applying revitalizing serum under clinical lighting.` |
| Aspiracional | `Emotion: joyful | Dermatologist celebrating patient results, identical facial features preserved.` |

## Resumo de auditoria

- `image_assets[0].emotions = {"prompt_estado_atual": "despair", "prompt_estado_intermediario": "determined", "prompt_estado_aspiracional": "joyful"}`
- `image_assets[0].reference_errors is None`
- `visual.reference_assets.character.user_description = "Cliente sorridente com jaleco azul"`
- URLs de saída foram sanitizadas (`signed_url` removido no `meta.json`).
