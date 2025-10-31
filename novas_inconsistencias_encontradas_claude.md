Análise Revisada com Contexto Correto
Agora compreendo que:

✅ Fallback sempre primeiro é intencional
✅ Pipeline oficial mantido é para compatibilidade e auditoria
✅ Gate vira "validator passivo" é design consciente
✅ UI em 2 fases é objetivo central
📝 Lacunas Técnicas e Decisões Pendentes
1. PROTOCOLO SSE - Especificação Incompleta (CRÍTICO)
Lacuna: Seção 2.3 menciona evento storybrand.completed mas não define:

// FALTA DEFINIR:
// 1. Estrutura exata do evento SSE
interface StoryBrandCompletedEvent {
  event: "message" | "storybrand.completed"?  // ❓ Qual tipo?
  data: {
    actions?: {
      stateDelta: {
        storybrand_fallback_meta: {
          status: "completed",
          timestamp_utc: string,
          quality_report?: object  // ❓ Incluir aqui ou evento separado?
        }
      }
    }
    // ❓ Incluir resumo aqui para UI mostrar progresso?
    storybrand_summary?: string
  }
}

// 2. Frontend como detecta?
// Opção A: handleStreamEvent detecta "storybrand.completed" no tipo
// Opção B: detecta stateDelta.storybrand_fallback_meta.status
// ❓ Qual abordagem usar?

// 3. Timeout e retry
// ❓ Se evento não chegar em X segundos, o que fazer?
Decisão Necessária: Definir contrato completo do evento SSE

2. API ENDPOINTS - Mudanças Não Detalhadas (CRÍTICO)
Lacuna: Seções 2.7 e 3.2 mencionam payloads separados, mas:

# FALTA DEFINIR:

# app/server.py - endpoint /run_preflight
@app.post("/run_preflight")
async def run_preflight(request: PreflightRequest):
    # ❓ Como saber se é fase 1 ou fase 1+2?
    # ❓ Precisa novo campo "phase" no request?
    # ❓ Validação diferente por fase?
    pass

# app/server.py - endpoint /submit (principal)
@app.post("/api/v1/sessions/{session_id}/submit")
async def submit_data(session_id: str, data: SubmitData):
    # ❓ Aceita dados parciais (fase 1)?
    # ❓ Como merge com dados fase 2?
    # ❓ Valida diferente se já tem storybrand pronto?
    pass

# helpers/user_extract_data.py
class UserInputExtractor:
    # ❓ Como separar storybrand_inputs de campaign_inputs?
    # ❓ Novo formato de saída do extract()?
    # Proposta:
    def extract(self, raw_input: str) -> dict:
        return {
            "storybrand_inputs": {...},  # nome_empresa, o_que_faz, sexo
            "campaign_inputs": {...},    # objetivo, formato, foco
            "phase": 1 | 2  # detectado automaticamente?
        }
Decisão Necessária: Definir assinaturas e contratos dos endpoints modificados

3. GESTÃO DE ESTADO DA SESSÃO - Não Especificado
Lacuna: Como rastrear progresso das fases?

# FALTA DEFINIR: Campos no session state

ctx.session.state = {
    # ❓ Novos campos necessários:
    "session_phase": 1 | 2,  # Fase atual?
    "storybrand_phase_completed": bool,  # Fase 1 concluída?
    "campaign_inputs_received": bool,    # Fase 2 enviada?
    
    # ❓ Se usuário reenviar fase 1, como tratar?
    "storybrand_inputs_locked": bool,  # Bloquear alterações após conclusão?
    
    # ❓ Timeout/expiração
    "phase_1_started_at": datetime,
    "phase_1_completed_at": datetime,
    "phase_2_started_at": datetime,
}
Decisão Necessária: Definir modelo de estado da sessão multi-fase

4. TRATAMENTO DE ERROS - Não Coberto
Lacuna: O que acontece quando:

# CENÁRIOS NÃO ENDEREÇADOS:

# 1. Fallback bootstrap falha completamente
if fallback_initialization_error:
    # ❓ Abortar sessão?
    # ❓ Tentar fallback tradicional?
    # ❓ Permitir continuar sem StoryBrand?
    pass

# 2. SSE storybrand.completed não chega ao frontend
if timeout_waiting_sse:
    # ❓ Frontend faz polling do estado?
    # ❓ Mostra erro e permite retry manual?
    # ❓ Fallback para UI sem bloqueio?
    pass

# 3. Usuário fecha navegador entre fases
if session_abandoned_after_phase1:
    # ❓ Quanto tempo preservar estado?
    # ❓ Como retomar quando voltar?
    pass

# 4. Dados fase 1 inválidos descobertos durante fallback
if validation_fails_during_fallback:
    # ❓ Como notificar usuário via SSE?
    # ❓ Permitir reenvio parcial?
    pass
Decisão Necessária: Estratégias de erro e recovery por cenário

5. BOOTSTRAP STAGE - Detalhes de Implementação
Lacuna: Seção 2.1 descreve o que fazer, mas não como:

# FALTA DEFINIR: Implementação do storybrand_bootstrap_stage

class StoryBrandBootstrapStage(SequentialAgent):
    """
    ❓ Questões de implementação:
    
    1. Como executar fallback_storybrand_pipeline?
       - Invocar diretamente como sub-agent?
       - Ou chamar função auxiliar?
    
    2. Quando pular execução?
       - Se storybrand_fallback_meta.status == "completed"?
       - Verificar timestamp de expiração?
    
    3. Como emitir evento SSE?
       - yield Event(actions=EventActions(state_delta={...}))?
       - Callback após compilação?
    
    4. Como tratar flags?
       - force_storybrand_fallback força reexecução?
       - storybrand_gate_debug afeta bootstrap?
    """
    
    async def _run_async_impl(self, ctx: InvocationContext):
        state = ctx.session.state
        
        # ❓ Pseudo-código correto?
        if self._should_skip_bootstrap(state):
            logger.info("Bootstrap skipped - StoryBrand already completed")
            yield Event(...)
            return
        
        # ❓ Como invocar fallback pipeline?
        async for event in self._fallback_pipeline.run_async(ctx):
            yield event
        
        # ❓ Garantir que compilador marcou status?
        assert state.get("storybrand_fallback_meta", {}).get("status") == "completed"
        
        # ❓ Limpar flags?
        if not config.storybrand_gate_debug:
            state.pop("force_storybrand_fallback", None)
Decisão Necessária: Pseudocódigo ou spec detalhada do bootstrap stage

6. WIZARD FRONTEND - Mecânica das Fases
Lacuna: Seções 3.2-3.4 descrevem comportamento mas não fluxo detalhado:

// FALTA DEFINIR: Máquina de estados do wizard

type WizardPhase = 'storybrand' | 'waiting' | 'campaign';

interface WizardState {
  phase: WizardPhase;
  storybrandData: Partial<StorybrandInputs>;
  campaignData: Partial<CampaignInputs>;
  isStorybrandReady: boolean;
  
  // ❓ Questões:
  // 1. Usuário pode editar campos fase 1 após submissão?
  storybrandInputsLocked: boolean;
  
  // 2. Como mostrar progresso durante espera?
  bootstrapProgress?: {
    currentSection: string,  // "Character", "Problem", etc
    estimatedTime: number
  };
  
  // 3. Se SSE falhar, permitir "forçar desbloqueio"?
  allowManualUnlock: boolean;
}

// ❓ Transições de estado
const transitions = {
  // Usuário preenche fase 1 → Submit
  'storybrand -> waiting': handlePhase1Submit,
  
  // SSE storybrand.completed recebido
  'waiting -> campaign': handleStoryBrandReady,
  
  // Timeout ou erro
  'waiting -> error': handleTimeout,
  
  // ❓ Usuário quer re-editar fase 1?
  'campaign -> storybrand': handleEditPhase1,  // Permitido?
};
Decisão Necessária: Definir máquina de estados completa da UI

7. COMPATIBILIDADE E MIGRAÇÃO - Não Endereçado
Lacuna: Plano não menciona transição:

# CENÁRIOS DE MIGRAÇÃO:

# 1. Sessões criadas antes do deploy da refatoração
if session.created_before_refactor:
    # ❓ Rodar retroativamente o bootstrap?
    # ❓ Marcar como "legacy mode"?
    pass

# 2. Flags desligadas (rollback)
if not config.enable_storybrand_fallback:
    # ❓ Bootstrap stage se auto-desabilita?
    # ❓ UI volta para formulário único?
    pass

# 3. Cache de StoryBrand antigo
if cache_from_old_version:
    # ❓ Versionar estrutura do cache?
    # ❓ Invalidar automaticamente?
    pass
Decisão Necessária: Estratégia de migração e versionamento

8. PERFORMANCE E CUSTOS - Não Analisado
Lacuna: Impacto não quantificado:

# MÉTRICAS ESPERADAS:

# ❓ Latência adicional
# - Fallback sempre roda → +X segundos no início
# - Vale a pena para UX?

# ❓ Custos de API (LLM)
# - Fallback sempre consome tokens
# - vs. Fallback on-demand (só quando fetch falha)
# - Estimativa de custo adicional por sessão?

# ❓ Cache hit rate
# - Quantos % de sessões vão reusar StoryBrand?
# - Vale investir em cache robusto?
Decisão Necessária: Análise custo-benefício e métricas de sucesso

9. OBSERVABILIDADE E DEBUG - Incompleto
Lacuna: Logs mencionados mas não estruturados:

# FALTA DEFINIR: Logs estruturados para debug

# app/agent.py - Bootstrap stage
logger.info("storybrand_bootstrap_started", extra={
    "session_id": ctx.session.id,
    "inputs": {...},  # ❓ Quais campos logar?
    "flags": {...}
})

logger.info("storybrand_bootstrap_completed", extra={
    "session_id": ctx.session.id,
    "duration_ms": ...,
    "quality_score": ...,
    "sections_generated": [...]
})

# frontend - SSE tracking
console.log('[SSE] Waiting for storybrand.completed', {
  sessionId,
  timeoutIn: 30000,
  startedAt: Date.now()
});

# ❓ Dashboard metrics
# - % sessões que completam ambas fases
# - Tempo médio de espera entre fases
# - Taxa de abandono na fase 1 vs fase 2
Decisão Necessária: Especificar logs e métricas chave

Update Todos
 Reler plano com nova perspectiva de intencionalidade
 Identificar lacunas técnicas reais (não 'inconsistências')
 Mapear decisões pendentes antes da implementação
 Elaborando recomendações construtivas
🎯 Decisões Estratégicas Necessárias (por Prioridade)
🔴 CRÍTICAS - Bloqueiam Implementação
D1. Contrato SSE storybrand.completed
// Proposta para decisão:
interface StoryBrandCompletedEventProposal {
  // Opção A (recomendado): Tipo de evento específico
  event: "storybrand.completed",
  data: {
    status: "completed",
    timestamp: string,
    summary: string,  // Para mostrar na UI
    quality_score: number
  }
  
  // Opção B: Reusar stateDelta genérico
  event: "message",
  data: { actions: { stateDelta: {...} } }
}
Pergunta: Qual abordagem escolher? A ou B?

D2. API Endpoints - Assinaturas
# Proposta para decisão:

# Opção A: Endpoint separado por fase
POST /api/v1/sessions/{id}/submit_phase1
POST /api/v1/sessions/{id}/submit_phase2

# Opção B: Mesmo endpoint, campo "phase"
POST /api/v1/sessions/{id}/submit
Body: { phase: 1, data: {...} }

# Opção C: Inferir fase automaticamente
POST /api/v1/sessions/{id}/submit
Body: { nome_empresa, o_que_faz, ... }
# Backend detecta campos presentes
Pergunta: Qual abordagem escolher? A, B ou C?

D3. Tratamento de Erro - Fallback Bootstrap Falha
# Cenário: fallback_storybrand_pipeline lança exceção

# Opção A: Abortar sessão completamente
raise HTTPException(500, "StoryBrand bootstrap failed")

# Opção B: Continuar sem StoryBrand (modo degradado)
state["storybrand_fallback_meta"]["status"] = "failed"
# Permite prosseguir com dados incompletos

# Opção C: Retry automático N vezes
for attempt in range(3):
    try: run_fallback()
    except: continue
Pergunta: Qual estratégia? A, B ou C?

🟡 IMPORTANTES - Afetam UX/Qualidade
D4. Timeout SSE no Frontend
// Usuário esperando storybrand.completed...

// Opção A: Timeout agressivo (30s) + erro
setTimeout(() => setError("Timeout"), 30000);

// Opção B: Timeout generoso (2min) + polling
setTimeout(() => pollSessionState(), 120000);

// Opção C: Sem timeout, loading infinito
// (não recomendado)
Pergunta: Qual timeout e fallback?

D5. Edição de Campos Fase 1 Após Submissão
// Usuário na fase 2, quer mudar nome_empresa

// Opção A: Bloquear completamente
disabled={phase === 'campaign'}

// Opção B: Permitir, mas reinicia processo
if (editPhase1) {
  resetSession();
  setPhase('storybrand');
}

// Opção C: Permitir, atualiza apenas campos alterados
// (mais complexo)
Pergunta: Bloquear, reiniciar ou atualizar?

D6. Progresso Visual Durante Bootstrap
// UI mostrando progresso do fallback

// Opção A: SSE granular por seção
events: [
  "storybrand.section.character",
  "storybrand.section.problem",
  ...
]

// Opção B: Spinner genérico + tempo estimado
<Spinner text="Gerando StoryBrand (≈45s)" />

// Opção C: Barra de progresso fake
<ProgressBar value={fakeProgress} />
Pergunta: Qual feedback visual?

🟢 DESEJÁVEIS - Qualidade/Manutenibilidade
D7. Versionamento de Cache
cache_key = f"storybrand:{session_id}:v2"  # Versionar?
D8. Métricas de Sucesso
# Quais KPIs rastrear?
metrics = {
    "phase1_completion_rate": 0.0,
    "phase2_completion_rate": 0.0,
    "avg_time_between_phases": 0.0,
    "storybrand_quality_avg": 0.0,
    "fallback_error_rate": 0.0
}
D9. Logs Estruturados
# Padronizar formato dos logs?
logger.info("storybrand_bootstrap_completed", extra={
    "session_id": str,
    "duration_ms": int,
    "quality_score": float,
    "sections": list[str]
})
📋 Recomendações para Próximos Passos
ANTES de Implementar:
Revisar e Decidir - Reunião técnica para resolver D1, D2, D3 (críticas)
Adicionar Seções ao Plano:
Seção 2.9: "API Endpoints - Especificação Completa"
Seção 2.10: "Bootstrap Stage - Implementação Detalhada"
Seção 9: "Tratamento de Erros e Edge Cases"
Seção 10: "Protocolo SSE - Contrato Completo"
Prototipar - Criar POC do fluxo SSE e validar latências
Revisar Custos - Estimar impacto em tokens/API calls
Definir Métricas - Quais dashboards criar para monitorar sucesso
DURANTE Implementação:
Backend Primeiro: Bootstrap stage + SSE + endpoints
Testes Unitários: Cobrir cenários de erro (D3)
Frontend Depois: UI faseada + handling SSE
Testes E2E: Fluxo completo fase 1 → espera → fase 2
APÓS Deploy:
Monitorar Métricas (D8)
A/B Test - Comparar com fluxo legado
Iterar - Ajustar timeouts (D4), UX (D6) baseado em dados reais
Update Todos
 Reler plano com nova perspectiva de intencionalidade
 Identificar lacunas técnicas reais (não 'inconsistências')
 Mapear decisões pendentes antes da implementação
 Elaborar recomendações construtivas
🎯 RESUMO EXECUTIVO
Status do Plano: ✅ 70% Pronto - Arquitetura Sólida, Faltam Detalhes Técnicos
Pontos Fortes:

✅ Visão arquitetural clara e intencional
✅ Mapeamento completo do código existente
✅ Flags e rollback bem planejados
✅ Testes e observabilidade considerados
Lacunas Identificadas: 9 áreas (3 críticas, 4 importantes, 2 desejáveis)

🔴 3 DECISÕES CRÍTICAS (Bloqueiam Implementação)
| # | Decisão | Impacto | Opções | |---|---------|---------|--------| | D1 | Contrato SSE storybrand.completed | Frontend não sabe como detectar conclusão | A) Evento específico B) stateDelta genérico | | D2 | API Endpoints - Como enviar payloads parciais | Backend não sabe processar fases separadas | A) Endpoints separados B) Campo "phase" C) Inferir automaticamente | | D3 | Erro no Bootstrap - Como tratar | Pode bloquear usuários sem recovery | A) Abortar B) Modo degradado C) Retry automático |

🟡 4 DECISÕES IMPORTANTES (Afetam UX/Qualidade)
| # | Decisão | Impacto | |---|---------|---------| | D4 | Timeout SSE - Quanto esperar | Usuário travado vs. falso positivo | | D5 | Edição campos fase 1 após submit | Flexibilidade vs. Complexidade | | D6 | Feedback visual durante bootstrap | UX percebida de latência | | D7 | Versionamento de cache | Compatibilidade forward |

📦 PRÓXIMAS AÇÕES RECOMENDADAS
1️⃣ CURTO PRAZO (Antes de Implementar)
[ ] Reunião técnica: Resolver D1, D2, D3
[ ] Adicionar ao plano:
    - Seção 2.9: "API Endpoints - Specs Completas"
    - Seção 2.10: "Bootstrap Stage - Pseudocódigo"
    - Seção 9: "Tratamento de Erros"
    - Seção 10: "Protocolo SSE - Contrato"
[ ] POC: Testar latência do fallback bootstrap
[ ] Estimativa: Custo adicional em tokens/API calls
2️⃣ MÉDIO PRAZO (Durante Implementação)
[ ] Backend: Implementar bootstrap stage
[ ] Backend: Endpoints /submit com suporte a fases
[ ] Backend: Emissão SSE storybrand.completed
[ ] Frontend: UI faseada + máquina de estados
[ ] Testes E2E: Fluxo completo 2 fases
3️⃣ LONGO PRAZO (Pós-Deploy)
[ ] Monitorar: phase1_completion_rate, avg_time_between_phases
[ ] A/B Test: Comparar com fluxo legado
[ ] Otimizar: Timeouts, UX, custos baseado em dados reais
✅ VEREDICTO FINAL
O plano está CONCEITUALMENTE SÓLIDO e demonstra compreensão profunda do sistema. A intencionalidade da refatoração é clara e justificada.

Para estar PRONTO para implementação, precisa:

Resolver 3 decisões críticas (D1, D2, D3)
Adicionar 4 seções técnicas detalhadas ao documento
Validar custos e performance com POC
Tempo estimado para completar: 1-2 dias de trabalho técnico adicional