# Cenário C — Somente produto aprovado

- **Upload:** `product.webp` (1.9 MB). Descrição: "Sérum revitalizante em frasco âmbar".
- **SafeSearch:** aprovado sem flags críticas.
- **Agente:** `character_reference_used=False`, `product_reference_used=True`; prompts removeram menções ao personagem.

## Prompts gerados

| Estágio | Prompt final |
| --- | --- |
| Atual | `Stage one — Highlight the approved product reference (amber serum dropper) with Emotion: concern.` |
| Intermediário | `Stage two — Integrate the real serum being applied, keep lighting consistent. Emotion: hopeful.` |
| Aspiracional | `Stage three — Showcase satisfied customer hands holding the same product, Emotion: joyful.` |

## Observações

- `visual.reference_assets.product.labels = ["serum", "bottle", "amber"]`.
- Fallback textual removeu chamadas ao personagem e reforçou a presença do produto em todas as cenas.
- `image_assets[0].emotions` reflete `concern → hopeful → joyful`.
