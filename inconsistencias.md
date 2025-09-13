## Inconsistências entre as duas pesquisas

Abaixo estão as principais diferenças e contradições identificadas entre `resultado_deep_research_1.md` e `resultado_deep_research_2.md`.

1) Ferramenta de fetch nativa do ADK
- Pesquisa 1: Afirma que não há ferramenta nativa de fetch (p.ex. `web_fetch`, `http_fetch`) e propõe criar uma Function Tool custom.
- Pesquisa 2: Afirma que existe `load_web_page(url)` nativa (import de `google.adk.tools`).

2) Estratégia de coleta e análise
- Pesquisa 1: Propõe tool custom (`web_fetch_tool`/`fetch_and_extract_text`) + callbacks para parsing/StoryBrand.
- Pesquisa 2: Propõe usar `load_web_page` nativa junto com `google_search`, escolhendo via `before_tool_callback`.

3) Uso de `google_search`
- Pesquisa 1: Substitui `google_search` pela tool custom de fetch.
- Pesquisa 2: Mantém `google_search` e adiciona `load_web_page` às `tools`.

4) Arquitetura do pipeline
- Pesquisa 1: Um único `landing_page_analyzer` com `before_tool_callback`/`after_tool_callback` e `output_key="landing_page_analysis_summary"`.
- Pesquisa 2: Separa em “LandingFetcher” + agente “SB7QA” (com `output_schema`) e sugere `LoopAgent` entre eles.

5) Terminação/controle de loop
- Pesquisa 1: Sugere uma `exit_loop_tool` que seta `tool_context.actions.escalate = True` para encerrar o loop.
- Pesquisa 2: Usa `state["retry_fetch"]` para reexecutar o trecho; não detalha a escalada explícita.

6) Modelos LLM exemplificados
- Pesquisa 1: Exemplo com `model="gemini-1.5-flash"`.
- Pesquisa 2: Usa `gemini-2.5-flash` e `gemini-2.5-pro` em agentes diferentes.

7) Persistência de resultados no estado
- Pesquisa 1: Enfatiza `output_key="landing_page_analysis_summary"` e menos chaves explícitas no estado.
- Pesquisa 2: Lista chaves específicas: `fetch_result`, `parsed_page`, `storybrand_json`, `lacunas_detectadas`, `qa_report`, `retry_fetch`.

8) Organização de código sugerida
- Pesquisa 1: Modifica `agent.py` e importa `.tools.web_fetch_tool`.
- Pesquisa 2: Recomenda pastas dedicadas (`tools/`, `callbacks/`, `schemas/`, `agents/`) e arquivos como `langextract_sb7.py`, `landing_fetch_callbacks.py`, `sb7_qa.py`.

9) Aplicação do StoryBrand (SB7)
- Pesquisa 1: Defende fazer a transformação SB7 de forma determinística no `after_tool_callback`, evitando um segundo agente.
- Pesquisa 2: Usa wrapper `langextract_sb7.py` (LangExtract) e um agente “SB7QA” com `output_schema` para validar/estruturar o JSON.

