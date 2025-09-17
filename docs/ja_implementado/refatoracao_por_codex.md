# Refatoração por Codex — Preflight + Planos Fixos para Ads (Vertex AI)

## Objetivo

Colocar o servidor como gatekeeper para validar e normalizar a entrada do usuário (preflight) usando LangExtract via Vertex AI, selecionar um de três planos fixos por formato (Reels/Stories/Feed) e iniciar o ADK já com o plano correto e especificações do formato. O ADK foca apenas em executar tarefas mínimas para preencher o JSON final, com loops de revisão/refino dentro de cada tarefa.

## Por que esta refatoração

- Eliminar variação do planejamento dinâmico herdado de deep research que gera 25–35 tarefas e atrasa a entrega (45+ min no log analisado).
- Garantir foco no entregável (JSON do anúncio), com um plano curto e determinístico por formato.
- Reduzir custo/latência: validar insumos antes de acionar o ADK; manter loops apenas onde agregam valor (revisão/refino por tarefa).

## Escopo e princípios

- Não alterar o schema de saída do anúncio.
- Reusar o pipeline ADK existente (agentes, loops, montagem/validação final), apenas mudando a origem do plano (fixo, injetado) e adicionando preflight no servidor.
- Manter Vertex AI (ADC) como backend único, inclusive no preflight.
- Reels no pipeline atual: imagens (sem vídeo). Especificações por formato devem refletir isso.

---

## Visão Geral da Solução

1) Preflight no servidor: extrai e valida `landing_page_url`, `objetivo_final`, `perfil_cliente`, `formato_anuncio`, `foco` a partir do texto do usuário usando LangExtract (Vertex AI). Normaliza sinônimos, valida mínimos. Se inválido, responde ao usuário sem acionar o ADK.

2) Seleção de plano fixo (por formato): Reels/Stories/Feed — cada plano é determinístico e mapeia 1:1 para os campos do JSON final com 6–8 tarefas no máximo.

3) Injeção de estado inicial no ADK: cria/atualiza a sessão com os campos normalizados, `implementation_plan` fixo e `format_specs` do formato escolhido.

4) Execução: o ADK processa tarefa a tarefa; revisão/refino acontece em loop dentro da tarefa; ao concluir as tarefas, monta e valida o JSON final.

---

## Componentes

### 1. Preflight (helpers/user_extract_data.py)

- Função: transformar um prompt livre em dados estruturados, normalizados e validados. Bloquear inputs inválidos/insuficientes.
- Tecnologia: LangExtract v1.0.9+ via Vertex AI (ADC) com `language_model_params`.
- Saída padronizada:
  - `success: bool`
  - `data: { landing_page_url, objetivo_final, perfil_cliente, formato_anuncio, foco }`
  - `normalized: { formato_anuncio_norm, objetivo_final_norm }`
  - `errors: [{ field, message }]` (quando `success=false`)

Config LangExtract (preflight):
- `model_id: "gemini-2.5-flash"`
- `language_model_params: { vertexai: true, project: $GOOGLE_CLOUD_PROJECT, location: $GOOGLE_CLOUD_LOCATION|us-central1 }`
- `extraction_passes: 1`, `max_workers: 4`, `max_char_buffer: 1500–2000`
- `use_schema_constraints: true`, `fence_output: false`

Prompt (preflight, ideia):
- “From this user text, extract:
  - landing_page_url (http/https)
  - objetivo_final (one of contato|leads|vendas|agendamentos|inscrições)
  - perfil_cliente (free text)
  - formato_anuncio (one of Reels|Stories|Feed)
  - foco (optional)
  Use exact user text; do not invent. If not present, leave empty. Normalize common synonyms as in examples.”

Few-shot (curto e prático):
- Exemplo 1: linhas “chave: valor” (com todos os campos).
- Exemplo 2: sinônimos (“story”→“Stories”; “mensagens no WhatsApp”→“agendamentos”).
- Exemplo 3: inválidos (“formato: anúncio rápido”).

Normalização (pós-extract):
- `formato_anuncio_norm`:
  - {"reel", "reels", "reels video"} → "Reels"
  - {"story", "stories", "storie", "storys"} → "Stories"
  - {"feed", "carrossel"} → "Feed"
  - outros → inválido
- `objetivo_final_norm` (exemplos, ajustar conforme regras):
  - {"mensagens", "whatsapp", "whats", "conversas"} → "agendamentos"
  - {"leads", "cadastros", "inscrições"} → "inscrições" (ou "leads", conforme padrão)
  - {"compras", "vendas"} → "vendas"

Validação mínima:
- Obrigatórios: `landing_page_url` válida; `formato_anuncio_norm` ∈ {Reels, Stories, Feed}; `objetivo_final_norm` não vazio; `perfil_cliente` não vazio.
- Se faltar algo: `success=false`, responder 422 ao usuário com `errors` e dicas de correção.

### 2. Planos Fixos (app/plan_models/fixed_plans.py)

- Três constantes: `REELS_PLAN`, `STORIES_PLAN`, `FEED_PLAN`.
- Estrutura compatível com `ImplementationPlan`/`ImplementationTask` do agente atual (categories e campos existentes):
  - Categorias usadas: STRATEGY, RESEARCH, COPY_DRAFT, COPY_QA, VISUAL_DRAFT, VISUAL_QA, COMPLIANCE_QA, ASSEMBLY.
  - Máx. 6–8 tarefas.

Plano mínimo sugerido (base):
- STRATEGY (curto; mensagens-chave objetivas)
- RESEARCH (preencher `referencia_padroes`)
- COPY_DRAFT (preencher `copy` e `cta_instagram`)
- COPY_QA (validar copy; ajustes se for o caso)
- VISUAL_DRAFT (preencher `visual` + coerência de `formato`)
- VISUAL_QA (validar visual)
- COMPLIANCE_QA (ver políticas; sem gerar campo)
- ASSEMBLY (montar JSON final: `landing_page_url`, `formato`, `copy`, `visual`, `cta_instagram`, `fluxo`, `referencia_padroes`, `contexto_landing`)

Dependências entre tarefas:
- COPY_QA depende de COPY_DRAFT
- VISUAL_QA depende de VISUAL_DRAFT
- ASSEMBLY depende de COPY_QA, VISUAL_QA, RESEARCH, COMPLIANCE_QA

Mapeamento 1:1 (campo do JSON ↔ tarefa):
- `copy`, `cta_instagram` ↔ COPY_DRAFT (+ COPY_QA)
- `visual` (descricao_imagem, aspect_ratio) ↔ VISUAL_DRAFT (+ VISUAL_QA)
- `referencia_padroes` ↔ RESEARCH
- `formato` ↔ VISUAL_DRAFT (respeita `format_specs`)
- `fluxo`, `contexto_landing`, `landing_page_url` ↔ ASSEMBLY

Planos por formato (diretrizes chave):
- Reels: `aspect_ratio="9:16"`; copy com gancho curto e verbos de ação; visual com elementos on-screen curtos (lembrando que geramos imagem estática).
- Stories: `aspect_ratio="9:16"`; urgência/escassez; CTA claro para “Enviar mensagem”/“Saiba mais”. Evitar elementos não permitidos em ads.
- Feed: `aspect_ratio="1:1"` ou `"4:5"`; copy ligeiramente mais informativa; visual focado em composição estática e legível.

### 3. Especificações por Formato (app/format_specifications.py)

- Dicionário `FORMAT_SPECS` com regras curtas e acionáveis:
  - copy: `headline_max_chars`, estilo, tom, variações sugeridas.
  - visual: `aspect_ratio` por formato; diretrizes de composição.
  - strategy: etapa de funil preferencial; `cta_preferencial` por `objetivo_final`.
- No state: `format_specs` (dict) e `format_specs_json` (string compacta) para prompts.

### 4. Integração no Servidor

- Endpoint gateway (ex.: `POST /run_preflight`):
  1. Recebe o texto do usuário (`newMessage.parts[0].text`).
  2. Chama `helpers/user_extract_data.extract_user_input(text)`.
  3. Se `success=false`: responde 422 com `errors`, sem acionar ADK.
  4. Se `success=true`: carrega plano fixo por `formato_anuncio_norm`, injeta `implementation_plan`, campos normalizados e `format_specs` na sessão do ADK e inicia a execução (reencaminhando para `/run_sse` ou chamando o `root_agent`).

- Alternativa: middleware antes de `/run`/`/run_sse`. O endpoint separado é mais seguro para rollout.

### 5. Execução no ADK (sem grandes mudanças)

- Reusar `complete_pipeline` existente. Duas opções:
  - A) Deixar `planning_pipeline` no‑op quando o state já tiver `implementation_plan` (flag `planning_mode=fixed`).
  - B) Endpoint alternativo que começa direto no `execution_pipeline` (exige pequena alteração na orquestração).
- Loops de revisão/refino permanecem dentro de cada tarefa (`code_review_loop`). Idealmente, refiner só roda se review for “fail”.
- Montagem/validação final (`final_assembler`/`final_validator`) ficam inalterados.

---

## Fluxo Detalhado (E2E)

1) Usuário envia prompt (texto livre) → servidor `/run_preflight`.
2) Preflight (LangExtract/Vertex) extrai/normaliza/valida campos.
   - Se falha: 422 com campos ausentes/invalidos + exemplo de correção.
3) Seleção de plano: Reels/Stories/Feed.
4) Criar/atualizar sessão ADK com state inicial:
   - `landing_page_url`, `objetivo_final`, `perfil_cliente`, `formato_anuncio`, `foco` (normalizados)
   - `format_specs`, `format_specs_json`
   - `implementation_plan` (fixo) e flag `planning_mode=fixed`
5) Iniciar ADK (`/run_sse`):
   - `TaskInitializer` carrega tarefas fixas
   - Para cada tarefa: `TaskManager` → `code_generator` → `code_review_loop` (review/refine) → `code_approver` → `TaskIncrementer`
6) Ao concluir tarefas: `final_assembler` monta JSON final; `final_validator` valida; `final_fix_agent` corrige se necessário; retorno ao frontend.

---

## Contratos Sugeridos (sem implementar agora)

### A. helpers/user_extract_data.py

- Função pública:
  - `def extract_user_input(raw_text: str) -> dict` → `{ success, data, normalized, errors }`
- Internos:
  - `class UserInputExtractor` com `__init__(model_id="gemini-2.5-flash")` e `_examples()`
  - `extract(text)`: chama `lx.extract(...)` com `language_model_params` Vertex
  - `_convert_to_schema(langextract_result)`: mapeia para nosso schema (data/normalized/errors)

Exemplo de resposta (sucesso):
```json
{
  "success": true,
  "data": {
    "landing_page_url": "https://exemplo.com/landing",
    "objetivo_final": "agendamentos",
    "perfil_cliente": "homens 35-50, executivos...",
    "formato_anuncio": "Reels",
    "foco": "não engordar no inverno"
  },
  "normalized": {
    "formato_anuncio_norm": "Reels",
    "objetivo_final_norm": "agendamentos"
  },
  "errors": []
}
```

Exemplo (falha):
```json
{
  "success": false,
  "data": {"landing_page_url": "https://exemplo.com"},
  "normalized": {"formato_anuncio_norm": ""},
  "errors": [
    {"field": "formato_anuncio", "message": "Valor 'anúncio rápido' não suportado. Use Reels|Stories|Feed."}
  ]
}
```

### B. app/plan_models/fixed_plans.py

- Exporta: `REELS_PLAN`, `STORIES_PLAN`, `FEED_PLAN` (compatíveis com `ImplementationPlan`).
- Cada plano: 6–8 tarefas nas categorias já existentes; dependências corretas; `file_path` dummy (ex.: "ads/TASK-00X.json").

### C. app/format_specifications.py

- Exporta: `FORMAT_SPECS = { "Reels": {...}, "Stories": {...}, "Feed": {...} }`
- Regras sintéticas e práticas; manter compacto para não inflar prompts.

---

## Critérios de Sucesso/Fracasso (por tarefa)

- COPY_DRAFT: contém `copy.headline`, `copy.corpo`, `copy.cta_texto` coerentes com `format_specs` e `landing_page_context`; `cta_instagram` válido.
- COPY_QA: se `validacao_copy == "ok"` e ajustes vazios/irrelevantes → pass; senão → refino obrigatório.
- VISUAL_DRAFT: `visual.descricao_imagem` clara e `visual.aspect_ratio` coerente com o formato.
- VISUAL_QA: validação análoga à de copy.
- RESEARCH: `referencia_padroes` com síntese objetiva (sem lorem ipsum; Brasil 2024–2025).
- COMPLIANCE_QA: sem termos proibidos; atenção a saúde/medicina.
- ASSEMBLY: todos os campos obrigatórios presentes, enums corretos, coerência com objetivo/foco/landing.

Observação: o `code_review_loop` já implementa o padrão review→refine; apenas reduzir iterações no modo fixo.

---

## Telemetria e Logs

- Reaproveitar `make dev-quiet`, `logs-follow-essential`, `logs-slim` e `logs-essential`.
- Logar no preflight: entrada truncada (len/hash), `success`, `errors`, `formato_anuncio_norm`, plano escolhido.
- Em execução: manter eventos essenciais; evitar spam de LangExtract/Vertex (já filtrado).

---

## Rollout sugerido

1) Implementar o helper de preflight (isolado, com testes unitários simples).
2) Adicionar `app/plan_models/fixed_plans.py` e `app/format_specifications.py`.
3) Criar endpoint `/run_preflight` (ou gateway) que chama o ADK após sucesso.
4) Inicialmente, manter `complete_pipeline` intacto. Em seguida, adicionar flag `planning_mode=fixed` para `planning_pipeline` virar no‑op.
5) Ajustar limites de iteração para modo fixo (loops menores) e medir latência.
6) Validar E2E em três casos (Reels/Stories/Feed) e com entradas inválidas.

---

## Riscos e Mitigações

- LangExtract no preflight adiciona custo/latência: usar `extraction_passes=1`, poucos exemplos e normalização simples pós-processamento.
- Incompatibilidade com prompts: evitada ao manter categorias/fields do pipeline atual; planos não devem introduzir chaves novas não suportadas.
- Reels com vídeo: evitar; specs deixam explícito `tipo_midia: imagem`.
- Falhas de ADC/Vertex: garantir `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=us-central1`, billing e permissões; mensagens de erro claras.

---

## Futuro e extensões

- Toggle de variações: `ads_variations_count` (1 ou 3) para trocar instruções dos 3 agentes finais sem refatorar pipeline.
- Status por tarefa: adicionar `task_statuses` (`pending|in_progress|done|failed`) para retomada e debugar.
- Adotar montagem incremental (`ad_draft`) no state após cada “pass” de tarefa.
- Otimizações no LangExtract da landing (StoryBrand): truncar texto, `extraction_passes=1` quando latência for crítica.

---

## Conclusão

Este desenho coloca o servidor como gatekeeper, aplica LangExtract via Vertex para validar/normalizar a entrada, seleciona planos fixos por formato e deixa o ADK executar apenas o necessário para preencher o JSON final. O resultado é previsibilidade, menor latência/custo e foco no entregável — sem quebrar o pipeline existente.

