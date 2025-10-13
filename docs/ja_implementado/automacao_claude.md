# Plano de Restauração de Templates do Sistema Multi-Agente

## Objetivos
- Reconstituir templates oficiais de briefings (`.claude/plans`) e outputs (`.claude/results`) alinhados às estruturas descritas em `.claude/docs/multiagentes_claude_code.md` e `.claude/docs/complementacao_claude_code.md`.
- Garantir que arquivos operacionais sejam sempre gerados a partir desses modelos, evitando desgaste após cada iteração do pipeline.
- Atualizar o manual (`.claude/CLAUDE.md`) e disponibilizar um script de restauração que o próprio Claude Code pode executar em segurança.

## Etapas Planejadas

### 1. Análise e Preparação
- Revisar novamente as seções 4.1–4.5 da documentação principal e os acréscimos do arquivo complementar para confirmar campos obrigatórios, ordem das chaves e nomes de arquivos.
- Verificar se existem dados relevantes nos arquivos atuais de `.claude/plans/` e `.claude/results/`; caso necessários para histórico, arquivar manualmente antes de prosseguir.

### 2. Estrutura de Diretórios
- Criar (ou garantir existência de) `.claude/plans/templates/` e `.claude/results/templates/` com permissões normais de leitura.
- Limpar o conteúdo das pastas operacionais (`.claude/plans/` e `.claude/results/`) apenas após o backup do passo anterior, mantendo-as prontas para receber cópias dos modelos.

### 3. Templates de Brief (Planos)
Criar os arquivos abaixo em `.claude/plans/templates/`, usando exatamente os campos previstos na documentação (placeholders `<...>` para valores variáveis):

1. `task-init.template.json`
```json
{
  "task_id": "<TASK_ID>",
  "created_at": "<ISO_TIMESTAMP>",
  "description": "<USER_REQUEST_SUMMARY>",
  "requested_by": "user",
  "initial_phase": "checklist"
}
```
2. `checklist-brief.template.json`
```json
{
  "task_id": "<TASK_ID>",
  "task_type": "<feature|bugfix|refactor>",
  "description": "<PLAIN_TEXT_DESCRIPTION>",
  "context": {
    "project_info": "<PROJECT_SUMMARY>",
    "relevant_files": [],
    "constraints": [],
    "validation_report": null,
    "critical_blockers": []
  }
}
```
3. `writer-brief.template.json`
```json
{
  "task_id": "<TASK_ID>",
  "requirements": {
    "checklist_analysis_file": ".claude/results/checklist-output.json",
    "explicit_requirements": [],
    "implicit_requirements": [],
    "acceptance_criteria": []
  },
  "expected_outputs": {
    "files_to_create": [],
    "files_to_modify": [],
    "files_to_delete": [],
    "tests_to_create": []
  },
  "testing_requirements": {
    "coverage_target": 80,
    "test_types": ["unit", "integration"],
    "test_strategy": "<TEST_APPROACH_NOTES>"
  },
  "project_context": "<RELEVANT_BACKGROUND>",
  "critical_notes": []
}
```
4. `review-brief.template.json`
```json
{
  "task_id": "<TASK_ID>",
  "iteration": 1,
  "references": {
    "checklist_analysis": ".claude/results/checklist-output.json",
    "writer_output": ".claude/results/writer-output.json",
    "previous_reviewer_output": null
  },
  "review_focus": {
    "priority_areas": [],
    "acceptance_criteria_reference": [],
    "testing_expectations": []
  }
}
```
5. `fixer-brief.template.json`
```json
{
  "task_id": "<TASK_ID>",
  "iteration": 1,
  "review_report": ".claude/results/reviewer-output.json",
  "priority_fixes": [],
  "time_budget": "<30min|60min|120min>",
  "focus": "critical_and_high_only"
}
```

### 4. Templates de Resultados
Criar os modelos em `.claude/results/templates/`, mantendo campos, tipos e nomes fiéis às seções 4.1–4.5:

1. `checklist-output.template.json`
```json
{
  "agent": "checklist-agent",
  "task_id": "<TASK_ID>",
  "verdict": "complete",
  "analysis": {
    "clarity_score": 0,
    "completeness_score": 0,
    "feasibility_score": 0,
    "overall_score": 0
  },
  "requirements": {
    "explicit": [],
    "implicit": [],
    "acceptance_criteria": []
  },
  "gaps": [],
  "next_action": "proceed_to_implementation"
}
```
2. `writer-output.template.json`
```json
{
  "agent": "writer-agent",
  "task_id": "<TASK_ID>",
  "status": "success",
  "implementation_summary": {
    "description": "<WHAT_WAS_DONE>",
    "approach": "<HOW_IT_WAS_DONE>",
    "key_decisions": []
  },
  "files_changed": {
    "created": [],
    "modified": [],
    "deleted": []
  },
  "tests_created": {
    "files": [],
    "coverage": {
      "lines": 0,
      "branches": 0
    },
    "tests_passed": 0,
    "tests_failed": 0
  },
  "validation": {
    "linter": { "status": "passed" },
    "type_checker": { "status": "passed" },
    "tests": { "status": "passed" },
    "build": { "status": "passed" }
  },
  "self_assessment": {
    "confidence": "high",
    "quality_score": 0,
    "ready_for_review": true
  },
  "next_action": "ready_for_review"
}
```
3. `reviewer-output.template.json`
```json
{
  "agent": "reviewer-agent",
  "task_id": "<TASK_ID>",
  "verdict": "approved",
  "overall_assessment": {
    "summary": "<SHORT_SYNTHESIS>",
    "completeness_score": 0,
    "correctness_score": 0,
    "security_score": 0,
    "quality_score": 0,
    "overall_score": 0
  },
  "acceptance_criteria_review": [],
  "issues": [],
  "tests_review": {
    "status": "passed",
    "coverage": {
      "lines": 0
    },
    "gaps": []
  },
  "next_action": {
    "action": "approve",
    "priority_fixes": [],
    "estimated_effort": "0min"
  }
}
```
4. `fixer-output.template.json`
```json
{
  "agent": "fixer-agent",
  "task_id": "<TASK_ID>",
  "iteration": 1,
  "status": "success",
  "fixes_applied": [],
  "fixes_attempted_but_failed": [],
  "fixes_skipped": [],
  "overall_validation": {
    "linter": { "status": "passed", "errors": 0 },
    "type_checker": { "status": "passed" },
    "tests": {
      "status": "passed",
      "total": 0,
      "passed": 0,
      "failed": 0
    },
    "build": { "status": "passed" }
  },
  "summary": {
    "total_issues": 0,
    "fixed": 0,
    "failed": 0,
    "skipped": 0,
    "critical_resolved": "0%",
    "high_resolved": "0%",
    "medium_resolved": "0%"
  },
  "remaining_issues": [],
  "next_action": {
    "recommendation": "send_back_to_reviewer",
    "reason": "<RATIONALE>",
    "expected_verdict": "approved"
  }
}
```

### 5. Replicação Inicial
- Copiar cada template recém-criado para as pastas operacionais correspondentes, removendo dados antigos.
- Confirmar que os arquivos resultantes não contêm referências a tarefas passadas (IDs, datas, nomes de arquivo específicos).

### 6. Atualização do `.claude/CLAUDE.md`
- Acrescentar instruções explícitas na seção “FILE BOUNDARIES” indicando que `templates/` é somente leitura e que `.claude/plans/` + `.claude/results/` devem ser tratados como buffers de trabalho.
- Inserir checklist operacional para o orquestrador: “copiar templates → preencher → executar agentes”.
- Mencionar o script de reset (passo seguinte) e quando utilizá-lo.

### 7. Script de Reset Automatizado
- Implementar `.claude/scripts/reset_claude_templates.py` com as ações:
  - Encontrar todos os `*.template.json` em `plans/templates` e `results/templates`.
  - Copiar substituindo os arquivos “correntes” (mesmo nome sem `.template`) nas pastas operacionais.
  - Ignorar `.claude/state/` e demais diretórios protegidos.
  - Exibir resumo das cópias efetuadas para auditoria.
- Testar o script com `python3` para assegurar compatibilidade com as permissões listadas em `.claude/settings*.json`.

### 8. Verificações Finais
- Executar o script recém-criado e inspecionar `git diff` para validar o conteúdo dos arquivos regenerados.
- Rodar `/memory` ou `/review-status` em Claude Code para confirmar que o fluxo reconhece os arquivos limpos.
- Caso necessário, atualizar README/automação complementar para refletir o novo processo.

## Considerações
- `.claude/state/` permanece intocado durante todo o processo.
- Qualquer alteração futura em formatos deve ocorrer primeiro nos templates; em seguida, o script de reset deve ser executado para propagar a mudança.
- Ao adicionar novos subagentes, incluir os respectivos templates nas pastas de modelos e atualizar o script para contemplá-los.
