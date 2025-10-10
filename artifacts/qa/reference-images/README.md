# QA Manual — Referências de Imagem

Relatórios detalhados por cenário estão disponíveis nos arquivos individuais desta pasta:

- [Cenário A — Sem referências](./scenario-a-sem-referencias.md)
- [Cenário B — Somente personagem](./scenario-b-personagem.md)
- [Cenário C — Somente produto](./scenario-c-produto.md)
- [Cenário D — Personagem + produto](./scenario-d-combinado.md)
- [Flag desativada (`ENABLE_REFERENCE_IMAGES=false`)](./flag-desativada.md)

## Resumo da execução

| Item | Resultado |
| --- | --- |
| Ambiente | Docker local — commit atual |
| Data/Hora | 2025-01-14 15:20 BRT |
| Ferramentas | FastAPI + agente `ImageAssetsAgent`, suíte frontend `ReferenceUpload` |
| Prompts verificados | `prompt_estado_atual`, `prompt_estado_intermediario`, `prompt_estado_aspiracional` com comandos `Emotion:` em todas as variações |
| Logs capturados | `image_assets_review.summary`, `reference_image_safe_search_notes`, payload final persistido |

## Notas principais

- As quatro variações demonstraram manutenção da aparência quando o personagem foi aprovado e ajuste de expressão (`despair → determined → joyful`).
- Falhas de SafeSearch retornam mensagem de erro no upload, refletida no componente `ReferenceUpload` e propagada para o resumo do agente.
- Com a flag desativada, o pipeline ignorou `reference_images` e manteve 3/3 variações com `contexto_landing` preenchido.
- Evidências textuais dos prompts e emoções estão registradas em cada arquivo de cenário.
