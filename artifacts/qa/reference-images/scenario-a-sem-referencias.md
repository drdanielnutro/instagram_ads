# Cenário A — Sem referências

- **Configuração:** formulário homepage sem uploads; flag `ENABLE_REFERENCE_IMAGES=true`.
- **SafeSearch:** não acionado (nenhum arquivo enviado).
- **Resultado do agente:** `image_assets_review.grade = "skipped"`; prompts mantiveram comandos de emoção padrão.

## Evidências

| Item | Valor |
| --- | --- |
| `visual[0].prompt_estado_atual` | `Emotion: despair — cliente percebendo queda de agendamentos` |
| `visual[0].prompt_estado_intermediario` | `Emotion: determined — consultor iniciando novo protocolo` |
| `visual[0].prompt_estado_aspiracional` | `Emotion: joyful — equipe comemorando agenda cheia` |
| `image_assets_review.summary[0].status` | `skipped` |
| Logs | `reference_images_present=false`, `safe_search_notes=None` |

## Observações

- Como não há metadados de referência, `reference_assets` não aparece no JSON final.
- O componente `ReferenceUpload` permanece em estado "Nenhum arquivo selecionado".
