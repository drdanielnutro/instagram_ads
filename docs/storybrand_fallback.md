# StoryBrand Fallback – Arquitetura e Fluxo

## Visão Geral
O fallback de StoryBrand garante que a narrativa esteja completa mesmo quando a landing page analisada não fornece dados suficientes. O gate `StoryBrandQualityGate` decide entre o caminho feliz e o fallback com base em:
- Score `storybrand_analysis.completeness_score` ou `landing_page_context.storybrand_completeness`.
- Flags `config.enable_storybrand_fallback` e `config.enable_new_input_fields`.
- Força manual (`state['force_storybrand_fallback']`) ou debug (`config.storybrand_gate_debug`).

Quando o fallback é acionado, ele executa os cinco blocos abaixo em `app/agents/storybrand_fallback.py`:
1. **FallbackInputInitializer** – garante chaves obrigatórias e inicializa `storybrand_audit_trail`.
2. **fallback_input_collector** – agente LLM que confirma/normaliza `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`.
3. **StoryBrandSectionRunner** – gera e revisa as 16 seções (writer → reviewer → corrector) respeitando `config.fallback_storybrand_max_iterations`.
4. **FallbackStorybrandCompiler** – converte as seções aprovadas para o schema `StoryBrandAnalysis`, atualizando `storybrand_summary`, `storybrand_ad_context` e score.
5. **FallbackQualityReporter** – agrega métricas e salva `storybrand_recovery_report`.

## Prompts
Os prompts residem em `prompts/storybrand_fallback/` e são carregados pelo utilitário `PromptLoader` (`app/utils/prompt_loader.py`). O loader faz cache em memória e dispara `FileNotFoundError` se qualquer arquivo obrigatório estiver ausente. Placeholders `{variavel}` são renderizados antes de cada execução.

Principais arquivos:
- `collector.txt` – valida inputs essenciais.
- `section_*.txt` – 16 prompts de escrita.
- `review_masculino.txt` e `review_feminino.txt` – revisão sensível ao gênero.
- `corrector.txt` – ajustes pós-review.
- `compiler.txt` – diretrizes para sumarização final (consumida pelo relatório).

## Métricas e Auditoria
- `state['storybrand_gate_metrics']`: score avaliado, threshold, caminho escolhido, timestamp, flags de força/debug.
- `state['storybrand_audit_trail']`: eventos cronometrados por estágio/seção.
- `state['storybrand_recovery_report']`: resumo agregando seções aprovadas e iterações.

## Configuração
- `ENABLE_STORYBRAND_FALLBACK` precisa estar `true` junto de `ENABLE_NEW_INPUT_FIELDS` para permitir fallback.
- `FALLBACK_STORYBRAND_MAX_ITERATIONS` controla o número máximo de tentativas por seção (default: 3).
- `FALLBACK_STORYBRAND_MODEL` permite definir um modelo dedicado (default usa `config.worker_model`).
- `STORYBRAND_GATE_DEBUG` força o fallback para QA.

## Testes
- `tests/unit/agents/test_storybrand_gate.py` cobre decisões do gate (score alto/baixo, force flag, flags desabilitadas).
- `tests/unit/utils/test_prompt_loader.py` valida carregamento e renderização dos prompts.
- `tests/unit/agents/test_storybrand_sections.py` garante o mapeamento das 16 seções.

Para testes de integração adicionais, use `config.storybrand_gate_debug=True` e verifique os logs estruturados (`storybrand_gate_decision`) para confirmar o caminho executado.

## Futuro
- Monitorar `storybrand_gate_metrics` em dashboard dedicado.
- Avaliar cache de resultados de fallback para evitar recomputações.
- Explorar relatórios de auditoria baseados em `storybrand_audit_trail`.
