---
description: Priorizar correção apenas de issues CRITICAL
---

# Fix Critical - Foco em Bloqueadores

Você recebeu instrução para focar APENAS em issues CRITICAL.

## Instruções

1. **Ler último relatório do Reviewer**:
   `.claude/results/reviewer-output-iter[N].json`

2. **Filtrar apenas CRITICAL**:
   ```json
   critical_issues = [issue for issue in issues if issue.severity == "critical"]
   ```

3. **Se nenhum CRITICAL**:
   ```
   ✅ Sem issues CRITICAL pendentes!
   Revisor pode aprovar ou iterar em HIGH/MEDIUM se necessário.
   ```

4. **Se há CRITICAL**:
   - Criar brief para Fixer Agent focado APENAS nesses issues
   - Definir `priority_fixes` = IDs dos CRITICAL
   - Definir `time_budget` = "focus_critical_only"
   - Invocar fixer-agent

5. **Após correção**:
   - Retornar para Reviewer para validar
   - Se CRITICAL resolvidos → aprovar mesmo com MEDIUM/LOW pendentes
   - Se CRITICAL persistem → escalar ao usuário

## Vantagem
Este comando permite aprovar tarefas rapidamente quando apenas issues não-bloqueadores permanecem, acelerando o fluxo sem sacrificar segurança.