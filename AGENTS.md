# Repository Guidelines

Este documento concentra as informações essenciais para qualquer pessoa que contribua com o projeto. Use-o como referência rápida antes de acionar os subagentes ou editar o código.

---

## 1. Visão Geral do Projeto
- Plataforma multiagente (Google ADK + FastAPI + React) que gera anúncios do Instagram em JSON (texto + imagem) a partir de inputs do usuário.
- Pipeline completo: `input_processor → landing_page_analyzer → planning_pipeline → execution_pipeline → final_assembly → validation`.
- Backend em `app/`, frontend em `frontend/`, testes em `tests/`, infraestrutura em `deployment/`.

### Componentes críticos
- `app/server.py`: endpoints FastAPI (`/run_preflight`, `/run`, `/run_sse`).
- `app/agent.py`: definição do pipeline completo ADK.
- `app/callbacks/persist_outputs.py`: gravação do JSON final e `meta.json`.
- `app/agents/storybrand_fallback.py`: implementação do fallback StoryBrand com agentes sequenciais.
- `frontend/src/`: interface Vite/React para operação humana.

---

## 2. Comandos de Desenvolvimento
- Instalação: `make install`
- Dev full stack: `make dev` (`make dev-backend-all` + `npm --prefix frontend run dev` se preferir separado)
- API isolada: `make local-backend`
- Testes: `make test` ou `uv run pytest tests/unit -q`
- Lint e type-check: `make lint` (codespell, ruff, mypy)
- Outros úteis:
  - `uv run ruff check . --diff`
  - `uv run ruff format . --check --diff`
  - `uv run mypy .`
  - `uv run codespell`

---

## 3. Estrutura e Estilo de Código
- Python 3.10–3.12, type hints obrigatórios, linha 88 (E501 ignorado). Use `snake_case` para funções/variáveis e `PascalCase` para classes.
- TypeScript/React: siga ESLint/TS configs (`PascalCase` para componentes, `camelCase` para variáveis/funções).
- Nunca formate manualmente em conflito com ruff/ESLint; deixe as ferramentas cuidarem.

---

## 4. Entrada da API
### Campos Base
- `landing_page_url`, `objetivo_final`, `perfil_cliente`, `formato_anuncio`.
### Campos Condicionais (`ENABLE_NEW_INPUT_FIELDS=true`)
- `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo` (`"masculino"` ou `"feminino"` estrito).
- Inputs adicionais ficam disponíveis no fallback StoryBrand quando essas flags estão ativadas.

---

## 5. Variáveis de Ambiente & Flags
- Ajuste em `app/.env` e `app/.env.example` (mantemos ambos sincronizados).
- Principais flags:
  - `ENABLE_STORYBRAND_FALLBACK`
  - `ENABLE_NEW_INPUT_FIELDS`
  - `STORYBRAND_GATE_DEBUG`
  - `ENABLE_DETERMINISTIC_FINAL_VALIDATION`
  - `PERSIST_STORYBRAND_SECTIONS` (desativada por padrão; salva JSON com as 16 seções em `artifacts/storybrand/` e registra caminhos no meta)
- Use `make dev` para recarregar envs após alterações.

---

## 6. Persistência StoryBrand (Fallback)
- `PersistStorybrandSectionsAgent` salva as 16 seções completas antes do compilador; saída local `artifacts/storybrand/<session>.json` e upload opcional para GCS.
- `persist_outputs.py` injeta `storybrand_sections_saved_path`, `storybrand_sections_gcs_uri` e `storybrand_sections_present` em `meta.json`.
- Testes principais: `tests/unit/agents/test_storybrand_fallback.py` e `tests/unit/callbacks/test_persist_final_delivery.py`.
- Quando editar esse fluxo, atualize também a documentação e o changelog correspondente.

---

## 7. Testes e Qualidade
- `pytest`, `pytest-asyncio` (loop escopo função). Mantenha cobertura ≥80% em código crítico.
- Testes unitários: `tests/unit/`; integração: `tests/integration/`; locust: `tests/load_test/`.
- Adicione fixtures/mocks reutilizáveis em `tests/conftest.py`.
- Ao ajustar StoryBrand fallback, certifique-se de cobrir: flag habilitada, desabilitada, upload GCS, e meta.json consistente.

---

## 8. Segurança e Configuração
- Nunca versionar secrets. Use env vars conforme `app/.env.txt` e credenciais GCP via ADC.
- Valide inputs com Pydantic ao entrar no sistema.
- Evite logs com conteúdo sensível; sanitização já cobre tokens/assinaturas, mas revise novos logs.
- Deploy Cloud Run exige `PROJECT_ID` correto e buckets existentes (ver `Makefile` e `deployment/`).

---

## 9. Fluxos Especiais
### Revisão de Planos `.md`
- Seguir `codex/anexo_revisao_planos.md` e acionar o subagente `plan-code-validator` para validação determinística.

### Revisão de Código Implementado
- Obedecer `codex/anexo_revisao_codigo.md` (checklist → plano → código). Garanta testes completos e documentação atualizada antes de aprovar.

### StoryBrand Checklist → Plano → Código
- Sempre abra `plano_storybrand_salvo_checklist.md` e atualize o item atual para `in progress`.
- Leia o plano `plano_storybrand_salvo.md` antes de tocar no código.
- Ao finalizar, marque como `done` e relate o resultado na resposta/PR.

---

## 10. Fluxo de Subagentes
- `StoryBrandQualityGate` decide se o fallback é executado (ver `app/agents/storybrand_gate.py`).
- Fallback pipeline: `StoryBrandSectionRunner` → `PersistStorybrandSectionsAgent` → `FallbackStorybrandCompiler` → `FallbackQualityReporter`.
- Prompts: `prompts/storybrand_fallback/` (fail-fast se faltar). Logs em `state['storybrand_gate_metrics']` e `state['storybrand_audit_trail']`.
- Ao criar novos testes, use `tests/unit/agents/test_storybrand_gate.py` e `tests/unit/utils/test_prompt_loader.py` como referência.

---

## 11. Contribuição
- Use Conventional Commits (`feat:`, `fix:`, `test:`, etc.).
- Antes do PR: `make lint && make test`; inclua descrição, racional, issue vinculada, cobertura e screenshots se houver UI.
- PRs pequenos e focados facilitam revisão.

---

Mantenha este documento sincronizado sempre que novos fluxos, flags ou diretórios forem introduzidos no projeto.
