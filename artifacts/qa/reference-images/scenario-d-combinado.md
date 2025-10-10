# Cenário D — Personagem + produto aprovados

- **Uploads:** `character.png` (3.0 MB) + `product.png` (2.4 MB).
- **SafeSearch:** personagem com `medical=LIKELY`, produto `LIKELY` ausente.
- **Agente:** `character_reference_used=True`, `product_reference_used=True`; prompts combinaram aparência e item real.

## Prompts gerados

| Estágio | Prompt final |
| --- | --- |
| Atual | `Emotion: despair | Same patient with short curly hair and amber serum bottle unopened.` |
| Intermediário | `Emotion: determined | Identical patient applying the official product with clinical assistant.` |
| Aspiracional | `Emotion: joyful | Patient celebrating healthy skin holding the same branded bottle.` |

## Evidências adicionais

- `image_assets[0].emotions = {"prompt_estado_atual": "despair", "prompt_estado_intermediario": "determined", "prompt_estado_aspiracional": "joyful"}`
- `visual.reference_assets` inclui blocos `character` e `product` com descrições fornecidas pelo usuário.
- Logs estruturados (`image_assets_generation_complete`) registraram `reference_images_present=True` e notas de SafeSearch propagadas.
