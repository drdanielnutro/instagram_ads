# Plano de Refatoração: Remoção do `html_content` do Pipeline

**Data:** 2025-09-30
**Autor:** Equipe de Desenvolvimento
**Objetivo:** Eliminar o campo `html_content` do retorno do `web_fetch_tool` para reduzir payload e resolver problemas de quota Vertex AI.

---

## 📋 Sumário Executivo

### Problema Identificado
O sistema atual retorna tanto `html_content` (~1.7 MB) quanto `text_content` (~125 chars) do `web_fetch_tool`. O HTML completo:
- Infla spans de telemetria para 2+ MB
- Aumenta contexto nas chamadas Vertex AI
- Nunca é utilizado pelos agentes (sempre usam `text_content`)
- Causa erros 429 RESOURCE_EXHAUSTED em páginas grandes

### Solução Proposta
Remover completamente o campo `html_content` do retorno, mantendo apenas `text_content` (extraído pela Trafilatura). O HTML permanece como variável local para extração de metadados, mas não é propagado.

### Impacto Esperado
- **Redução de payload:** 85-90% (de ~2 MB para ~200-300 KB)
- **Redução de erros 429:** Menor pressão nas cotas Vertex AI
- **Zero regressão funcional:** Fallback automático garante continuidade
- **Simplicidade:** 2 arquivos modificados, ~10 linhas alteradas

---

## 🔍 Análise do Fluxo Atual

### 1. Extração de Conteúdo (`web_fetch_tool`)

**Arquivo:** `app/tools/web_fetch.py`
**Função:** `web_fetch_tool(url: str, tool_context: Optional[Any] = None) -> Dict[str, Any]`

**Fluxo atual:**
1. Faz requisição HTTP → obtém `html_content` (linha 92)
2. Trafilatura extrai texto limpo → `text_content` (linhas 95-102)
3. Se Trafilatura falha → BeautifulSoup como fallback (linhas 113-120)
4. Extrai metadados (title, meta_description, og_tags, h1) usando BeautifulSoup (linhas 123-159)
5. **Retorna ambos:** `html_content` E `text_content` (linha 169)

**Problema:**
```python
return {
    "status": "success",
    "html_content": html_content,  # ❌ 1.7 MB não utilizado
    "text_content": text_content,  # ✅ 125 chars usado
    # ...
}
```

### 2. Processamento StoryBrand (`process_and_extract_sb7`)

**Arquivo:** `app/callbacks/landing_page_callbacks.py`
**Função:** `process_and_extract_sb7(..., tool_response: Dict[str, Any], ...)`

**Fluxo atual:**
1. Recebe `tool_response` do `web_fetch_tool` (linha 94)
2. Extrai `text_content` e `html_content` (linhas 100-101)
3. **Fallback lógico:** `input_text = text_content or html_content` (linha 112)
4. Passa `input_text` para `StoryBrandExtractor.extract()` (linha 144)
5. Salva análise no estado (linhas 172-178)
6. **Retorna** `tool_response` completo (linha 225)

**Problema:**
- Linha 112: Fallback para HTML **nunca é usado** (Trafilatura sempre retorna algo)
- Linha 225: Retorna dict completo com `html_content` → propagado no histórico de mensagens do ADK

### 3. Extração StoryBrand (`StoryBrandExtractor`)

**Arquivo:** `app/tools/langextract_sb7.py`
**Método:** `extract(self, html_content: str, *, landing_page_url: Optional[str] = None)`

**Problema de nomenclatura:**
- Parâmetro chama-se `html_content` (linha 497)
- Docstring diz "HTML ou texto" (linha 502)
- **Na prática:** Sempre recebe `text_content` limpo da Trafilatura
- Nome é **enganoso** mas funcional

---

## 🎯 Mudanças Propostas

### Arquivo 1: `app/tools/web_fetch.py`

#### Mudança 1.1: Remover `html_content` do retorno de sucesso

**Localização:** Linha 167-175
**Antes:**
```python
return {
    "status": "success",
    "html_content": html_content,
    "text_content": text_content,
    "title": title,
    "meta_description": meta_description,
    "metadata": metadata,
    "error_message": None
}
```

**Depois:**
```python
return {
    "status": "success",
    "text_content": text_content,
    "title": title,
    "meta_description": meta_description,
    "metadata": metadata,
    "error_message": None
}
```

**Justificativa:**
- `html_content` nunca é usado pelos agentes
- `metadata` já contém informações extraídas do HTML (title, og_tags, h1)
- Variável `html_content` permanece local para extração de metadados (linhas 123-159)

---

#### Mudança 1.2: Remover `html_content` dos retornos de erro

**Localizações:** Linhas 46-52, 54-60, 180-186, 188-197, 199-208

**Antes (exemplo - linha 180):**
```python
return {
    "status": "error",
    "error_message": error_msg,
    "html_content": "",
    "text_content": "",
    "metadata": {}
}
```

**Depois:**
```python
return {
    "status": "error",
    "error_message": error_msg,
    "text_content": "",
    "metadata": {}
}
```

**Justificativa:**
- Consistência do schema de retorno
- Em caso de erro, `html_content` seria vazio de qualquer forma

---

### Arquivo 2: `app/callbacks/landing_page_callbacks.py`

#### Mudança 2.1: Remover lógica de fallback para `html_content`

**Localização:** Linhas 99-104
**Antes:**
```python
# Preferir texto limpo do Trafilatura quando disponível (melhor latência/precisão)
text_content = result.get('text_content')
html_content = result.get('html_content', '')
if not (text_content or html_content):
    logger.warning("Conteúdo vazio, pulando análise StoryBrand")
    return result
```

**Depois:**
```python
# Usar texto limpo extraído pela Trafilatura
text_content = result.get('text_content', '')
if not text_content:
    logger.warning("Conteúdo de texto vazio, pulando análise StoryBrand")
    return result
```

**Justificativa:**
- Trafilatura sempre retorna texto (mesmo que mínimo)
- Fallback para HTML nunca foi acionado na prática
- Simplifica lógica condicional

---

#### Mudança 2.2: Remover fallback na atribuição de `input_text`

**Localização:** Linha 112
**Antes:**
```python
# Se houver texto limpo, usar; senão, cair para HTML bruto
input_text = text_content or html_content
```

**Depois:**
```python
# Usar texto limpo extraído pela Trafilatura
input_text = text_content
```

**Justificativa:**
- `html_content` não existe mais no `result`
- Trafilatura garante que `text_content` sempre tem valor (ou early return na linha 102)

---

#### Mudança 2.3: Simplificar logging de tamanhos

**Localização:** Linhas 114-121
**Antes:**
```python
try:
    logger.info(
        "StoryBrand input sizes: text_len=%s, html_len=%s",
        len(text_content) if isinstance(text_content, str) else 0,
        len(html_content) if isinstance(html_content, str) else 0,
    )
except Exception:
    pass
```

**Depois:**
```python
try:
    logger.info(
        "StoryBrand input sizes: text_len=%s",
        len(text_content) if isinstance(text_content, str) else 0,
    )
except Exception:
    pass
```

**Justificativa:**
- Remove referência a variável inexistente
- Mantém métrica importante (tamanho do texto)

---

## 🔒 Garantias de Segurança

### 1. Metadados Preservados

**HTML ainda é usado localmente:**
```python
# web_fetch.py linhas 123-159
soup = BeautifulSoup(html_content, 'html.parser')  # ✅ Variável local
title = soup.find('title').get_text(strip=True)
meta_desc = soup.find('meta', attrs={'name': 'description'})
og_tags = soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')})
h1_tags = soup.find_all('h1')
```

**Resultado:** Todos os metadados continuam disponíveis em `metadata`.

---

### 2. Fallback Automático para Páginas Pobres

**Cenário:** Página com texto insuficiente (ex: lojachicamorena.com - 125 chars)

**Fluxo:**
1. `web_fetch_tool` retorna `text_content: "ou 4x sem juros..."` (125 chars)
2. `StoryBrandExtractor` processa → retorna score 0.14 (muito baixo)
3. `storybrand_gate.py` detecta `score < 0.6` (min_storybrand_completeness)
4. Gate aciona `fallback_storybrand_pipeline` automaticamente
5. Fallback reconstrói StoryBrand usando `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`
6. Pipeline continua normalmente com score 1.0

**Referências:**
- Gate decision: `app/agents/storybrand_gate.py:47-126`
- Fallback pipeline: `app/agents/storybrand_fallback.py:200-731`

---

### 3. Tratamento de Casos Extremos

| Cenário | `text_content` | Comportamento | Resultado |
|---------|----------------|---------------|-----------|
| **Página rica** | 10k+ chars | StoryBrand score ≥ 0.6 | ✅ Happy path |
| **Página pobre** | <500 chars | StoryBrand score < 0.6 | ✅ Fallback acionado |
| **Trafilatura falha** | BeautifulSoup extrai | StoryBrand tenta processar | ✅ Funciona ou fallback |
| **Página vazia** | `""` (string vazia) | Early return (linha 102) | ✅ StoryBrand não criado → fallback |
| **Erro de rede** | `status: "error"` | Callback não executa | ✅ Erro propagado graciosamente |
| **Timeout** | `status: "error"` | Callback não executa | ✅ Erro propagado graciosamente |

---

## 📊 Análise de Impacto

### Redução de Tamanho (caso real: lojachicamorena.com)

**Antes:**
```json
{
  "html_content": "<!DOCTYPE html>...[1,690,831 chars]...",
  "text_content": "ou 4x sem juros no cartão de crédito\nWhatsApp...",
  "metadata": {...}
}
```
- **Tamanho total:** ~1.7 MB
- **Span telemetria:** 2088 KB

**Depois:**
```json
{
  "text_content": "ou 4x sem juros no cartão de crédito\nWhatsApp...",
  "metadata": {...}
}
```
- **Tamanho total:** ~200 bytes
- **Span telemetria estimado:** 200-300 KB
- **Redução:** ~99% no retorno, ~85-90% no span total

---

### Impacto em Vertex AI

**Problema atual:**
- Histórico de mensagens do ADK inclui `tool_response` completo
- Cada agente subsequente recebe contexto inflado
- Limite de tokens/minuto atingido mais rapidamente
- Erro 429 RESOURCE_EXHAUSTED

**Após refatoração:**
- Histórico ~10x menor
- Menos tokens por chamada Vertex
- Margem maior antes de atingir limites
- Redução esperada de erros 429: 70-90%

---

### Compatibilidade com Código Existente

**Agentes que referenciam `html_content`:**
```bash
grep -r "html_content" app/
```

**Resultados:**
- ✅ `app/tools/web_fetch.py` - Variável local (continua existindo)
- ✅ `app/callbacks/landing_page_callbacks.py` - Será removido
- ✅ `app/tools/langextract_sb7.py` - Parâmetro `html_content` (nome enganoso, aceita texto)
- ❌ Nenhum outro arquivo referencia

**Conclusão:** Zero impacto em outros módulos.

---

## 🧪 Plano de Testes

### Testes Unitários

#### Teste 1: `web_fetch_tool` não retorna `html_content`
```python
def test_web_fetch_no_html_content():
    result = web_fetch_tool("https://example.com")
    assert "html_content" not in result
    assert "text_content" in result
    assert result["text_content"]  # Não vazio
```

#### Teste 2: `process_and_extract_sb7` funciona apenas com `text_content`
```python
def test_process_extract_text_only():
    tool_response = {
        "status": "success",
        "text_content": "Sample text content",
        "metadata": {}
    }
    # Não deve lançar KeyError para html_content
    result = process_and_extract_sb7(
        tool=mock_tool,
        tool_response=tool_response,
        tool_context=mock_context
    )
    assert result is not None
```

#### Teste 3: Early return quando `text_content` vazio
```python
def test_early_return_empty_text():
    tool_response = {
        "status": "success",
        "text_content": "",
        "metadata": {}
    }
    result = process_and_extract_sb7(
        tool=mock_tool,
        tool_response=tool_response,
        tool_context=mock_context
    )
    assert result == tool_response  # Retorna sem processar
```

---

### Testes de Integração

#### Teste 4: Pipeline completo com página rica
```bash
# URL: https://www.exemplo-rico.com.br
# Expectativa: StoryBrand score ≥ 0.6, happy path
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "landing_page_url": "https://www.exemplo-rico.com.br",
    "objetivo_final": "vendas",
    "perfil_cliente": "Empresários",
    "formato_anuncio": "Feed"
  }'

# Verificar:
# - storybrand_completeness ≥ 0.6
# - Nenhum erro 429
# - Span size < 500 KB
```

#### Teste 5: Pipeline completo com página pobre (fallback)
```bash
# URL: https://www.lojachicamorena.com
# Expectativa: StoryBrand score < 0.6, fallback acionado
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "landing_page_url": "https://www.lojachicamorena.com",
    "objetivo_final": "vendas",
    "perfil_cliente": "Mulheres",
    "formato_anuncio": "Feed",
    "nome_empresa": "Loja Chica Morena",
    "o_que_a_empresa_faz": "Vende roupas femininas",
    "sexo_cliente_alvo": "feminino"
  }'

# Verificar:
# - storybrand_gate_metrics.decision_path == "fallback"
# - storybrand_completeness == 1.0 (após fallback)
# - Nenhum erro 429
# - Span size < 500 KB
```

#### Teste 6: URL inválida/timeout
```bash
# URL: https://invalid-url-that-does-not-exist.com
# Expectativa: Erro gracioso, não trava pipeline
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "landing_page_url": "https://invalid-url.com",
    "objetivo_final": "vendas",
    "perfil_cliente": "Geral",
    "formato_anuncio": "Feed"
  }'

# Verificar:
# - Retorna erro com status != success
# - Não lança exceção não tratada
```

---

### Testes de Regressão

#### Teste 7: Metadados continuam sendo extraídos
```python
def test_metadata_extraction():
    result = web_fetch_tool("https://example.com")
    assert "metadata" in result
    assert "title" in result["metadata"]
    assert "meta_description" in result["metadata"]
    assert "open_graph" in result["metadata"]
    assert "h1_headings" in result["metadata"]
```

#### Teste 8: Trafilatura fallback para BeautifulSoup
```python
def test_trafilatura_fallback():
    # Mock Trafilatura para retornar None
    with mock.patch('trafilatura.extract', return_value=None):
        result = web_fetch_tool("https://example.com")
        # BeautifulSoup deve ter extraído texto
        assert result["text_content"]  # Não vazio
```

---

## 📝 Checklist de Implementação

### Pré-implementação
- [x] Análise de impacto concluída
- [x] Plano de testes definido
- [x] Backup do código atual (git commit)

### Implementação
- [ ] **Mudança 1.1:** Remover `html_content` do retorno de sucesso (`web_fetch.py:169`)
- [ ] **Mudança 1.2:** Remover `html_content` dos retornos de erro (`web_fetch.py:49,57,183,194,205`)
- [ ] **Mudança 2.1:** Atualizar lógica de validação (`landing_page_callbacks.py:100-104`)
- [ ] **Mudança 2.2:** Remover fallback HTML (`landing_page_callbacks.py:112`)
- [ ] **Mudança 2.3:** Simplificar logging (`landing_page_callbacks.py:115-119`)

### Validação
- [ ] Executar testes unitários (pytest)
- [ ] Executar teste de integração com página rica
- [ ] Executar teste de integração com página pobre (fallback)
- [ ] Verificar logs: span size reduzido
- [ ] Verificar logs: nenhum erro 429
- [ ] Validar metadados extraídos corretamente

### Pós-implementação
- [ ] Commit com mensagem descritiva
- [ ] Atualizar documentação (README.md, CLAUDE.md)
- [ ] Monitorar produção por 48h
- [ ] Coletar métricas: taxa de erros 429, duração média de pipeline

---

## 🚀 Rollout Planejado

### Fase 1: Desenvolvimento (Local)
1. Implementar mudanças em branch `refactor/remove-html-content`
2. Executar testes unitários e de integração
3. Validar com URLs conhecidas (rica + pobre)
4. Code review

### Fase 2: Staging (Opcional)
1. Deploy em ambiente de staging
2. Executar suite completa de testes
3. Monitorar telemetria (spans, erros Vertex)
4. Validar por 24h

### Fase 3: Produção
1. Merge para `main`
2. Deploy via `make backend`
3. Monitoramento ativo por 48h
4. Coleta de métricas de sucesso

---

## 📈 Métricas de Sucesso

### KPIs Primários
- **Redução de span size:** ≥ 80%
- **Redução de erros 429:** ≥ 50%
- **Taxa de sucesso de pipeline:** ≥ 95%

### KPIs Secundários
- **Latência média de pipeline:** Sem aumento significativo (≤ 5%)
- **Taxa de acionamento de fallback:** Monitorar baseline
- **Completeness score médio:** Sem degradação

### Coleta de Métricas
```python
# Adicionar logs estruturados
logger.info(
    "pipeline_metrics",
    extra={
        "span_size_kb": span_size / 1024,
        "storybrand_score": completeness_score,
        "fallback_triggered": decision_path == "fallback",
        "vertex_errors": error_count,
        "duration_seconds": duration
    }
)
```

---

## 🔄 Plano de Rollback

### Condições para Rollback
- Taxa de erros > 10%
- Degradação de completeness score > 20%
- Erros críticos não previstos

### Procedimento de Rollback
1. **Reverter commit:**
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

2. **Redeploy:**
   ```bash
   make backend
   ```

3. **Validar:**
   - Pipeline volta a funcionar
   - Erros 429 retornam (esperado)

4. **Post-mortem:**
   - Analisar logs de falha
   - Ajustar plano de refatoração
   - Reagendar implementação

---

## 📚 Referências Técnicas

### Arquivos Modificados
1. `app/tools/web_fetch.py` - Função `web_fetch_tool()`
2. `app/callbacks/landing_page_callbacks.py` - Função `process_and_extract_sb7()`

### Arquivos Relacionados (não modificados)
1. `app/tools/langextract_sb7.py` - `StoryBrandExtractor.extract()` (parâmetro mantido)
2. `app/agents/storybrand_gate.py` - Lógica de decisão de fallback
3. `app/agents/storybrand_fallback.py` - Pipeline de fallback
4. `app/agent.py` - Definição de agentes e pipeline

### Bibliotecas Envolvidas
- **Trafilatura 1.x:** Extração de texto de HTML
- **BeautifulSoup4:** Fallback de extração + metadados
- **Requests:** Download de páginas web

### Documentação Externa
- [Trafilatura Documentation](https://trafilatura.readthedocs.io/)
- [Vertex AI Error 429](https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429)
- [Google ADK Callbacks](https://github.com/google/adk)

---

## 👥 Aprovações Necessárias

- [ ] **Tech Lead:** Revisão técnica do plano
- [ ] **QA:** Validação do plano de testes
- [ ] **DevOps:** Aprovação de deploy
- [ ] **Product Owner:** Aceite de impacto funcional (zero regressão esperada)

---

## 📞 Contatos e Suporte

**Em caso de dúvidas ou problemas:**
- Tech Lead: [email]
- Canal Slack: #instagram-ads-dev
- Documentação: `CLAUDE.md`, `README.md`

---

**Última atualização:** 2025-09-30
**Versão do documento:** 1.0
**Status:** Aguardando revisão e aprovação
