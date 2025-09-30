# Inconsistências Identificadas — Codex 7

1. **Uso de atributos inexistentes em `config` (`config.ENABLE_*`)**  
   - Descrição: O plano instrui o gate a ler `config.ENABLE_STORYBRAND_FALLBACK` e `config.ENABLE_NEW_INPUT_FIELDS`, mas a configuração só expõe atributos em `snake_case` (e a flag do fallback ainda será adicionada nesse formato).  
   - Impacto: Tentativas de acessar os atributos em maiúsculas gerarão `AttributeError`, impedindo o roteamento entre caminho feliz e fallback.  
   - Evidências: Plano (`StoryBrandQualityGate`) usa os nomes incorretos; `DevelopmentConfiguration` define apenas atributos minúsculos e overrides correspondentes.【F:aprimoramento_plano_storybrand_v2.md†L22-L27】【F:app/config.py†L34-L94】  
   - Referência ADK: o `StoryBrandQualityGate` precisa ler flags de `ctx.session.state`/`config`; erro nessa etapa derruba o pipeline.  
   - Correção sugerida: Atualizar o plano para referenciar `config.enable_storybrand_fallback` e `config.enable_new_input_fields`, documentando as variáveis de ambiente `ENABLE_STORYBRAND_FALLBACK` e `ENABLE_NEW_INPUT_FIELDS`. Acrescentar ação explícita para revisar a seção "Como fazer" garantindo que todos os trechos de código exemplo usem `snake_case` e prever teste unitário que falhe caso a flag seja acessada com o nome incorreto.

2. **Fallback forçado pode executar sem novos campos disponíveis**  
   - Descrição: O plano manda executar o fallback imediatamente quando `state['force_storybrand_fallback']` ou `config.storybrand_gate_debug` estão ativos, sem reforçar que `config.enable_new_input_fields` precisa ser `True`.  
   - Impacto: Se a flag de novos campos estiver desabilitada (valor padrão), o `/run_preflight` não inclui `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo` no `initial_state`, deixando o fallback sem dados essenciais.  
   - Evidências: Plano autoriza fallback forçado; `app/server.py` só insere os novos campos quando `config.enable_new_input_fields` é verdadeiro; configuração padrão mantém a flag desativada.【F:aprimoramento_plano_storybrand_v2.md†L22-L27】【F:app/server.py†L221-L304】【F:app/config.py†L34-L56】  
   - Referência ADK: subagentes do fallback dependem dessas chaves para gerar e revisar as 16 seções.  
   - Correção sugerida: Deixar explícito que o fallback (mesmo forçado) requer `config.enable_new_input_fields=True` e `VITE_ENABLE_NEW_FIELDS=true`, ou instruir o plano a popular as chaves antes de acionar o pipeline. Incluir checklist operacional no plano para validar o estado das flags antes de permitir o acionamento manual do fallback.

3. **Flag `force_storybrand_fallback` não é propagada pelo `/run_preflight`**  
   - Descrição: O plano afirma que o preflight pode definir `state['force_storybrand_fallback']`, mas o endpoint constrói o `initial_state` sem copiar essa chave e o helper não a produz.  
   - Impacto: A flag nunca chega ao `ctx.session.state`, tornando impossível acionar o fallback manualmente.  
   - Evidências: Plano descreve a flag; `app/server.py` monta `initial_state` apenas com campos explícitos; `helpers/user_extract_data.py` não retorna `force_storybrand_fallback`.【F:aprimoramento_plano_storybrand_v2.md†L51-L56】【F:app/server.py†L282-L308】【F:helpers/user_extract_data.py†L420-L567】  
   - Referência ADK: sem a flag na sessão, o `StoryBrandQualityGate` jamais detectará o pedido de fallback forçado.  
   - Correção sugerida: Orientar a atualização do `/run_preflight` (e do helper) para popular `initial_state['force_storybrand_fallback']` quando configurado. Especificar que o contrato de dados (`UserExtractedData`) e os testes E2E devem ser atualizados para cobrir a nova chave no estado inicial.
