---
description: Iniciar fluxo multi-agente completo automaticamente
argument-hint: [descrição da tarefa]
---

# Start Task - Fluxo Automatizado

Você recebeu uma solicitação para iniciar uma nova tarefa no sistema multi-agente.

## Instruções

1. **Gerar Task ID único**:
   ```
   TASK-[YYYYMMDD]-[HHMM]
   Exemplo: TASK-20251007-1430
   ```

2. **Criar brief inicial**:
   Salvar em `.claude/plans/task-init.json`:
   ```json
   {
     "task_id": "[gerado]",
     "created_at": "[ISO timestamp]",
     "description": "$ARGUMENTS",
     "requested_by": "user",
     "initial_phase": "checklist"
   }
   ```

3. **Invocar Checklist Agent**:
   Use checklist-agent para analisar a tarefa descrita em $ARGUMENTS

4. **Reportar Próximo Passo**:
   Baseado no veredito do Checklist:
   - `complete`: "✅ Requisitos validados. Prosseguindo para Writer Agent..."
   - `needs_clarification`: "❓ Checklist identificou gaps. Perguntas:"
   - `incomplete`: "⚠️ Tarefa incompleta. Por favor reformule com mais detalhes."

## Automações Ativas
- SessionStart hook já carregou contexto inicial
- PreToolUse hook validará file boundaries
- PostToolUse hook formatará código automaticamente