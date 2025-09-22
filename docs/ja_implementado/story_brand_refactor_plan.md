# StoryBrand Fallback & Refactor Plan

## 1. Contexto Atual
- **Componente principal**: `StoryBrandExtractor` em `app/tools/langextract_sb7.py` utiliza LangExtract + Gemini para mapear elementos do framework StoryBrand.
- **Callback**: `process_and_extract_sb7` em `app/callbacks/landing_page_callbacks.py` processa o retorno do `web_fetch_tool` e persiste `storybrand_analysis`, `storybrand_summary` e `storybrand_ad_context` no estado.
- **Problema**: Quando LangExtract não identifica elementos suficientes, o extrator retorna `_empty_result()` e o pipeline prossegue sem contexto significativo. Isso gera anúncios pobres e sem direcionamento StoryBrand.

## 2. Objetivo
Implementar um fallback determinístico e rastreável que gere um contexto mínimo a partir do conteúdo bruto da landing page quando a análise StoryBrand ficar abaixo de um limiar definido.

## 3. Critérios de Ativação do Fallback
1. Após validar `StoryBrandAnalysis`, verificar `analysis.completeness_score`.
2. Limiar proposto: `< 0.2` (ajustável via constante ou env `STORYBRAND_FALLBACK_THRESHOLD`).
3. Alternativamente, disparar também quando `analysis.metadata.elements_found` estiver vazio.
4. Quando o fallback for acionado:
   - Marcar no estado `storybrand_fallback = True`.
   - Registrar `storybrand_reason = "no_storybrand_elements"`.
   - Logar evento estruturado (`logger.log_struct`).

## 4. Fluxo de Responsabilidade
1. `web_fetch_tool` → retorna HTML, texto e metadados.
2. `process_and_extract_sb7` → chama `StoryBrandExtractor.extract` com `text_content` (ou `html_content`).
3. Após obter `StoryBrandAnalysis`, verificar critérios do fallback.
4. Se fallback ativo:
   - Invocar função auxiliar para sintetizar contexto base.
   - Preencher `landing_page_context`, `storybrand_summary` e `storybrand_ad_context` com dados conservadores.
   - Garantir compatibilidade com o restante do pipeline (ex.: context_synthesizer).

## 5. Implementação Técnica Detalhada

### 5.1 Ajustes em `process_and_extract_sb7`
- Inserir constante local `FALLBACK_THRESHOLD = float(os.getenv("STORYBRAND_FALLBACK_THRESHOLD", 0.2))`.
- Após criação de `analysis`, adicionar bloco:
  ```python
  fallback_triggered = analysis.completeness_score < FALLBACK_THRESHOLD or not analysis.metadata.elements_found
  if fallback_triggered:
      tool_context.state['storybrand_fallback'] = True
      tool_context.state['storybrand_reason'] = 'no_storybrand_elements'
      logger.warning("[storybrand_fallback] score=%s elements=%s", analysis.completeness_score, analysis.metadata.get('elements_found'))
  ```
- Encaminhar processamento para função `apply_storybrand_fallback(...)` quando `fallback_triggered` for `True`.

### 5.2 Função Auxiliar `apply_storybrand_fallback`
Criar dentro do callback (ou módulo separado) uma função com responsabilidades:
- **Input**: `tool_context`, `result`, `analysis`, `text_content`, `html_content`, `metadata`.
- **Passos**:
  1. Extrair título: usar `metadata.get('title')` e `metadata.get('h1_headings', [])`.
  2. Identificar frases-chave: selecionar as primeiras linhas relevantes de `text_content` (p.ex., 2–3 sentenças).
  3. Extrair CTAs básicos: buscar termos como "clique", "saiba mais", "agende" no `text_content` ou em `metadata` (ex.: `open_graph`).
  4. Construir `fallback_context` com chaves mínimas esperadas pelo pipeline:
     ```python
     fallback_context = {
         "titulo_principal": title or "Título não disponível",
         "beneficios": key_sentences[:3],
         "ctas_principais": detected_ctas or ["Solicite mais informações"],
         "tom_voz": "Informativo",
         "palavras_chave": extract_keywords(key_sentences),
         "storybrand_completeness": analysis.completeness_score,
     }
     ```
  5. Atualizar `result['landing_page_context'] = fallback_context` (fundindo com contexto existente se necessário).
  6. Definir `fallback_summary = "Conteúdo insuficiente para StoryBrand. Usando resumo baseado no texto original."` e salvar em `tool_context.state['storybrand_summary']`.
  7. Criar `fallback_ad_context` com campos vazios ou derivados (`persona`, `beneficios`, `cta_principal`) garantindo compatibilidade com prompts.
  8. Persistir `storybrand_analysis` como `analysis.model_dump()` para manter schema, mas adicionar `analysis.metadata['fallback'] = True`.

### 5.3 Reaproveitamento de Dados
- Certificar que `landing_page_context` resultante contenha campos esperados por `context_synthesizer` (`persona_cliente`, `problemas_dores`, etc.) ainda que vazios.
- Fornecer defaults explícitos (strings vazias ou listas) para evitar `KeyError`.

### 5.4 Logs e Telemetria
- Adicionar log estruturado:
  ```python
  logger.log_struct({
      "event": "storybrand_fallback",
      "score": analysis.completeness_score,
      "elements_found": analysis.metadata.get('elements_found', []),
      "text_length": len(text_content or ''),
      "truncated": truncated,
  }, severity="WARNING")
  ```
- Manter `storybrand_timing` e quaisquer métricas já existentes.

## 6. Testes Propostos

### 6.1 Testes Unitários (pytest)
1. **Caso Fallback**:
   - Mockar `StoryBrandExtractor.extract` para retornar `_empty_result()`.
   - Verificar que `storybrand_fallback` é `True`, `landing_page_context` contém título/benefícios/ctas, e `storybrand_summary` menciona fallback.
2. **Caso Normal**:
   - Retornar análise com `completeness_score = 0.6` e elementos presentes.
   - Confirmar que fallback não é acionado e que o contexto mantém dados originais.
3. **Conteúdo Vazio**:
   - Simular `tool_response` sem texto/HTML e garantir que o callback retorna cedo, sem tentar fallback.

### 6.2 Testes de Integração
- Pipelines com `landing_page_analyzer` usando HTML minimalista para acionar fallback.
- Assegurar que o pipeline posterior (`context_synthesizer`, `feature_planner`) consome o fallback sem erros.

### 6.3 Testes Manuais
- Executar `make dev-backend-all` + frontend, enviar requisição com landing simplificada.
- Verificar logs (`[storybrand_fallback]`) e conteúdo da resposta final (JSON gerado).

## 7. Documentação e Comunicações
- Atualizar `README.md` ou doc específico com seção "Fallback StoryBrand":
  - Descrever o limiar, comportamento quando sem elementos, e flags no estado.
- Adicionar nota em changelog/próximo release destacando o fallback.
- Informar equipe sobre sinalizadores (`storybrand_fallback`, `storybrand_reason`) para debug.

## 8. Configurações e Observabilidade
- Considerar tornar o limiar configurável via env `STORYBRAND_FALLBACK_THRESHOLD` (documentado).
- Expor métrica/contador (futuro) para monitorar frequência de fallbacks.

## 9. Sequência de Execução Recomendada
1. Implementar detecção do fallback + flags/logs.
2. Criar função auxiliar `apply_storybrand_fallback` e garantir integridade dos dados retornados.
3. Atualizar persistência no estado (`storybrand_summary`, `storybrand_ad_context`, `landing_page_context`).
4. Adicionar testes unitários e ajustar mocks necessários.
5. Rodar testes de integração/manuais.
6. Documentar mudanças.

## 10. Riscos e Mitigações
- **Contexto gerado pouco útil**: garantir heurísticas simples (ex.: usar headings reais) e revisitar após feedback.
- **Falsos positivos (fallback indevido)**: escolher limiar conservador + log detalhado para ajuste.
- **Impacto em prompts**: revisar prompts (`context_synthesizer`, `code_generator`) para lidar com campos vazios ou placeholders.
- **Performance**: processamento adicional é leve (opera em string/metadata local).

---

**Próximo Passo**: aprovar este plano e só então iniciar implementação seguindo a sequência detalhada.
