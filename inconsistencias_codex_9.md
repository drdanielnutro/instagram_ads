### Inconsistência #1: Regras conflitantes para forçar o fallback
**Severidade**: ALTA
**Descrição**: A Seção 3 condiciona o fallback às flags `enable_storybrand_fallback` e `enable_new_input_fields`, mas logo em seguida autoriza `state['force_storybrand_fallback']` ou `config.storybrand_gate_debug` a desviarem diretamente para o pipeline de recuperação sem reforçar as mesmas flags.
**Impacto**: Permitir essa exceção sem validar as flags pode executar o fallback com estado incompleto, contrariando as salvaguardas do preflight.
**Evidências**: Plano ambíguo sobre as flags; o endpoint `/run_preflight` rejeita `force_storybrand_fallback` quando as flags estão desativadas.【F:aprimoramento_plano_storybrand_v2.md†L22-L26】【F:app/server.py†L302-L356】
**Referências**: `aprimoramento_plano_storybrand_v2.md`, `app/server.py`
**Relação ADK**: Afeta o comportamento do `BaseAgent` gate e o contrato de estado compartilhado (`ctx.session.state`).
**Correção Sugerida**: Esclarecer que a flag de debug/force só pode pular o score quando ambas as flags estiverem ativas (ou documentar a exceção descrevendo como inicializar os campos obrigatórios antes de chamar o fallback).

### Inconsistência #2: Lista de seções sem prefixo `storybrand_`
**Severidade**: CRÍTICA
**Descrição**: A tabela de seções do fallback usa nomes genéricos (`character`, `plan`, `identity`), enquanto o compilador existente lê chaves `storybrand_*`. 
**Impacto**: Implementar prompts/loop com as chaves genéricas faria o compilador produzir elementos vazios, quebrando o contrato final de estado.
**Evidências**: Plano lista nomes sem prefixo; `FallbackStorybrandCompiler` consome `storybrand_character`, `storybrand_plan`, `storybrand_identity` etc.【F:aprimoramento_plano_storybrand_v2.md†L44-L48】【F:app/agents/fallback_compiler.py†L90-L218】
**Referências**: `aprimoramento_plano_storybrand_v2.md`, `app/agents/fallback_compiler.py`
**Relação ADK**: O `SequentialAgent` de fallback precisa produzir exatamente as chaves esperadas para que o compilador (outro `BaseAgent`) mantenha o contrato de estado.
**Correção Sugerida**: Atualizar o plano para adotar os nomes `storybrand_*` já suportados pelo compilador e refletir essa nomenclatura nos prompts e na configuração das seções.

### Inconsistência #3: Aborto do pipeline sem mecanismo definido
**Severidade**: MÉDIA
**Descrição**: O plano ordena que o `fallback_input_collector` aborte o pipeline se `sexo_cliente_alvo` não puder ser determinado, mas não explica como interromper o `SequentialAgent` dentro do ADK.
**Impacto**: Sem orientação (ex.: `EventActions(escalate=True)` ou exceção), a implementação pode apenas registrar o erro e continuar, deixando o estado inconsistente.
**Evidências**: Plano determina “abortar imediatamente”; exemplos existentes usam `EventActions(escalate=True)` para encerrar fluxos.【F:aprimoramento_plano_storybrand_v2.md†L45-L47】【F:app/agent.py†L200-L235】
**Referências**: `aprimoramento_plano_storybrand_v2.md`, `app/agent.py`
**Relação ADK**: Necessita alinhar-se ao mecanismo de escalada de eventos do `SequentialAgent` para interromper execuções.
**Correção Sugerida**: Incluir instruções explícitas para emitir um `Event` com `EventActions(escalate=True)` (ou lançar exceção) quando o coletor não conseguir normalizar o campo obrigatório.

### Inconsistência #4: Campo `storybrand_gate_debug` já existe
**Severidade**: BAIXA
**Descrição**: A Seção 10 enumera `storybrand_gate_debug` como novo campo de configuração, porém ele já está presente em `DevelopmentConfiguration` com override via `STORYBRAND_GATE_DEBUG`.
**Impacto**: Pode induzir trabalho duplicado ou confusão sobre renomear/remover o atributo.
**Evidências**: Plano trata o campo como novidade; arquivo de configuração já o declara na lista de flags.【F:aprimoramento_plano_storybrand_v2.md†L108-L110】【F:app/config.py†L34-L40】
**Referências**: `aprimoramento_plano_storybrand_v2.md`, `app/config.py`
**Relação ADK**: Nenhuma direta.
**Correção Sugerida**: Ajustar o plano para reconhecer o campo existente e focar em documentar/testar seu uso.
