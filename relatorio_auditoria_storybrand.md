**Sumário Executivo**
- Alegações totais: 17
- Confirmadas: 11 • Refutadas: 6 • Inconclusivas: 0
- Causas-raiz recorrentes:
  * Plano depende de campos/estruturas inexistentes ou não inicializados no código atual (ex.: `storybrand_fallback_meta.status`, `storybrand_inputs`).



  * Gaps de definição operacional (limpeza de flags, rollback, persistência FE) não detalhados no plano, embora necessários para o fluxo real.



  * Preflight/backend continuam exigindo payload completo, conflitantes com a divisão em fases proposta para o frontend.



**Metodologia**
- Estratégias: navegação seletiva com `rg`, `sed -n`, `nl -ba` para mapear referências; inspeção manual dos arquivos listados no plano.
- Critérios: comparação literal entre instruções do plano e implementação atual; verificação de dependências cruzadas (estado, SSE, tipos TS).
- Limitações: auditoria somente leitura; sem execução de testes automatizados.

**Matriz de Alegações — Vereditos**

| # | Resumo da alegação | Tipo | Sev. | Veredito | Arquivos-chave | Linhas |
|---|--------------------|------|------|----------|----------------|--------|
| A1 | Plano usa `status` inexistente | dados/estado | 🔴 | Confirmada | plano_refatoracao_storybrand.md / app/agents/storybrand_gate.py | 30-33 / 105-110 |
| A2 | Bootstrap × Gate executam fallback duas vezes | arquitetura | 🔴 | Refutada | plano_refatoracao_storybrand.md | 30-33, 41-43 |
| A3 | Checagem `status != "completed"` falha sem meta | lógica | 🔴 | Confirmada | app/agents/storybrand_gate.py | 48-57 |
| A4 | Ordem do pipeline invertida incorretamente | arquitetura | 🔴 | Refutada | app/agent.py | 2076-2083 |
| A5 | Falta validar `REQUIRED_INPUT_KEYS` no bootstrap | validação | 🔴 | Refutada | app/agents/storybrand_fallback.py | 269-314 |
| A6 | Early return ambíguo em `LandingPageStage` | implementação | 🟠 | Refutada | plano_refatoracao_storybrand.md | 61-63 |
| A7 | Limpeza de flags sem local definido | flags | 🟠 | Confirmada | plano_refatoracao_storybrand.md | 33-33 |
| A8 | Formato SSE `state_delta` não especificado | contrato | 🟠 | Refutada | plano_refatoracao_storybrand.md | 49-56 |
| A9 | Preflight falha com payload parcial | backend | 🟠 | Confirmada | helpers/user_extract_data.py | 492-599 |
| A10 | Estado FE não persistido | frontend | 🟠 | Confirmada | plano_refatoracao_storybrand.md / frontend/src/App.tsx | 125-133 / 120-147 |
| A11 | Compatibilidade retroativa não garantida | migração | 🟠 | Confirmada | plano_refatoracao_storybrand.md / helpers/user_extract_data.py / app/server.py / app/agent.py | 85-87,214-217 / 520-599 / 501-514 / 195-210 |
| A12 | Tipos TS sem `phase` | tipagem | 🟡 | Confirmada | frontend/src/types/wizard.types.ts | 3-58 |
| A13 | Matriz de testes sem fixtures/mocks | testes | 🟡 | Confirmada | plano_refatoracao_storybrand.md | 90-95,177-186 |
| A14 | Rollback não trata dados já persistidos | rollback | 🟡 | Confirmada | plano_refatoracao_storybrand.md / app/callbacks/persist_outputs.py | 214-217 / 238-261 |
| A15 | Glossário sem novas flags | docs | 🟡 | Refutada | plano_refatoracao_storybrand.md | 161-173 |
| A16 | Tratamento de erros ausente (SSE/timeouts) | resiliência | 🟡 | Confirmada | plano_refatoracao_storybrand.md | 125-147 |
| A17 | Falta doc de migração/rollout | migração | 🟡 | Confirmada | plano_refatoracao_storybrand.md | 208-217 |

**Análise Detalhada por Alegação**

**A1 — Plano usa `status` inexistente**  
Trecho do Plano: “invocando `fallback_storybrand_pipeline` quando `storybrand_fallback_meta.status != "completed"`… definir `state["storybrand_fallback_meta"]["status"] = "completed"`.”

  
Validação no Código:
```python
state["storybrand_fallback_meta"] = {
    "fallback_engaged": should_run_fallback,
    "decision_path": metrics["decision_path"],
    "trigger_reason": trigger_reason,
    "timestamp_utc": timestamp,
}
```

  
Análise: estrutura atual não contém chave `status`, logo o plano referencia campo inexistente.  
Veredito: **CONFIRMADA**

**A2 — Conflito arquitetural Bootstrap × Gate**  
Trecho do Plano: bootstrap só roda quando `status != "completed"` e gate pula fallback se `status == "completed"` sem `force`.

  
Análise: instruções garantem que, após bootstrap definir `status="completed"`, o gate não reexecuta o fallback, exceto quando forçado. Não há conflito arquitetural inerente.  
Veredito: **REFUTADA**

**A3 — Checagem `status != "completed"` falha sem meta**  
Trecho do Plano: mesma dependência do campo `status`.

  
Validação no Código: apenas o gate atual inicializa `storybrand_fallback_meta` (antes do bootstrap proposto).

  
Análise: ao inserir o bootstrap antes do gate, a chave pode não existir, causando `KeyError` ou retorno `None` se não tratado.  
Veredito: **CONFIRMADA**

**A4 — Ordem do pipeline invertida vs atual**  
Validação no Código: pipeline atual `input_processor → landing_page_stage → storybrand_quality_gate → execution_pipeline`.

  
Trecho do Plano: adiciona `storybrand_bootstrap_stage` antes de `landing_page_stage`, mantendo restante da ordem.

  
Análise: a mudança é intencional para tornar o fallback padrão; não quebra a ordem relativa dos estágios existentes, nem impossibilita o gate usar o score (porque `landing_page_stage` permanece antes do gate).  
Veredito: **REFUTADA**

**A5 — Falta validar `REQUIRED_INPUT_KEYS`**  
Validação no Código:
```python
for key in REQUIRED_INPUT_KEYS:
    ...
    if not value:
        errors.append(f"{key} ausente")
...
if errors:
    EventActions(escalate=True)
    raise RuntimeError(...)
```

  
Análise: o pipeline já valida os campos essenciais; o bootstrap apenas delegaria ao mesmo pipeline.  
Veredito: **REFUTADA**

**A6 — Early return ambíguo em `LandingPageStage`**  
Trecho do Plano: “Substituir early-return por fallback forçado apenas quando `force_storybrand_fallback`... se `status == "completed"` permitir análise oficial.”

  
Análise: plano determina explicitamente o novo comportamento; não há ambiguidade.  
Veredito: **REFUTADA**

**A7 — Limpeza de flags sem local definido**  
Trecho do Plano: “Limpar `state["force_storybrand_fallback"]` somente quando não estiver em modo debug...”.

  
Análise: o plano não indica em qual estágio isso deve ocorrer, apesar de existirem pontos potenciais (bootstrap, gate, callbacks). Ambiguidade permanece.  
Veredito: **CONFIRMADA**

**A8 — Formato SSE `state_delta` não especificado**  
Trecho do Plano: exemplo explícito de evento `Event(actions=EventActions(state_delta={"storybrand_fallback_meta": {...}}))`.

  
Análise: formato está descrito; a ADK já suporta `state_delta` (inclusive em fixtures de testes).  
Veredito: **REFUTADA**

**A9 — Preflight falha com payload parcial**  
Trecho do Plano: fase 1 envia somente StoryBrand e espera desbloqueio posterior.

  
Validação no Código: `extract_user_input` exige URL, formato, objetivo, persona etc. e retorna erro se ausentes.

  
Análise: com os requisitos atuais, um payload incompleto da fase 1 geraria 422; plano não trata isso.  
Veredito: **CONFIRMADA**

**A10 — Persistência frágil no frontend**  
Trecho do Plano: novos estados (`storybrandInputs`, `pendingCampaignPayload`) mantidos em memória local.

  
Código atual: `App.tsx` mantém todos os estados com `useState`, sem qualquer persistência em `localStorage` ou backend.

  
Análise: se a página recarregar entre as fases, o usuário perde o progresso; plano não propõe mitigação.  
Veredito: **CONFIRMADA**

**A11 — Compatibilidade retroativa não garantida**  
Trechos do Plano: separar `extract` em `storybrand_inputs/campaign_inputs` e afirmação de compatibilidade com flags/sessões legadas.

  
Código atual: preflight monta `initial_state` plano com chaves de topo (landing_page_url, objetivo_final, etc.), e diversas partes do agente assumem essas chaves planas.



  
Análise: migrar para estrutura aninhada quebraria consumidores existentes; o plano não descreve atualização/migração dessas dependências.  
Veredito: **CONFIRMADA**

**A12 — Tipos TS faltando (`phase`)**  
Código atual: interface `WizardStep` não possui campo `phase`; adicioná-lo exigiria alterar o tipo central.

  
Análise: plano pede `phase` nos passos, mas não lista a atualização do tipo; sem isso, TS acusará erro.  
Veredito: **CONFIRMADA**

**A13 — Matriz de testes sem fixtures/mocks**  
Trechos do Plano: lista cenários, porém não define fixtures/mocks necessários nas seções 2.8 e 5.

  
Análise: ausência de instruções sobre setup compartilhado deixa lacuna operacional para testes.  
Veredito: **CONFIRMADA**

**A14 — Rollback parcial não trata dados já persistidos**  
Trecho do Plano: rollback apenas desativa flags.

  
Código atual: persistência inclui `storybrand_fallback_meta` completo no estado/meta final.

  
Análise: se novos campos forem gravados, desativar flags não remove registros; plano não explica como lidar com dados históricos.  
Veredito: **CONFIRMADA**

**A15 — Glossário sem novas flags**  
Trecho do Plano: lista completa das flags existentes, sem necessidade de novas chaves para o bootstrap (plano explicita “mantidas, sem rename”).

  
Análise: não há flags novas a documentar; alegação carece de fundamento.  
Veredito: **REFUTADA**

**A16 — Tratamento de erros ausente**  
Trechos do Plano: seções 3.4–3.6 abordam estados e logs, mas não preveem timeouts/SSE falhando/aba fechada.

  
Análise: lacuna real; nenhum mecanismo adicional de resiliência proposto.  
Veredito: **CONFIRMADA**

**A17 — Falta doc de migração/rollout**  
Trecho do Plano: seção 7 resume rollback e observabilidade; não há plano de migração gradual ou sessões em andamento.

  
Análise: ausência confirmada.  
Veredito: **CONFIRMADA**

**Achados Transversais**
- Dependência excessiva do novo campo `storybrand_fallback_meta.status` impacta múltiplas alegações (A1, A3, A7, A14, A16).  
- A arquitetura faseada exige repensar preflight e persistência; sem isso, fluxos legados quebram (A9, A10, A11).  
- Documentação operacional insuficiente (rollback, migração, testes) aparece em várias inconsistências (A13, A14, A17).

**Recomendações Objetivas**
- Atualizar plano com a definição completa de `storybrand_fallback_meta` (inicialização antes do bootstrap, compatibilidade com `fallback_engaged`) e roteiro de migração das sessões existentes.



- Descrever pontos exatos de limpeza de `force_storybrand_fallback` e estratégias de resiliência (retries SSE, timeout) no backend/frontend.



- Ajustar plano de preflight para aceitar payload parcial (nova API/param `phase`) ou detalhar fallback seguro quando campos faltarem.



- Incluir atualização do tipo `WizardStep` e fixtures/mocks necessários na seção de testes para garantir viabilidade do plano.



- Expandir seção 7 com guia de migração/rollback que trate dados já gravados e sessões em andamento (scripts, flags adicionais, limpeza).



**Apêndice**
- Comandos utilizados: `rg`, `sed -n`, `nl -ba`, `find`.
- Glossário rápido: `fallback_engaged` (bool atual), `storybrand_fallback_meta.status` (campo proposto), `storybrand_inputs/campaign_inputs` (estrutura planejada para o estado inicial).  
- Nenhum commit/PR gerado; auditoria apenas documental.

**Testing**
- ⚠️ `tests não executados (auditoria documental)`
