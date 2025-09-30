# Inconsistências — Codex 5

1. **Coleta dos campos essenciais via `landing_page_context`**
   - **Descrição**: O plano orienta o `fallback_input_collector` a popular `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo` lendo `state['landing_page_context']`, mas o estado atual só armazena esses valores na raiz da sessão após o preflight.
   - **Impacto**: O fallback ficaria sem entradas obrigatórias mesmo quando o usuário as fornece, resultando em abortos ou saídas incoerentes.
   - **Evidências**: Estrutura planejada na Seção 4; `landing_page_context` contém apenas dados da página; `initial_state` injeta os campos na raiz quando as flags estão ativas.【F:aprimoramento_plano_storybrand_v2.md†L38-L46】【F:app/agent.py†L626-L687】【F:app/server.py†L284-L305】
   - **Referências ao código**: `landing_page_analyzer` (classe `LlmAgent` em `app/agent.py`); preflight em `app/server.py`.
   - **Relação com ADK**: O `SequentialAgent` do fallback opera sobre `ctx.session.state`; ler a chave errada viola o contrato de dados esperado pelos subagentes.

2. **Abortar fallback quando `sexo_cliente_alvo` ≠ {masculino,feminino} sem garantir flags de coleta**
   - **Descrição**: A Seção 16.3 exige abortar se o valor final não estiver normalizado para o domínio binário, mas o backend usa `neutro` como default quando `ENABLE_NEW_INPUT_FIELDS` está desligado e o extractor só valida rigidamente quando essa flag está ativa.
   - **Impacto**: Ativar o fallback sem sincronizar as flags de coleta quebraria o fluxo por erro artificial, mesmo que a UI ainda não obrigue o preenchimento.
   - **Evidências**: Política descrita na Seção 16.3; preflight atribui `neutro` quando o campo não é obrigatório; validações condicionais no extractor.【F:aprimoramento_plano_storybrand_v2.md†L176-L184】【F:app/server.py†L220-L305】【F:helpers/user_extract_data.py†L300-L420】
   - **Referências ao código**: Função `run_preflight` em `app/server.py`; classe `UserInputExtractor` em `helpers/user_extract_data.py`.
   - **Relação com ADK**: O gate pode acionar o fallback (por score baixo) e o pipeline terminaria em erro antes de produzir o StoryBrand necessário para agentes subsequentes.
