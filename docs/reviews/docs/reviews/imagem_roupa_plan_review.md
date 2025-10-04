# Relatório de Validação — plano `imagem_roupa.md`

## Resumo executivo
- Registry de criações com 12 itens planejados (novos schemas, cache de referências, endpoint de upload, componentes React, helpers Vision/GCS, testes e documentação).
- Foram avaliadas 7 alegações de dependência/modificação; 5 alinharam com o código atual e 2 apresentaram blockers P0.
- Principais falhas: tentativa de mutar `initial_state` dentro do endpoint de upload (variável inexistente nesse escopo) e alteração proposta na assinatura de `persist_final_delivery` que conflita com os callbacks atuais do pipeline.

## Métricas
| Categoria                  | Quantidade |
| -------------------------- | ---------- |
| Alegações avaliadas        | 7          |
| P0 (crítico)               | 2          |
| P1                         | 0          |
| P2                         | 0          |
| P3                         | 0          |
| Itens no creation registry | 12         |

## Achados críticos (P0)
1. **Upload tenta atualizar `initial_state` inexistente**  
   - **Alegação**: "Antes de finalizar o endpoint, executar `initial_state.update(...)` para incluir as chaves no payload de `/run_preflight`".  
   - **Problema**: `initial_state` é um dicionário local criado apenas dentro de `run_preflight`; o endpoint de upload não compartilha essa referência e não há armazenamento global para mutação cruzada.  
   - **Evidência**: `initial_state` é definido dentro do escopo de `run_preflight`, retornado ao cliente e nunca exposto globalmente.【F:app/server.py†L334-L379】  
   - **Ação recomendada**: Persistir metadados em cache (como sugerido no plano) e fazer o `run_preflight` ler desse cache via `resolve_reference_metadata`, em vez de tentar mutar uma variável inexistente.

2. **Assinatura de `persist_final_delivery` incompatível com callbacks**  
   - **Alegação**: "Atualizar `app/callbacks/persist_outputs.py:45-56` para receber `state` no `persist_final_delivery`".  
   - **Problema**: A função hoje recebe apenas `callback_context`, resolve o `state` internamente e é chamada diretamente pelo `ImageAssetsAgent` e como `after_agent_callback` do `final_assembler`. Alterar a assinatura para exigir `state` quebraria ambas as chamadas (o callback de agentes envia somente o contexto).  
   - **Evidência**: `persist_final_delivery` obtém o estado via `resolve_state` e é invocado com único argumento tanto pelo agente quanto pelo callback configurado no `final_assembler`.【F:app/callbacks/persist_outputs.py†L35-L142】【F:app/agent.py†L310-L567】【F:app/agent.py†L1030-L1055】  
   - **Ação recomendada**: Manter a assinatura atual e apenas sanitizar `reference_images` dentro da função ao salvar o meta, sem exigir parâmetro extra.

## Tabela Plano ↔ Código
| Item do plano                                                                                       | Evidência no repositório                                                                                                                                                                                                               |
| --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pipeline de imagens citado para receber referências (`app/tools/generate_transformation_images.py`) | Função existente que gera as três etapas, permitindo expansão para novos parâmetros.【F:app/tools/generate_transformation_images.py†L209-L290】                                                                                        |
| Ajustes no `ImageAssetsAgent` para orquestrar geração com novas referências                         | Agente atual percorre variações, chama `generate_transformation_images` e persiste resultado, servindo como ponto de integração.【F:app/agent.py†L310-L583】                                                                           |
| Atualizações de prompts (`COPY_DRAFT`, `VISUAL_DRAFT`) e final assembler                            | Seções correspondentes já definidas no arquivo, prontas para receber placeholders adicionais.【F:app/agent.py†L860-L929】【F:app/agent.py†L1030-L1055】                                                                                |
| `run_preflight` responsável por popular `initial_state`                                             | Função existente monta o dicionário retornado, onde novos campos podem ser acrescentados com base no cache.【F:app/server.py†L334-L379】                                                                                               |
| Frontend `handleSubmit` e formulário `foco` como pontos de integração                               | `handleSubmit` controla o payload enviado ao backend e o formulário já coleta o campo `foco`, possibilitando anexar descrições de referência.【F:frontend/src/App.tsx†L423-L498】【F:frontend/src/components/InputForm.tsx†L250-L270】 |

## ✅ Planned Creations (não validar no código)
1. Novo módulo `app/schemas/reference_assets.py` com `ReferenceImageMetadata` e métodos de serialização.
2. Utilitário `app/utils/reference_cache.py` com `resolve_reference_metadata`, `build_reference_summary`, `merge_user_description` e `cache_reference_metadata` (TTL configurável).
3. Endpoint `POST /upload/reference-image` em `app/server.py` para tratar uploads de personagem/produto.
4. Função `upload_reference_image` em `app/utils/gcs.py` e helper `analyze_reference_image` em `app/utils/vision.py` (SafeSearch + labels).
5. Componente React `frontend/src/components/ReferenceUpload.tsx` e store/hook (`useReferenceImages`) para armazenar respostas do backend.
6. Helper `_load_reference_image` e novos flags em `app/tools/generate_transformation_images.py`.
7. Novos templates `image_current_prompt_template` e `image_aspirational_prompt_template_with_product` em `app/config.py`.
8. Logs/auditoria adicionais (`state['image_generation_audit']`, eventos estruturados) e persistência sanitizada de referências.
9. Suíte de testes unitários/integrados/cypress dedicados às novas funcionalidades.
10. Atualizações de documentação (README, materiais internos) descrevendo o fluxo de referências visuais.

## Incertezas / Follow-ups
- Nenhuma pendência adicional identificada além das correções apontadas acima.