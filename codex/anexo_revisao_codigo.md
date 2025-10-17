# Anexo – Revisão de Código Implementado (Template de Auditoria)

Estas instruções complementam `.claude/CLAUDE.md` e `AGENTS.md`, sendo obrigatórias sempre que for necessário validar entregas concluídas comparando **plano original (.md) vs código-fonte implementado**. Devem ser aplicadas após sincronizar o repositório com o trabalho executado pelos subagentes (Writer, Fixer, etc.) ou qualquer outra fonte.

## Contexto do Fluxo Multi-Agente

Este documento se integra ao fluxo definido em `.claude/CLAUDE.md`:
- **Writer/Fixer** implementam código baseado no plano especificado em `.claude/plans/`
- **Reviewer** valida a implementação, mas pode não detectar inconsistências sutis com o plano original
- **Esta auditoria** atua como validação adicional, comparando sistematicamente o plano original com o código-fonte final

**IMPORTANTE:** Ao invocar esta auditoria, especifique no prompt:
- **Plano original a auditar:** caminho do arquivo do plano (ex.: `codex/plans/feature_xyz.md`)
- **Fase/seção do plano:** identificador da fase concluída (ex.: "Fase 2.1 - Implementação do endpoint")
- **Escopo de arquivos (opcional):** lista de arquivos/diretórios a auditar (ex.: `app/`, `tests/test_feature.py`)

## 1. Objetivo

Garantir que cada fase/seção concluída no **plano original** foi implementada exatamente conforme especificado, observando:

- **Cobertura integral:** todas as subtarefas, requisitos e entregáveis descritos no plano foram implementados
- **Aderência ao design:** estruturas, contratos, nomenclaturas e comportamentos seguem exatamente o plano
- **Conformidade com diretrizes:** código segue convenções de `AGENTS.md` e padrões do projeto
- **Ausência de regressões:** alterações não introduzem bugs ou quebram funcionalidades existentes
- **Evidências concretas:** código-fonte, testes e documentação comprovam a implementação

## 2. Escopo

A auditoria deve ocorrer **fase a fase** ou **seção a seção** do plano. Para cada rodada:

1. **Localizar a seção no plano:** identifique no plano original a fase/seção que foi implementada (ex.: "Fase 2: Implementação do Backend", "Seção 3.2: Validação de Schemas")
2. **Extrair requisitos:** liste todos os requisitos, entregáveis, arquivos, funções, classes, testes e comportamentos descritos naquela seção
3. **Mapear código-fonte:** identifique os arquivos e linhas onde a implementação deveria estar
4. **Comparar plano vs código:** valide se cada requisito do plano está presente e correto no código
5. **Avaliar completude:** verifique testes, documentação, logs, tratamento de erros e efeitos colaterais
6. **Produzir relatório:** documente achados com evidências (`arquivo:linha`) e severidade (P0-P3)

## 3. Preparação Obrigatória

Antes de iniciar a revisão, execute estas etapas:

### 3.1 Leitura de Contexto
- **Leia `AGENTS.md`:** contextualize dependências, feature flags, convenções de testes e responsabilidades do projeto
- **Leia `.claude/CLAUDE.md`:** entenda o fluxo multi-agente e file boundaries
- **Leia o plano original completo:** compreenda o escopo total antes de auditar uma fase específica

### 3.2 Localização da Fase
- **Identifique a seção no plano:** localize exatamente qual fase/seção foi solicitada no prompt de auditoria
- **Extraia requisitos:** liste TODOS os requisitos, entregáveis, arquivos mencionados, funções/classes esperadas, testes descritos, comportamentos especificados

### 3.3 Sincronização e Ferramentas
- **Sincronize repositório:** execute `git pull` para trabalhar no código mais recente
- **Identifique commit-alvo:** se especificado no prompt, checkout no commit pós-implementação
- **Configure ferramentas:** prepare Read, Grep, Glob, diff viewers para navegar código eficientemente

## 4. Procedimento de Revisão

Siga estas etapas sistematicamente para cada fase auditada:

### 4.1 Mapeamento Plano → Código
Para cada requisito/entregável listado no plano:

- **Identifique menções explícitas:** arquivos, classes, funções, variáveis, constantes, endpoints, schemas
- **Use ferramentas de busca:** Grep para encontrar símbolos, Glob para localizar arquivos
- **Registre localizações:** documente `arquivo:linha` de cada implementação encontrada
- **Marque ausências:** anote requisitos do plano NÃO encontrados no código (potenciais P0/P1)

### 4.2 Verificação de Conformidade
Para cada implementação encontrada:

- **Assinaturas:** valide tipos de parâmetros, retornos, exceções (ex.: `def process(data: dict[str, Any]) -> Result`)
- **Nomenclatura:** confirme nomes exatos de funções, classes, variáveis conforme plano
- **Comportamento:** verifique lógica, condicionais, loops, tratamento de casos especiais descritos no plano
- **Integrações:** valide imports, chamadas a outras funções, callbacks, atualizações de estado
- **Valores default:** confirme constantes, configurações, flags conforme especificado

### 4.3 Análise de Testes
- **Existência:** verifique se arquivos de teste mencionados no plano existem (ex.: `tests/test_feature.py`)
- **Cobertura de casos:** valide testes para happy-path, edge cases, falhas, fallbacks descritos no plano
- **Conformidade com ferramentas:** execute `pytest`, `mypy`, `ruff` se aplicável
- **Assertions específicas:** confirme asserts para comportamentos críticos mencionados no plano

### 4.4 Documentação e Observabilidade
- **Documentação inline:** verifique docstrings, comentários críticos quando exigidos no plano
- **Documentação externa:** valide atualizações em README, AGENTS.md, playbooks se mencionados
- **Logs estruturados:** confirme mensagens de log, campos, níveis (INFO/ERROR) descritos no plano
- **Métricas:** valide exposição de métricas, SSE events, audit trails quando especificados

### 4.5 Detecção de Riscos e Side-Effects
- **Regressões:** busque alterações em código legado não mencionadas no plano (use git diff)
- **Feature flags:** valide comportamento com flag ativada/desativada conforme plano
- **Mudanças fora do escopo:** identifique arquivos modificados não listados no plano, avalie se justificados
- **Lacunas de qualidade:** detecte código sem testes, sem tipagem, sem validação de entrada
- **Compatibilidade:** verifique impactos em integrações, APIs externas, banco de dados

## 5. Critérios de Sucesso

A fase revisada só é considerada **APROVADA** se **TODOS** os itens abaixo forem verdadeiros:

✅ **Completude:**
- Todos os requisitos, entregáveis e subtarefas descritos no plano foram implementados
- Nenhum item obrigatório do plano está ausente no código

✅ **Conformidade com Design:**
- Estruturas de dados, contratos de API, schemas seguem exatamente o especificado
- Nomenclatura de funções, classes, variáveis corresponde ao plano
- Comportamentos, lógica de negócio, fluxos implementados conforme descrito

✅ **Qualidade de Testes:**
- Testes mencionados no plano existem e passam
- Cobertura de casos (happy-path, edge cases, erros) está completa
- Nenhum teste falha ao executar `pytest`

✅ **Documentação e Observabilidade:**
- Documentação inline/externa atualizada quando exigido no plano
- Logs estruturados, métricas, eventos SSE implementados conforme especificado

✅ **Ausência de Regressões:**
- Código legado não foi alterado inadvertidamente
- Feature flags preservam comportamento original quando desativados
- Nenhuma funcionalidade existente foi quebrada

✅ **Conformidade com Diretrizes:**
- Código segue convenções de `AGENTS.md` (estilo, lint, tipagem)
- File boundaries respeitados (somente arquivos permitidos foram editados)
- Nenhuma violação de segurança introduzida

## 6. Classificação de Achados (Findings)

Classifique cada inconsistência encontrada conforme severidade:

### P0 - BLOQUEANTE (Requer correção imediata)
Implementação **PARA** até corrigir. Exemplos:
- ❌ Funcionalidade crítica descrita no plano está completamente ausente
- ❌ Contrato de API/schema quebrado (tipos incompatíveis, campos obrigatórios faltando)
- ❌ Regressão crítica: código existente quebrado pela mudança
- ❌ Testes obrigatórios do plano inexistentes
- ❌ Violação de segurança introduzida (ex.: exposição de credenciais)

### P1 - ALTO (Corrigir antes de prosseguir)
Implementação pode avançar, mas **deve** ser corrigido antes de deploy. Exemplos:
- ⚠️ Implementação parcial: apenas 50-80% dos requisitos do plano implementados
- ⚠️ Lógica incorreta: comportamento não segue especificação do plano
- ⚠️ Testes insuficientes: casos críticos descritos no plano não testados
- ⚠️ Nomenclatura divergente: nomes de funções/classes diferentes do plano (quebra contratos)
- ⚠️ Documentação obrigatória ausente (ex.: README, AGENTS.md prometidos no plano)

### P2 - MÉDIO (Corrigir em follow-up próximo)
Não bloqueia, mas deve entrar no backlog. Exemplos:
- ℹ️ Desvios menores de design sem impacto funcional
- ℹ️ Logs estruturados faltando (não críticos para operação)
- ℹ️ Testes para edge cases não mencionados no plano
- ℹ️ Documentação inline (docstrings) incompleta
- ℹ️ Oportunidades de refatoração identificadas

### P3 - BAIXO (Nitpicks, opcional)
Melhorias cosméticas ou best practices. Exemplos:
- 💡 Formatação, estilo de código
- 💡 Variáveis mal nomeadas (mas funcionalmente corretas)
- 💡 Comentários desnecessários ou redundantes
- 💡 Pequenas otimizações de performance

## 7. Boas Práticas de Auditoria

### Durante a Revisão
- ✅ **Use ferramentas eficientemente:** Read para ler arquivos, Grep para buscar símbolos, Glob para listar arquivos
- ✅ **Compare linha a linha:** não suponha que algo foi implementado, valide explicitamente no código
- ✅ **Verifique variações:** se algo parecer ausente, busque por renomeações, arquivos movidos, refatorações
- ✅ **Execute testes:** rode `pytest` localmente para confirmar que testes passam conforme alegado
- ✅ **Use git diff:** compare código atual com commit base para detectar mudanças não planejadas
- ✅ **Documente evidências:** SEMPRE inclua `arquivo:linha` em findings (ex.: `app/agent.py:512`)

### Ao Classificar Findings
- ⚠️ **Evite suposições:** se algo não está claro no plano, marque como "necessita esclarecimento" ao invés de reprovar
- ⚠️ **Seja conservador:** na dúvida entre P1 e P2, escolha P1 (melhor ser rigoroso)
- ⚠️ **Registre incertezas separadamente:** crie seção "Dúvidas/Ambiguidades" no relatório
- ⚠️ **Diferencie ausência vs divergência:**
  - Ausência total = P0/P1
  - Implementado diferente do plano = P1/P2 (depende do impacto)

### Ao Reportar
- 📋 **Seja específico:** "Função `validate_schema()` ausente" vs "Validação não implementada"
- 📋 **Cite o plano:** referencie seção/parágrafo do plano que não foi atendido
- 📋 **Priorize ação:** sugira correção específica, não apenas aponte o problema

## 8. Formato do Relatório Final

Ao concluir a revisão, produza um relatório estruturado seguindo este template:

---

### 📋 RELATÓRIO DE AUDITORIA DE CÓDIGO

#### 1. RASTREABILIDADE
```
Plano auditado:    [caminho do arquivo .md]
Fase/Seção:        [identificador exato da seção no plano]
Commit analisado:  [hash do git commit]
Auditor:           [nome do agente/revisor]
Data/Hora:         [timestamp America/Sao_Paulo]
```

#### 2. RESUMO EXECUTIVO
```
Total de findings: [N]
  - P0 (Bloqueantes): [N]
  - P1 (Alto): [N]
  - P2 (Médio): [N]
  - P3 (Baixo): [N]

Decisão: [APROVADO | REQUER CORREÇÕES | BLOQUEADO]
Justificativa: [1-2 frases explicando a decisão]
```

#### 3. FINDINGS DETALHADOS

Para cada finding, use este formato:

```
[ID] [P0/P1/P2/P3] - [Título curto do problema]

Descrição:
  [Explicação detalhada do que está incorreto/ausente]

Referência no Plano:
  Seção: [nome da seção no plano]
  Requisito: [trecho específico do plano não atendido]

Evidência no Código:
  Arquivo: [caminho:linha]
  Situação atual: [o que foi encontrado ou está ausente]
  Esperado: [o que deveria estar conforme plano]

Ação Recomendada:
  [Correção específica a ser aplicada]

Impacto:
  [Como isso afeta funcionalidade, testes, segurança, etc.]
```

#### 4. ANÁLISE DE COBERTURA

```
Requisitos do Plano Implementados: [N/M] ([X]%)

Arquivos Mencionados no Plano:
  ✅ [arquivo1.py] - Implementado conforme plano
  ⚠️ [arquivo2.py] - Implementação parcial (detalhes em findings)
  ❌ [arquivo3.py] - Não implementado

Testes Especificados:
  ✅ [test_feature.py::test_happy_path] - Passa
  ❌ [test_feature.py::test_edge_case] - Ausente (P1)
```

#### 5. RISCOS E SIDE-EFFECTS

```
Regressões Detectadas:
  [Lista de código legado afetado, se houver]

Mudanças Fora do Escopo:
  [Arquivos modificados não mencionados no plano]
  Justificadas: [sim/não, com explicação]

Feature Flags:
  [Status de compatibilidade com flags ativadas/desativadas]
```

#### 6. DÚVIDAS E AMBIGUIDADES

```
[Lista de itens do plano não claros ou ambíguos que requerem esclarecimento]
```

#### 7. DECISÃO FINAL

```
☐ APROVADO - Implementação conforme plano, pode prosseguir
☐ REQUER CORREÇÕES - P1/P2 devem ser corrigidos antes de avançar
☐ BLOQUEADO - P0 detectados, requer retrabalho imediato
```

**Próximos Passos:**
[Lista de ações recomendadas]

---

## 9. Exemplos de Invocação

### Exemplo 1: Auditoria de Fase Específica
```
Audite a implementação da Fase 2 conforme:
- Plano: codex/plans/feature_xyz.md
- Seção: "Fase 2: Implementação do Backend"
- Commit: HEAD (ou hash específico)
```

### Exemplo 2: Auditoria Completa do Plano
```
Audite TODAS as fases implementadas conforme:
- Plano: codex/plans/refactor_validation.md
- Escopo: Todos os arquivos em app/ e tests/
- Gere relatório consolidado
```

### Exemplo 3: Auditoria Pós-Correção
```
Re-audite os findings P0/P1 do relatório anterior conforme:
- Plano: codex/plans/feature_xyz.md
- Relatório anterior: .claude/results/audit-2024-01-15.md
- Foco: Validar se correções foram aplicadas
```

---

## 10. Integração com Fluxo Multi-Agente

Este documento se integra ao fluxo de `.claude/CLAUDE.md` da seguinte forma:

1. **Após FASE 3 (Reviewer):** Se reviewer aprovou mas há dúvidas, use esta auditoria para validação adicional
2. **Antes de deploy:** Execute auditoria completa do plano antes de marcar como "pronto para produção"
3. **Pós-correção (Fixer):** Re-audite findings específicos após Fixer aplicar correções
4. **Escalação:** Use findings P0 documentados neste relatório como base para `/escalate`

**Nota:** Esta auditoria NÃO substitui o Reviewer Agent, mas o complementa com foco específico em conformidade plano↔código.

---

Seguir este anexo garante revisões consistentes, auditáveis e alinhadas às melhores práticas de code review para **qualquer plano** do projeto.
