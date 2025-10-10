# Execução com `ENABLE_REFERENCE_IMAGES=false`

- **Configuração:** variável de ambiente ajustada antes do `make local-backend`.
- **Resultado esperado:** pipeline ignora referências, entrega três variações completas com `contexto_landing` preenchido.

## Evidências

| Item | Valor |
| --- | --- |
| `config.enable_reference_images` | `false` |
| `initial_state.reference_images` | ausente |
| `final_code_delivery` | 3 variações, cada uma com prompts contendo `Emotion:` |
| `image_assets_review.grade` | `skipped` |
| `deterministic_final_validation.normalized_payload.variations[0].contexto_landing` | presente |

## Observações

- Ao reenviar com a flag ligada, as referências voltam a ser consideradas sem necessidade de limpar cache manualmente.
- Não foram registradas regressões na entrega textual (`copy`, `cta_texto`).
