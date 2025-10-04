# StoryBrand Landing Page Flow

## Estado atual (commit 47e6f5e)
- O pipeline `complete_pipeline` executa `LandingPageStage` antes do `StoryBrandQualityGate`. O wrapper chama o agente real de landing page apenas quando o fallback não está sendo forçado. Caso as flags `ENABLE_STORYBRAND_FALLBACK`, `ENABLE_NEW_INPUT_FIELDS` e `STORYBRAND_GATE_DEBUG` ou o sinal `force_storybrand_fallback` estejam ativos, ele preenche `landing_page_context` com `{}` e registra `storybrand_landing_page_skipped` sem coletar dados da landing page.
- Após o estágio condicional, `StoryBrandQualityGate` decide se roda o fallback (sempre que o forçamento está habilitado ou o score está ausente/abaixo do mínimo) e em seguida delega para o planejador normal.

## Estado anterior (commit 53f1b9c)
- O mesmo `complete_pipeline` chamava `landing_page_analyzer` diretamente. Mesmo quando o gate entrava em modo debug/forçado, a análise da landing page era executada antes do fallback.
- As decisões do `StoryBrandQualityGate` já honravam as flags (`ENABLE_STORYBRAND_FALLBACK`, `ENABLE_NEW_INPUT_FIELDS`, `STORYBRAND_GATE_DEBUG`, `force_storybrand_fallback`), mas como a análise vinha antes do gate, o fallback “forçado” ainda consumia os recursos da etapa de landing page.

> Referências diretas:
> - commit 47e6f5ea8b96c98717c636d087788aa3d50b6546 (`app/agent.py`, linhas 692-724 e 1270-1278).
> - commit 53f1b9c246a47e599859fdd260f5d8d0d164e7a0 (`app/agent.py`, linhas 1233-1240).
