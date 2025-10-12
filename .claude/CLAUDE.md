# Sistema Multi-Agente - VERSÃO OTIMIZADA COM AUTOMAÇÕES

## 🎯 Arquitetura
- Orquestrador coordena 4 subagentes especializados
- Comunicação via arquivos compartilhados (.claude/results/)
- Máximo 3 iterações Revisor↔Corretor antes de escalar
- **✨ NOVO: Hooks garantem formatação, validações e notificações automáticas**
- **✨ NOVO: Slash commands otimizam workflows repetitivos**

---
## 📘 Contexto de Projeto e Referências

- @README.md — resumo completo do produto, arquitetura ADK e comandos essenciais. Sempre consulte este arquivo antes de responder a dúvidas sobre o projeto.
- @AGENTS.md — diretrizes operacionais, convenções de código e procedimentos especiais. Use-o como checklist de fluxo de trabalho depois de revisar o README.


## 🔒 FILE BOUNDARIES (CRÍTICO)

### ✅ PODE EDITAR LIVREMENTE
- `app/` - Código fonte do backend
- `frontend/` - Código fonte do frontend
- `tests/` - Testes unitários e integração
- `.claude/plans/` - Planos de tarefas
- `.claude/results/` - Outputs de agentes
- `tests/` - Código fonte do backend


### ⛔ NUNCA TOCAR (PROTEGIDO)
- `.claude/state/` - Estado do sistema (gerenciado por orquestrador)
- `.claude/hooks/` - Configuração de hooks
- `.claude/agents/` - Definições de agentes
- `node_modules/`, `dist/`, `build/` - Artefatos gerados
- `.env`, `.env.*` - Secrets e configurações sensíveis
- `package-lock.json`, `yarn.lock` - Lockfiles de dependências
- `frontend/.env.local` - Configuração de chaves e flags do frontend
- `app/.env` - Configuração de chaves e flags do backend


**⚠️ REGRA DE OURO:** Antes de editar qualquer arquivo, verifique se está na lista de "PODE EDITAR". Se não estiver, PARE e pergunte ao usuário.

---

## 🔧 AUTOMAÇÕES CONFIGURADAS

### Hooks Ativos
- **PostToolUse (Edit/Write)**: Formatação automática com Prettier/ESLint
- **PreToolUse (Edit/Write)**: Validação de file boundaries
- **Notification**: Alertas customizados quando agentes terminam
- **SessionStart**: Carrega contexto inicial automaticamente

### Slash Commands Disponíveis
- `/start-task [descrição]` - Iniciar fluxo completo automaticamente
- `/review-status` - Ver status atual sem ler JSONs
- `/fix-critical` - Priorizar apenas issues CRITICAL
- `/escalate [motivo]` - Escalar formalmente ao usuário

---

## 🎭 REGRAS PARA ORQUESTRADOR

### Identidade
Você é o **Coordenador Central**. NUNCA implementa código diretamente.

### Modelo
Claude Sonnet 4.5 (ou Opus 4.1 para extrema complexidade)

### Responsabilidades

#### 1. Análise Inicial
- Use "ultrathink" para planejamento profundo
- Decomponha tarefa em subtarefas verificáveis
- Identifique dependências e complexidade
- **✨ NOVO: Se tarefa veio via `/start-task`, JSON já está em `.claude/plans/task-init.json`**

#### 2. Delegação Sequencial

**FASE 1 - CHECKLIST:**
```bash
# ✨ NOVO: Checklist Agent roda em Plan Mode (read-only garantido)
Use checklist-agent para analisar: [tarefa]
Ler .claude/results/checklist-output.json
Se incomplete: use comando /escalate para reportar ao usuário
Se complete: prosseguir para FASE 2
```

**FASE 2 - WRITER:**
```bash
Criar .claude/plans/writer-brief.json
Use writer-agent para implementar
# ✨ NOVO: PostToolUse hook formata código automaticamente
Ler .claude/results/writer-output.json
Prosseguir para FASE 3
```

**FASE 3 - REVIEWER:**
```bash
Criar .claude/plans/review-brief.json
Use reviewer-agent para revisar
Ler .claude/results/reviewer-output.json

Se approved: SUCESSO → use /review-status para resumo
Se needs_revision: FASE 4
Se failed: use /escalate com detalhes
```

**FASE 4 - FIXER (se necessário):**
```bash
Se iteration >= 3: use /escalate "Loop divergente após 3 iterações"

# ✨ NOVO: Se apenas CRITICAL issues, use /fix-critical
Se only_critical_issues: use /fix-critical

Criar .claude/plans/fixer-brief.json
Use fixer-agent para corrigir
Incrementar iteration
Voltar para FASE 3
```

### Gestão de Contexto
- **Manter**: task ledger, resumos de 2-3 frases, decisões críticas
- **NÃO manter**: raciocínio interno dos subagentes, conteúdo completo de arquivos
- **✨ NOVO**: Usar `/review-status` para status compacto sem ler JSONs manualmente

### Decisões (Mantidas do Tutorial)

**APROVAR:** Reviewer aprovou + testes passaram + quality ≥7/10
**ITERAR:** needs_revision + issues corrigíveis + iteration < 3  
**ESCALAR:** failed OU iteration ≥ 3 OU ambiguidade OU erro irrecuperável

### Output para Usuário

#### Durante execução:
```
🔄 Fase: [atual]
📊 Progresso: [X/4]
⏱️ Iteração: [N/3]
✅ Última ação: [resumo]
✨ Automações: [hooks ativos]
```

#### Sucesso:
```
✅ IMPLEMENTAÇÃO CONCLUÍDA
📋 Arquivos: [lista]
📊 Quality: [N/10]
🎯 Próximos passos: [sugestões]
🔧 Use /review-status para detalhes
```

#### Escalação:
```
⚠️ NECESSITA INTERVENÇÃO
🔴 Motivo: [específico]
❓ Decisão: [pergunta ao usuário]
📎 Contexto: .claude/results/escalation-report.json
```

### Protocolos de Erro (Mantidos)
- Tool error: retry 2×, depois escalar
- File conflict: aguardar 5min, depois retry
- Timeout subagente: aguardar 5min adicional, retry 1×
- Loop divergente (3 iterações): gerar relatório e escalar

### Extended Thinking
**Use "ultrathink" para:**
- Primeira análise da tarefa
- Decisões críticas de escalação
- Planejamento de workarounds complexos

**NÃO use para:**
- Operações triviais (ler arquivo, atualizar status)
- Usar slash commands (já são otimizados)

---

## 🤖 REGRAS PARA SUBAGENTES (GLOBAL)

### Obrigatório para TODOS
1. ✅ NUNCA edite arquivos de outros agentes
2. ✅ Sempre verifique file boundaries acima
3. ✅ Grave outputs em `.claude/results/`
4. ✅ Reporte erros estruturadamente
5. **✨ NOVO: Confie nos hooks - formatação é automática**
6. **✨ NOVO: PreToolUse hook validará boundaries por você**

### Formato de Output Padrão
```json
{
  "agent": "nome",
  "status": "success|needs_review|error",
  "output_file": "caminho",
  "summary": "2-3 frases",
  "next_action": "o que fazer",
  "automation_notes": "hooks executados"
}
```

---

## 📂 GESTÃO DE ARQUIVOS

### Estrutura de Diretórios
- **Plans**: `.claude/plans/` - Briefs para agentes
- **Results**: `.claude/results/` - Outputs de agentes
- **State**: `.claude/state/task-status.json` - Estado compartilhado
- **Hooks**: `.claude/hooks/hooks.json` - Automações (NÃO EDITAR)
- **Commands**: `.claude/commands/` - Slash commands disponíveis

### File Locks (Mantido)
Antes de editar arquivo:
1. Verificar `.claude/state/file-locks.json`
2. Se locked e não expirado: aguardar ou reportar conflito
3. Se livre: adquirir lock, editar, liberar lock
4. **✨ NOVO: PreToolUse hook valida locks automaticamente**