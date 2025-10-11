---
description: Escalar formalmente ao usuário com contexto completo
argument-hint: [motivo da escalação]
---

# Escalate - Reportar ao Usuário

Você recebeu instrução para escalar uma decisão ao usuário.

## Instruções

1. **Criar relatório estruturado**:
   Salvar em `.claude/results/escalation-report.json`:
   ```json
   {
     "task_id": "[atual]",
     "escalated_at": "[ISO timestamp]",
     "escalated_by": "orchestrator",
     "reason": "$ARGUMENTS",
     "context": {
       "current_phase": "...",
       "iteration": X,
       "last_actions": [...],
       "blocking_issues": [...]
     },
     "options": [
       {
         "option": "A",
         "description": "...",
         "pros": [...],
         "cons": [...]
       }
     ],
     "recommendation": "..."
   }
   ```

2. **Formatar mensagem ao usuário**:
   ```
   ⚠️ ESCALAÇÃO NECESSÁRIA
   
   🔴 Motivo: $ARGUMENTS
   
   📊 Contexto:
   - Task: [ID]
   - Fase: [atual]
   - Iteração: X/3
   
   📋 Situação:
   [Resumo do que aconteceu]
   
   🤔 Opções:
   A) [opção 1]
      Prós: ...
      Contras: ...
   
   B) [opção 2]
      Prós: ...
      Contras: ...
   
   💡 Recomendação: [sua sugestão]
   
   ❓ Como gostaria de prosseguir?
   ```

3. **Aguardar decisão do usuário**

## Use Cases
- Loop divergente (3+ iterações)
- Requisitos ambíguos (checklist incomplete)
- Falha crítica irrecuperável
- Trade-off complexo requer decisão humana

---