# Plano de Refatoração: Especificações Dinâmicas por Formato

## Objetivo
Implementar injeção de especificações específicas por formato (Reels, Stories, Feed) mantendo o schema de saída fixo, conforme validado pelo Codex.

## Premissas (Validadas pelo Codex)
1. ✅ State é compartilhado entre todos os agentes
2. ✅ Placeholders `{variavel}` são substituídos automaticamente pelo ADK
3. ✅ Callbacks podem adicionar novos campos ao state
4. ✅ Sistema gera apenas imagens (tratar Reels como "still com estética de vídeo")

## Fase 1: Criar Arquivo de Especificações

### Arquivo: `app/format_specifications.py`

```python
"""
Especificações por formato de anúncio Instagram.
Mantido ENXUTO para otimizar consumo de tokens.
"""

FORMAT_SPECS = {
    "Reels": {
        "copy": {
            "headline_max_chars": 40,
            "corpo_max_chars": 125,
            "estilo": "gancho forte nos 3 primeiros segundos, bullets rápidos",
            "estrutura": "problema-solução-cta em 15 segundos",
            "tom": "dinâmico, urgente, verbos de ação"
        },
        "visual": {
            "aspect_ratio": "9:16",
            "composicao": "full-bleed vertical, texto mínimo sobreposto",
            "estetica": "movimento sugerido mesmo em still",
            "elementos": "setas, transições visuais, contrastes fortes"
        },
        "strategy": {
            "etapa_funil": "topo-meio",
            "objetivo_principal": "awareness e descoberta",
            "cta_preferencial": "Saiba mais",
            "metricas_foco": "alcance, engajamento"
        }
    },

    "Stories": {
        "copy": {
            "headline_max_chars": 30,
            "corpo_max_chars": 80,
            "estilo": "urgência e escassez, direto ao ponto",
            "estrutura": "oferta-benefício-ação imediata",
            "tom": "pessoal, exclusivo, FOMO"
        },
        "visual": {
            "aspect_ratio": "9:16",
            "composicao": "elementos interativos sugeridos (polls, quiz)",
            "estetica": "casual, autêntico, menos produzido",
            "elementos": "stickers visuais, countdown timer, setas para cima"
        },
        "strategy": {
            "etapa_funil": "meio-fundo",
            "objetivo_principal": "conversão rápida",
            "cta_preferencial": "Enviar mensagem",
            "metricas_foco": "swipe-ups, mensagens"
        }
    },

    "Feed": {
        "copy": {
            "headline_max_chars": 125,
            "corpo_max_chars": 2200,
            "estilo": "storytelling completo, desenvolvimento permitido",
            "estrutura": "contexto-desenvolvimento-prova-cta",
            "tom": "informativo, confiável, profissional"
        },
        "visual": {
            "aspect_ratio": "1:1",  # ou "4:5" baseado em pesquisa
            "composicao": "grid harmônico, branded, alta qualidade",
            "estetica": "polido, consistente com identidade visual",
            "elementos": "logo visível, cores da marca, hierarquia clara"
        },
        "strategy": {
            "etapa_funil": "todos",
            "objetivo_principal": "versatil por objetivo",
            "cta_preferencial": "Saiba mais",
            "metricas_foco": "conversões, salvamentos"
        }
    }
}

# Fallback para formato não reconhecido
FORMAT_SPECS["default"] = FORMAT_SPECS["Feed"]
```

## Fase 2: Modificar Callback Existente

### Arquivo: `app/agent.py`
### Função: `unpack_extracted_input_callback` (linha 126)

**Adicionar ao final da função (antes do except):**

```python
# NOVO: Injetar especificações do formato escolhido
try:
    from app.format_specifications import FORMAT_SPECS

    # Obter formato escolhido (default: Feed)
    formato = callback_context.state.get("formato_anuncio", "Feed")

    # Buscar especificações (com fallback)
    specs = FORMAT_SPECS.get(formato, FORMAT_SPECS.get("default"))

    # Adicionar ao state em dois formatos
    callback_context.state["format_specs"] = specs
    callback_context.state["format_specs_json"] = json.dumps(
        specs,
        indent=2,
        ensure_ascii=False
    )

    # Log para debug (opcional)
    if callback_context.state.get("enable_detailed_logging"):
        print(f"[FORMAT_SPECS] Injetadas especificações para formato: {formato}")

except ImportError:
    # Graceful degradation se arquivo não existir
    callback_context.state["format_specs"] = {}
    callback_context.state["format_specs_json"] = "{}"
```

**Importação necessária no topo do arquivo (linha ~16):**
```python
import json  # Já existe
```

## Fase 3: Atualizar Prompts dos Agentes

### 3.1 - `context_synthesizer` (linha 369)

**Adicionar ao instruction após linha 381:**

```python
## ESPECIFICAÇÕES DO FORMATO ESCOLHIDO
Use estas diretrizes específicas para {formato_anuncio}:
{format_specs_json}

Ajuste o briefing para respeitar:
- Limites de caracteres do formato
- Estilo de copy apropriado
- Estratégia de funil adequada
```

### 3.2 - `code_generator` (linha 473)

**Adicionar ao instruction após linha 484:**

```python
## DIRETRIZES OBRIGATÓRIAS DO FORMATO
Formato: {formato_anuncio}
Especificações que DEVEM ser seguidas:
{format_specs_json}

IMPORTANTE:
- Headline MÁXIMO {format_specs.copy.headline_max_chars} caracteres
- Corpo com estilo: {format_specs.copy.estilo}
- Aspect ratio OBRIGATÓRIO: {format_specs.visual.aspect_ratio}
- CTA preferencial: {format_specs.strategy.cta_preferencial}
```

### 3.3 - `code_reviewer` (linha 556)

**Adicionar ao instruction após linha 560:**

```python
## VALIDAÇÃO CONTRA ESPECIFICAÇÕES DO FORMATO
Especificações obrigatórias para {formato_anuncio}:
{format_specs_json}

REPROVAR se:
- Headline excede {format_specs.copy.headline_max_chars} caracteres
- Copy não segue estilo "{format_specs.copy.estilo}"
- Aspect ratio diferente de {format_specs.visual.aspect_ratio}
- CTA não alinhado com objetivo {format_specs.strategy.objetivo_principal}
- Visual não respeita composição: {format_specs.visual.composicao}
```

### 3.4 - `final_assembler` (linha 648)

**Modificar instruction - substituir linha 664 por:**

```python
Regras:
- Criar 3 variações RESPEITANDO formato {formato_anuncio}:
  * Reels: variar ganchos mantendo dinamismo
  * Stories: variar urgências (últimas horas, hoje só, etc)
  * Feed: variar ângulos narrativos
- Use aspect_ratio: {format_specs.visual.aspect_ratio}
- Headline máximo: {format_specs.copy.headline_max_chars} chars
- Estilo obrigatório: {format_specs.copy.estilo}
```

### 3.5 - `final_validator` (linha 677)

**Adicionar validação específica após linha 692:**

```python
7) Validações específicas do formato {formato_anuncio}:
   - Headline ≤ {format_specs.copy.headline_max_chars} caracteres
   - Aspect ratio = {format_specs.visual.aspect_ratio}
   - CTA alinhado com {format_specs.strategy.objetivo_principal}
```

## Fase 4: Testes de Validação

### 4.1 - Criar arquivo de teste: `tests/test_format_specs.py`

```python
import pytest
from app.format_specifications import FORMAT_SPECS

def test_format_specs_structure():
    """Valida estrutura básica das especificações"""
    for formato in ["Reels", "Stories", "Feed"]:
        assert formato in FORMAT_SPECS
        assert "copy" in FORMAT_SPECS[formato]
        assert "visual" in FORMAT_SPECS[formato]
        assert "strategy" in FORMAT_SPECS[formato]

def test_headline_limits():
    """Valida limites de headline por formato"""
    assert FORMAT_SPECS["Reels"]["copy"]["headline_max_chars"] == 40
    assert FORMAT_SPECS["Stories"]["copy"]["headline_max_chars"] == 30
    assert FORMAT_SPECS["Feed"]["copy"]["headline_max_chars"] == 125

def test_aspect_ratios():
    """Valida aspect ratios por formato"""
    assert FORMAT_SPECS["Reels"]["visual"]["aspect_ratio"] == "9:16"
    assert FORMAT_SPECS["Stories"]["visual"]["aspect_ratio"] == "9:16"
    assert FORMAT_SPECS["Feed"]["visual"]["aspect_ratio"] in ["1:1", "4:5"]
```

### 4.2 - Testes manuais via curl

```bash
# Teste Reels
curl -X POST http://localhost:8000/run \
  -d '{
    "appName": "app",
    "userId": "test",
    "sessionId": "test_reels",
    "newMessage": {
      "parts": [{
        "text": "landing_page_url: https://example.com\nobjetivo_final: leads\nperfil_cliente: jovens 18-24\nformato_anuncio: Reels"
      }]
    }
  }'

# Verificar:
# - Headline ≤ 40 chars
# - Aspect ratio 9:16
# - Copy com gancho forte
```

## Fase 5: Documentação

### Atualizar `README.md`

Adicionar seção após linha 106:

```markdown
### Especificações por Formato

O sistema agora aplica automaticamente diretrizes específicas baseadas no formato escolhido:

- **Reels**: Headlines curtas (40 chars), gancho forte, 9:16
- **Stories**: Urgência/escassez, CTAs diretos, 9:16
- **Feed**: Storytelling completo, até 2200 chars, 1:1 ou 4:5

As especificações são injetadas dinamicamente e validadas em todo o pipeline.
```

## Cronograma de Implementação

1. **Passo 1** (5 min): Criar `app/format_specifications.py`
2. **Passo 2** (10 min): Modificar `unpack_extracted_input_callback`
3. **Passo 3** (15 min): Atualizar os 5 prompts dos agentes
4. **Passo 4** (10 min): Criar testes básicos
5. **Passo 5** (5 min): Atualizar documentação
6. **Passo 6** (15 min): Testar com cada formato

**Tempo total estimado**: 60 minutos

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Specs muito grandes aumentam tokens | Média | Alto | Manter specs ENXUTAS, máximo 15 linhas por formato |
| Conflito com callbacks existentes | Baixa | Médio | Usar chaves únicas (format_specs, format_specs_json) |
| Placeholders não substituídos | Baixa | Alto | Fallback com valores default se specs ausentes |
| Incompatibilidade com vídeo | N/A | N/A | Já resolvido: tratamos como "still com estética de vídeo" |

## Critérios de Sucesso

✅ Headlines respeitam limite por formato
✅ Aspect ratios corretos automaticamente
✅ Copy segue estilo apropriado ao formato
✅ Validações rejeitam conteúdo fora das specs
✅ 3 variações adequadas ao formato
✅ Sem aumento significativo de latência
✅ Tokens não aumentam mais de 20%

## Rollback

Se necessário reverter:
1. Remover `app/format_specifications.py`
2. Reverter `unpack_extracted_input_callback`
3. Remover referências a `{format_specs}` e `{format_specs_json}` dos prompts
4. Sistema volta a funcionar como antes (genérico)

---

**Status**: Aguardando aprovação para implementação
**Autor**: Sistema ADK Instagram Ads
**Data**: 2025-01-14
**Baseado em**: Feedback do Codex + análise do código atual