# Plano de Correção do Anexo de Revisão de Planos

## 1. Contexto e Problema Identificado

### 1.1 Situação Atual
O arquivo `codex/anexo_revisao_planos.md` contém instruções para revisão manual de planos `.md` pelo Claude Code (Codex), mas **incorre nos mesmos erros** que o subagente `plan-code-validator` tinha antes das melhorias de 2025-01-04.

### 1.2 Problema Central
O anexo não tem mecanismo para detectar quando **o mesmo elemento aparece em múltiplos contextos** ao longo do plano:

**Exemplo de Falha:**
```markdown
Fase 1: Criar app/validators/final_delivery_validator.py
Fase 3: Usar final_delivery_validator no pipeline
```

**Comportamento Atual do Anexo:**
1. Extrai claim "Criar final_delivery_validator" → classifica como ENTREGA ✅
2. Extrai claim "Usar final_delivery_validator" → classifica como DEPENDÊNCIA ❌
3. Valida contra código → não encontra
4. Reporta como P0 blocker ❌ (FALSO POSITIVO)

**Comportamento Esperado:**
1. **First Pass**: Escaneia TODO o plano, descobre que `final_delivery_validator` será criado
2. Constrói "Creation Registry": `{"final_delivery_validator": True}`
3. Ao classificar claim "Usar final_delivery_validator", verifica registry PRIMEIRO
4. Como está no registry → classifica como ENTREGA (não valida contra código)
5. Resultado: ZERO falsos positivos

### 1.3 Root Causes
1. **Ausência de Two-Pass Analysis**: Não instrui fazer descoberta prévia do que será criado
2. **Falta de Regra de Precedência**: Não define que "criação vence uso" na classificação
3. **Sem Anti-Contradiction Check**: Não verifica se P0 reportado está marcado para criação
4. **Classificação Baseada Apenas em Contexto Local**: Analisa claim isoladamente, sem visão global do plano

---

## 2. Melhorias Implementadas no Subagente (Referência)

As seguintes melhorias foram implementadas em `.claude/agents/plan-code-validator.md` e devem ser espelhadas no anexo:

### 2.1 PHASE 1.5: Creation Registry Build (linhas 100-108)
- **First Pass obrigatório** antes de qualquer extração de claims
- Escaneia plano inteiro buscando padrões de criação:
  - Seções com verbos: "Fase N - Criar X", "Implementar Y"
  - Listas numeradas: "1. Criar...", "2. Implementar..."
  - Declarações: "será criado", "vamos adicionar"
- Extrai targets: file paths, class names, function names, config flags
- Constrói dict mapping: `{"app/validators/file.py": True, "RunIfPassed": True}`
- Loga tamanho para transparência: "Creation Registry: 23 elementos"

### 2.2 Lógica de Precedência na Classificação (linhas 112-116)
**Ordem obrigatória de verificação:**
1. **Checar Creation Registry PRIMEIRO**: Se elemento no registry → SEMPRE ENTREGA
2. Analisar verbos locais: "criar/implementar" → ENTREGA; "usar/chamar" → DEPENDÊNCIA
3. Checar qualificadores: "existente/atual" → DEPENDÊNCIA
4. **Regra de Ouro**: Registry vence contexto local

### 2.3 Anti-Contradiction Check (linha 133)
- Antes de finalizar relatório: verifica overlap entre Creation Registry e P0 findings
- Se encontrar: loga ERRO e reclassifica como ENTREGA

### 2.4 Phase 7: Final Classification Review (linhas 135-141)
- Re-revisa TODOS os P0s antes de gerar relatório
- Para cada P0: verifica se está no Creation Registry
- Se SIM: downgrade para INFO (não é blocker)
- Métricas separadas: "True P0 Blockers" vs "Planned Creations"

### 2.5 Exemplo Prático Multi-Fase (linhas 59-66)
```markdown
Fase 1: Criar app/validators/final_delivery_validator.py
Fase 3: Usar final_delivery_validator no pipeline
```
- Claim 1 (Fase 1): "final_delivery_validator" + "Criar" → ✅ ENTREGA
- Claim 2 (Fase 3): "final_delivery_validator" + "Usar" → Registry check → ✅ ENTREGA
- Resultado: 0 P0 blockers, elemento corretamente classificado como criação planejada

### 2.6 Regras Críticas Reforçadas (linhas 192-222)
- **MUST**: Construir Creation Registry ANTES de extrair claims
- **MUST**: Checar registry antes de marcar como DEPENDÊNCIA
- **MUST NOT**: Reportar como P0 qualquer coisa no registry (erro crítico)
- **CRITICAL ERROR DETECTION**: 3 perguntas obrigatórias antes de reportar P0:
  1. Está no Creation Registry?
  2. Plano diz explicitamente para criar?
  3. Escaneei o plano inteiro?

### 2.7 Relatório Enriquecido (linhas 143-148)
- JSON: inclui `creation_registry` em metadata
- Markdown: seção dedicada "✅ Planned Creations (Not Blockers)"

---

## 3. Especificação das Correções no Anexo

### 3.1 Adicionar Novo Passo 2.5 (após linha 11)

**Inserir após:** "1. Localizar e ler o plano..."

**Novo conteúdo:**
```markdown
2. **Construir Creation Registry (First Pass - OBRIGATÓRIO)**:
   - **Objetivo**: Descobrir TODOS os elementos que o plano diz criar ANTES de classificar qualquer alegação.
   - **Procedimento**:
     a) Escanear TODO o plano (todas as fases, seções, listas) buscando padrões de criação:
        - Títulos de seção: "Fase N - Criar X", "Implementar Y", "Construir Z"
        - Listas numeradas/bullet iniciando com: "Criar", "Implementar", "Adicionar", "Desenvolver", "Construir", "Estender"
        - Declarações explícitas: "será criado", "vamos implementar", "novo módulo X", "nova classe Y"
     b) Extrair targets de criação:
        - File paths: `app/validators/final_delivery_validator.py`
        - Class/function names: `RunIfPassed`, `FinalAssemblyGuardPre`
        - Config flags: `enable_deterministic_final_validation`
        - Modules: `app/schemas/final_delivery`
     c) Construir **Creation Registry** (mapa/dict):
        ```python
        creation_registry = {
            "app/validators/final_delivery_validator.py": True,
            "RunIfPassed": True,
            "FinalAssemblyGuardPre": True,
            "enable_deterministic_final_validation": True,
            # ... todos os elementos marcados para criação
        }
        ```
     d) Logar tamanho do registry para transparência:
        "Creation Registry construído: 23 elementos marcados para criação"
   - **Importância**: Este registro será usado como **primeira checagem** na classificação de todas as alegações subsequentes.
```

### 3.2 Modificar Passo 3 (linha 13) - Classificação

**Substituir:**
```markdown
3. **Classificar cada alegação** conforme o sistema do `plan-code-validator`:
   - `DEPENDÊNCIA`: deve existir hoje e será usada.
   - `MODIFICAÇÃO`: elemento existente que será alterado.
   - `ENTREGA`: item novo a ser criado (não validar no código; apenas registrar).
```

**Por:**
```markdown
3. **Classificar cada alegação COM REGRA DE PRECEDÊNCIA**:
   - **CRITICAL**: Aplicar verificações na ORDEM abaixo (Creation Registry tem prioridade sobre contexto local)

   **Ordem de Classificação (aplicar sequencialmente):**

   a) **VERIFICAÇÃO PRIMÁRIA - Creation Registry** (mais importante):
      - Checar se elemento/path está no Creation Registry
      - **Se SIM** → classificar como **ENTREGA** (independente do contexto local onde aparece)
      - **Se NÃO** → prosseguir para verificação de contexto local

   b) **VERIFICAÇÃO SECUNDÁRIA - Contexto Local** (quando NÃO está no registry):
      - Analisar verbos no contexto imediato da alegação:
        - Verbos de criação ("criar", "implementar", "adicionar", "desenvolver", "construir", "estender") → **ENTREGA**
        - Verbos de uso ("usar", "chamar", "importar", "ler de", "integrar com", "consumir") → **DEPENDÊNCIA**
        - Verbos de alteração ("refatorar", "modificar", "ajustar", "atualizar", "alterar") → **MODIFICAÇÃO**
      - Analisar qualificadores:
        - "existente", "atual", "disponível", "já implementado" → **DEPENDÊNCIA**
        - "novo", "nova", "adicional" → **ENTREGA**

   **REGRA DE OURO - Precedência:**
   - Creation Registry > Contexto Local > Qualificadores
   - Se elemento aparece em AMBOS contextos (criação E uso) → Registry vence → **ENTREGA**

   **Exemplo Prático (Plano Multi-Fase):**
   ```markdown
   Fase 1: Criar app/validators/final_delivery_validator.py
   Fase 3: Usar final_delivery_validator no pipeline
   ```
   - Passo 2.5: Creation Registry inclui `final_delivery_validator` ✅
   - Passo 3a: Claim "Criar final_delivery_validator" → no registry → **ENTREGA** ✅
   - Passo 3a: Claim "Usar final_delivery_validator" → no registry (check primário) → **ENTREGA** ✅
   - Resultado: 0 falsos positivos, 0 P0 blockers

   **Tipos de Classificação:**
   - `DEPENDÊNCIA`: elemento que deve existir hoje no código e será usado/consumido
   - `MODIFICAÇÃO`: elemento que existe hoje e será alterado/refatorado
   - `ENTREGA`: elemento que será criado durante a implementação (NÃO validar contra código)
```

### 3.3 Modificar Passo 4 (linha 17) - Validação

**Substituir:**
```markdown
4. **Validar no código** todas as alegações `DEPENDÊNCIA` e `MODIFICAÇÃO`:
```

**Por:**
```markdown
4. **Validar no código** todas as alegações `DEPENDÊNCIA` e `MODIFICAÇÃO`:
   - **IMPORTANTE**: Validar APENAS alegações classificadas como DEPENDÊNCIA ou MODIFICAÇÃO
   - **NUNCA validar** alegações classificadas como ENTREGA (são criações planejadas, esperado não existir ainda)
   - **Sanity Check obrigatório**: Antes de validar qualquer alegação, confirmar que NÃO está no Creation Registry
     - Se alegação está no registry mas foi classificada como DEPENDÊNCIA → **ERRO DE CLASSIFICAÇÃO** (reclassificar como ENTREGA)
```

### 3.4 Adicionar Novo Passo 5.5 (após linha 20, antes do Passo 6)

**Inserir antes de:** "6. Montar relatório estruturado"

**Novo conteúdo:**
```markdown
5.5 **Anti-Contradiction Check (verificação obrigatória antes do relatório)**:
   - Objetivo: Garantir que nenhum elemento apareça simultaneamente no Creation Registry E nos achados P0
   - Procedimento:
     a) Listar todos os achados classificados como P0 (blockers críticos)
     b) Para cada P0, verificar se o elemento/path está no Creation Registry
     c) **Se encontrar overlap**:
        - Logar ERRO: "Contradição detectada: elemento X está no Creation Registry mas foi reportado como P0"
        - Reclassificar de P0 → INFO (ou ENTREGA)
        - Atualizar métricas: remover de "True Blockers", adicionar a "Planned Creations"
     d) Resultado final: ZERO overlap entre Creation Registry e P0 findings
   - **Critical Error Detection** - Antes de reportar QUALQUER P0, verificar:
     1. ❓ Este elemento está no Creation Registry?
     2. ❓ O plano diz explicitamente para criar/implementar este elemento?
     3. ❓ Escaneei TODO o plano na etapa 2.5 (First Pass)?
     - Se resposta a QUALQUER pergunta for SIM → NÃO é P0 blocker, é criação planejada
```

### 3.5 Modificar Passo 6 (linha 22) - Estrutura do Relatório

**Substituir:**
```markdown
6. **Montar relatório estruturado** com:
   - Resumo executivo (quantidade de achados por severidade e impacto).
   - Lista de inconsistências, cada uma com: severidade, alegação original, evidência no código, ação recomendada.
   - Tabela mapa Plano ↔ Código (quando aplicável).
   - Itens de incerteza ou verificações pendentes.
```

**Por:**
```markdown
6. **Montar relatório estruturado** com:
   - **Metadata**:
     - Data/hora da validação (America/Sao_Paulo)
     - Creation Registry: lista de elementos marcados para criação (com referência à linha do plano)
   - **Resumo Executivo**:
     - Quantidade de achados por severidade (P0/P1/P2/P3)
     - **Métricas separadas**:
       - True P0 Blockers: elementos que deveriam existir mas não existem E não têm tarefa de criação
       - Planned Creations (INFO): elementos que não existem mas têm tarefa de criação (não são blockers)
     - Blast radius estimado (módulos/arquivos impactados)
   - **Seção 1: True Blockers (P0)** - apenas bloqueadores legítimos:
     - Cada achado com: severidade, alegação original, evidência no código (file:line), ação recomendada, acceptance criteria
   - **Seção 2: High Priority (P1/P2)** - ajustes necessários:
     - Divergências de assinatura, naming, etc.
   - **Seção 3: ✅ Planned Creations (INFO)** - não são problemas:
     - Lista de elementos no Creation Registry com:
       - Nome do elemento
       - Onde será criado (Fase/seção do plano)
       - Tipo (file, class, function, config)
       - Linha de referência no plano
   - **Seção 4: Tabela Mapa Plano ↔ Código** (quando aplicável):
     - Relacionamento entre alegações do plano e implementação real
   - **Seção 5: Incertezas e Verificações Pendentes**:
     - Elementos dinâmicos/metaprogramados
     - Verificações manuais necessárias
```

### 3.6 Adicionar Seção de Exemplos Práticos (após linha 28, antes de "Boas Práticas")

**Inserir:**
```markdown
## Exemplo Completo de Aplicação

### Cenário: Plano com Criação e Uso do Mesmo Elemento

**Plano original:**
```markdown
# Fase 1 - Estruturas de Base
1. Criar app/validators/final_delivery_validator.py com classe FinalDeliveryValidatorAgent

# Fase 2 - Validador
3. Implementar app/validators/final_delivery_validator.py importando schemas

# Fase 3 - Reorquestração
- Usar final_delivery_validator no pipeline
- Integrar com FinalDeliveryValidatorAgent
```

**Aplicação do Procedimento Corrigido:**

**Passo 2.5 (First Pass - Creation Registry):**
```python
creation_registry = {
    "app/validators/final_delivery_validator.py": {
        "type": "file",
        "phase": "Fase 1",
        "line": 2
    },
    "FinalDeliveryValidatorAgent": {
        "type": "class",
        "phase": "Fase 1",
        "line": 2
    }
}
# Log: "Creation Registry construído: 2 elementos marcados para criação"
```

**Passo 3 (Classificação com Precedência):**

| Alegação | Contexto Local | Registry Check | Classificação Final | Validar? |
|----------|---------------|----------------|---------------------|----------|
| "Criar app/validators/..." | Verbo "Criar" | ✅ No registry | **ENTREGA** | ❌ NÃO |
| "Implementar app/validators/..." | Verbo "Implementar" | ✅ No registry | **ENTREGA** | ❌ NÃO |
| "Usar final_delivery_validator" | Verbo "Usar" | ✅ No registry | **ENTREGA** (registry vence) | ❌ NÃO |
| "Integrar com FinalDeliveryValidatorAgent" | Verbo "Integrar" | ✅ No registry | **ENTREGA** (registry vence) | ❌ NÃO |

**Passo 5.5 (Anti-Contradiction Check):**
- P0 findings: [] (vazio)
- Creation Registry: 2 elementos
- Overlap: ZERO ✅
- Status: APROVADO

**Resultado Final:**
- True P0 Blockers: 0 ✅
- Planned Creations: 2 (informativo, não são problemas)
- Falsos positivos evitados: 4
```

### 3.7 Atualizar Seção "Boas Práticas" (linha 29)

**Adicionar ao final da lista existente:**
```markdown
- **SEMPRE construir Creation Registry ANTES de classificar** (Passo 2.5 é obrigatório, não opcional).
- **Checar registry PRIMEIRO** ao classificar qualquer alegação (precedência sobre contexto local).
- **NUNCA reportar como P0** algo que está no Creation Registry (erro crítico).
- **Executar Anti-Contradiction Check** antes de finalizar o relatório (Passo 5.5).
- Se elemento aparece em múltiplos contextos (criar E usar), prevalece a criação (classificar como ENTREGA).
- Logar o tamanho do Creation Registry para auditoria ("Registry: X elementos").
- Incluir Creation Registry completo no relatório final (seção dedicada).
```

---

## 4. Validação da Correção

### 4.1 Checklist de Implementação

Após aplicar as correções ao `anexo_revisao_planos.md`, verificar:

- [ ] Passo 2.5 "Creation Registry Build" adicionado com instruções detalhadas
- [ ] Passo 3 modificado com regra de precedência (Registry > Contexto > Qualificadores)
- [ ] Passo 4 atualizado com sanity check obrigatório
- [ ] Passo 5.5 "Anti-Contradiction Check" adicionado
- [ ] Passo 6 enriquecido com métricas separadas e seção "Planned Creations"
- [ ] Exemplo prático multi-fase adicionado
- [ ] Boas práticas atualizadas com regras do registry
- [ ] Todas as referências ao subagente `plan-code-validator` mantidas

### 4.2 Teste de Sanidade

Para validar se as correções funcionam, simular revisão do `plano_validacao_json.md`:

**Expectativa:**
- Creation Registry deve conter: `app/validators/final_delivery_validator.py`, `RunIfPassed`, `FinalAssemblyGuardPre`, `app/schemas/final_delivery.py`, etc.
- True P0 Blockers: ~0-2 (apenas bloqueadores legítimos)
- Planned Creations: ~8 (elementos que plano diz criar)
- ZERO overlap entre registry e P0s

**Se resultado divergir:** revisar aplicação das correções, especialmente:
1. Passo 2.5 está sendo executado ANTES da classificação?
2. Passo 3 está verificando registry PRIMEIRO?
3. Passo 5.5 está detectando contradições?

### 4.3 Exemplo de Aplicação Correta

Ao revisar um plano usando o anexo corrigido, o Claude Code deve:

1. **Início**: "Executando First Pass para construir Creation Registry..."
2. **Registry Log**: "Creation Registry construído: 23 elementos marcados para criação"
3. **Classificação**: "Verificando claim 'usar RunIfPassed' → encontrado no registry → classificar como ENTREGA"
4. **Anti-Contradiction**: "Revisando P0s contra Creation Registry... ZERO overlap detectado ✅"
5. **Relatório Final**:
   ```
   True P0 Blockers: 0
   Planned Creations: 23
   - app/validators/final_delivery_validator.py (Fase 2, linha 60)
   - RunIfPassed (Fase 2, linha 72)
   ...
   ```

---

## 5. Diferenças entre Anexo e Subagente

### 5.1 Elementos Comuns (alinhados)
- Sistema de classificação DEPENDÊNCIA/ENTREGA/MODIFICAÇÃO
- Regra de precedência (Creation Registry > Contexto Local)
- Anti-Contradiction Check
- Two-Pass Analysis (First Pass + Second Pass)

### 5.2 Diferenças Necessárias

| Aspecto | Subagente (plan-code-validator) | Anexo (anexo_revisao_planos) |
|---------|--------------------------------|------------------------------|
| **Formato Output** | JSON + Markdown (estruturado) | Descrição textual flexível |
| **Automação** | Totalmente automatizado via Task tool | Processo manual seguido pelo Claude Code |
| **Detalhamento** | AST parsing, fuzzy matching, heuristics | Leitura direta de código, verificação manual |
| **Métricas** | Schema v2.0.0, métricas quantitativas | Relatório qualitativo |
| **Fase** | 8 fases técnicas detalhadas | Passos simplificados para execução manual |

### 5.3 Garantir Alinhamento Conceitual

Embora formatos difiram, a **lógica de validação** deve ser idêntica:
- ✅ Ambos constroem Creation Registry ANTES de classificar
- ✅ Ambos aplicam precedência (registry > contexto)
- ✅ Ambos executam anti-contradiction check
- ✅ Ambos separam "True Blockers" de "Planned Creations"

---

## 6. Próximos Passos (Implementação)

### Ordem de Execução Recomendada:

1. **Aplicar correções ao anexo** seguindo especificações das seções 3.1 a 3.7
2. **Revisar anexo corrigido** para garantir coerência e clareza
3. **Atualizar AGENTS.md** se necessário (referências ao procedimento)
4. **Testar aplicação** simulando revisão de `plano_validacao_json.md`
5. **Comparar resultado** com validação do subagente para garantir alinhamento
6. **Documentar diferenças** entre anexo corrigido e subagente (se houver)

---

## 7. Conclusão

Este plano especifica todas as correções necessárias para eliminar falsos positivos no procedimento de revisão manual de planos, alinhando o `anexo_revisao_planos.md` com as melhorias já implementadas no subagente `plan-code-validator`.

**Impacto Esperado:**
- ✅ Eliminação de falsos positivos (P0s para entregas planejadas)
- ✅ Relatórios mais precisos e acionáveis
- ✅ Alinhamento entre revisão manual (Codex) e automatizada (subagente)
- ✅ Processo de validação mais robusto e confiável

**Critério de Sucesso:**
Ao revisar `plano_validacao_json.md` usando o anexo corrigido, deve produzir resultado equivalente ao subagente melhorado: ~0 true blockers, ~8 planned creations, ZERO contradições.
