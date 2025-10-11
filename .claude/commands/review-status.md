---
description: Ver status atual da tarefa sem ler JSONs manualmente
---

# Review Status - Resumo Compacto

Forneça um resumo estruturado do estado atual da tarefa.

## Instruções

1. **Ler** `.claude/state/task-status.json`

2. **Extrair informações chave**:
   - Task ID
   - Fase atual e iteração
   - Últimas ações completadas
   - Issues pendentes (por severity)
   - Quality scores

3. **Formatar output**:
   ```
   📊 [TASK_ID]
   🔄 Fase: [fase atual] (iteração X/3)
   
   ✅ Fases Completadas:
   - Checklist: [verdict] (score X.X)
   - Writer: [status] (X tests passing)
   - Reviewer: [verdict] (X issues)
   
   ⚠️ Issues Pendentes:
   - CRITICAL: X
   - HIGH: Y
   - MEDIUM: Z
   
   📊 Quality: X.X/10
   
   🎯 Próxima Ação: [next_action]
   ```

## Sem Necessidade de Extended Thinking
Este comando é uma operação de leitura simples. Use "think" apenas se houver ambiguidade no estado.