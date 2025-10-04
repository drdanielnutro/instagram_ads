# Diagnóstico: Fallback Storybrand não aciona com flags ativas

## 🧭 Caminho de carregamento das variáveis de ambiente
- O backend instancia `DevelopmentConfiguration` com valores padrão (`enable_new_input_fields=False`, `enable_storybrand_fallback=False`, `storybrand_gate_debug=False`). Esses valores só são atualizados quando `os.getenv` encontra variáveis de ambiente reais, pois o módulo é avaliado assim que `app.config` é importado.【F:app/config.py†L34-L108】
- Como não há nenhuma chamada a `python-dotenv` ou mecanismo equivalente no código, o backend depende exclusivamente das variáveis presentes no ambiente do processo no momento do import. Apenas possuir entradas em `.env`/`.env.local` não altera o estado de `config` se elas não forem exportadas antes da inicialização.【F:app/config.py†L79-L118】

## 🛠️ `Makefile` e propagação de variáveis no `make dev`
- A receita `make dev` apenas exporta `GOOGLE_APPLICATION_CREDENTIALS` e delega para `make dev-all`. Não existe comando que leia `.env` ou propague as flags do fallback para o shell que iniciará o backend.【F:Makefile†L24-L46】
- Dentro de `dev-all`, os alvos `make dev-backend-all` e `make dev-frontend` são disparados diretamente. O backend roda via `uv run uvicorn app.server:app`, portanto só verá variáveis que já estejam exportadas globalmente.【F:Makefile†L36-L63】
- Um teste com `uv run python -c "import os; print(os.getenv('ENABLE_STORYBRAND_FALLBACK'))"` retornou `None`, confirmando que `uv run` não carrega automaticamente os valores definidos apenas em `.env` e que o backend sobe com os padrões (flags desligadas).【2b7c9c†L1-L9】

## 🧩 Decisão de fallback e por que o debug é ignorado
- O `StoryBrandQualityGate` só considera o fallback habilitado quando **as duas** flags `config.enable_storybrand_fallback` e `config.enable_new_input_fields` estão `True`. Mesmo com `storybrand_gate_debug=True`, o forçamento (`should_force`) depende desse pré-requisito; se qualquer uma permanecer `False`, o gate mantém `decision_path='happy_path'` e registra `block_reason='fallback_disabled'`.【F:app/agents/storybrand_gate.py†L51-L109】
- O wrapper `LandingPageStage` reutiliza a mesma condição (`fallback_enabled`) para decidir se deve pular a análise da landing page. Como o flag combinado permanece `False`, a etapa de landing page continua sendo executada normalmente, reforçando o caminho feliz.【F:app/agent.py†L692-L724】
- Portanto, quando `make dev` inicializa o backend sem carregar as variáveis de ambiente, `config.enable_storybrand_fallback` e `config.enable_new_input_fields` ficam com os valores padrão (`False`), bloqueando o fallback mesmo em modo debug.

## ✅ Conclusão
Com `STORYBRAND_GATE_DEBUG=true` definido apenas em `.env`, o backend continua enxergando os valores padrão (`False`) porque `make dev`/`uv run` não carregam automaticamente esses arquivos. Como o gate só força o fallback quando o par (`enable_storybrand_fallback`, `enable_new_input_fields`) está ativo, o debug flag é ignorado e o pipeline segue pelo caminho feliz.【F:app/config.py†L34-L108】【F:app/agents/storybrand_gate.py†L51-L109】【2b7c9c†L1-L9】

## 💡 Recomendações
1. **Trate as flags como parte do ambiente de execução** – a prática recomendada é garantir que elas já estejam exportadas antes de iniciar `uv run`. Ajustar o `Makefile` para envolver o `make dev-all` com `set -a` e `source` dos arquivos `.env` garante que todas as variáveis fiquem visíveis para o backend, mantendo o comportamento alinhado ao ambiente de produção.【F:Makefile†L24-L63】

   ```make
   dev: check-and-kill-ports
	@set -a; \
	  if [ -f .env ]; then source .env; fi; \
	  if [ -f .env.local ]; then source .env.local; fi; \
	  export GOOGLE_APPLICATION_CREDENTIALS=$${GOOGLE_APPLICATION_CREDENTIALS:-./sa-key.json}; \
	  echo "Using GOOGLE_APPLICATION_CREDENTIALS=$${GOOGLE_APPLICATION_CREDENTIALS}"; \
	  if [ ! -f "$${GOOGLE_APPLICATION_CREDENTIALS}" ]; then \
	    echo "⚠️  Service account key not found at $${GOOGLE_APPLICATION_CREDENTIALS}. Continuing with ADC credentials (Signed URLs may fail)."; \
	  fi; \
	  make dev-all
   ```

   Com `set -a`, todas as variáveis carregadas dos arquivos `.env` e `.env.local` são exportadas para o subshell que invoca `make dev-all`, garantindo que `config.enable_new_input_fields`, `config.enable_storybrand_fallback` e `config.storybrand_gate_debug` recebam os valores configurados.
2. **Documente o passo de exportação para desenvolvimento local**, explicitando que apenas editar `.env` não basta porque `app.config` lê diretamente de `os.getenv` no momento do import.【F:app/config.py†L1-L149】
3. **Considere `python-dotenv` apenas se houver consenso de arquitetura** – embutir o carregamento via código resolve o gap local, mas difere do contrato esperado em produção (onde as env vars chegam prontas). Se optar por isso, garanta que o carregamento ocorra antes de `import app.config`, que exista fallback seguro quando o arquivo não estiver presente e que o comportamento continue consistente com os testes automatizados.

4. **Valide nos logs que o fallback está ativo** – após ajustar o `Makefile` e reiniciar o backend, confirme se a entrada `storybrand_gate_decision` agora registra `fallback_enabled=True`. Esse evento indica que o gate reconheceu as flags e que o pipeline de fallback será executado quando o debug estiver ativo.【F:app/agents/storybrand_gate.py†L51-L109】

## 🌐 Ambiente de produção
- Em produção (Cloud Run), as mesmas variáveis são definidas explicitamente via `--set-env-vars` ou pelo console; não há `.env` embarcado no container, e o serviço injeta os valores no ambiente do processo antes de o backend iniciar.【F:docs/ja_implementado/refatoracao_salvar_json.md†L127-L137】
- O `Dockerfile` e a aplicação não incluem loader automático desses arquivos, portanto `app/config.py` continua dependente apenas de `os.getenv`, tanto em dev quanto em prod.【F:Dockerfile†L1-L33】【F:app/config.py†L1-L149】