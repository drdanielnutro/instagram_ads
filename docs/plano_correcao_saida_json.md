# Plano de Correção: Falhas na Geração de Imagens no JSON Final

**Data**: 2025-10-01
**Autor**: Análise técnica do sistema Instagram Ads
**Status**: 🚨 CRÍTICO - Geração de imagens 100% falha

---

## 🎯 Sumário Executivo

O pipeline de fallback StoryBrand foi executado com **sucesso total** (score 1.0), gerando 3 variações de anúncios com copy de alta qualidade. Porém, **todas as 3 variações falharam na geração de imagens**, impedindo a entrega de anúncios completos.

### Estatísticas Finais:
- ✅ **Fallback StoryBrand**: 16/16 seções concluídas (100%)
- ✅ **Copy Generation**: 3/3 variações aprovadas (100%)
- ❌ **Image Generation**: 0/3 imagens geradas (0%)
- ⚠️ **Taxa de Sucesso Geral**: 66% (bloqueador crítico presente)

---

## 🔍 Problema 1: Modelo de Geração de Imagens Inexistente

### **Erro Observado (Variação 2):**
```json
{
  "image_generation_error": "Falha na geração de imagem após 3 tentativas: 404 NOT_FOUND. {'error': {'code': 404, 'message': 'Publisher Model `projects/instagram-ads-472021/locations/us-central1/publishers/google/models/gemini-2.5-flash-image-preview` was not found or your project does not have access to it.'}}"
}
```

### **Causa Raiz:**
O modelo `gemini-2.5-flash-image-preview` está hardcoded no código, mas **não existe** ou o projeto não tem acesso a ele.

### **Localização Exata do Problema:**
**Arquivo**: `/home/deniellmed/instagram_ads/app/tools/generate_transformation_images.py`
**Linha**: 24
**Código Problemático**:
```python
_MODEL_NAME = "gemini-2.5-flash-image-preview"
```

### **Verificação Necessária:**
1. Confirmar se o modelo existe no Vertex AI
2. Verificar se o projeto `instagram-ads-472021` tem acesso ao modelo
3. Verificar se a região `us-central1` suporta este modelo
4. Consultar documentação oficial: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions

### **Modelos Alternativos Possíveis:**
- `imagen-3.0-generate-001` (Imagen 3.0)
- `imagegeneration@006` (Imagen 2)
- `gemini-pro-vision` (apenas análise, não geração)

### **Solução Proposta:**
```python
# Arquivo: /home/deniellmed/instagram_ads/app/tools/generate_transformation_images.py
# Linha: 24

# ANTES (INCORRETO):
_MODEL_NAME = "gemini-2.5-flash-image-preview"

# DEPOIS (CORRETO):
_MODEL_NAME = "imagen-3.0-generate-001"  # ou outro modelo disponível
```

### **Impacto:**
🔴 **CRÍTICO** - Bloqueia 100% da geração de imagens. Sem imagens, os anúncios não podem ser publicados no Instagram.

---

## 🔍 Problema 2: Validação Rígida de Prompts Visuais

### **Erro Observado (Variação 1):**
```json
{
  "prompt_estado_atual": null,
  "prompt_estado_intermediario": null,
  "prompt_estado_aspiracional": "Editorial fashion photo...",
  "image_generation_error": "⚠️ Variação 1: campos ausentes para geração de imagens: prompt_estado_atual, prompt_estado_intermediario"
}
```

### **Erro Observado (Variação 3):**
```json
{
  "prompt_estado_atual": "Left side of a diptych...",
  "prompt_estado_intermediario": null,
  "prompt_estado_aspiracional": "Right side of a diptych...",
  "image_generation_error": "⚠️ Variação 3: campos ausentes para geração de imagens: prompt_estado_intermediario"
}
```

### **Causa Raiz:**
O sistema valida rigidamente que **sempre** devem existir 3 prompts (atual, intermediário, aspiracional), mesmo quando o conceito visual não requer transformação em 3 etapas.

**Casos que não precisam de 3 estados:**
- **Single image**: Apenas estado aspiracional (Variação 1)
- **Before/After (diptych)**: Apenas atual + aspiracional (Variação 3)
- **Carousel**: Múltiplos estados independentes

### **Localização do Problema:**

Preciso identificar onde está a validação. Provavelmente em:

**Arquivo Suspeito 1**: `/home/deniellmed/instagram_ads/app/tools/generate_transformation_images.py`
**Método**: `generate_transformation_images` ou similar

**Arquivo Suspeito 2**: `/home/deniellmed/instagram_ads/app/callbacks/` (algum callback de validação)

**Arquivo Suspeito 3**: Schema de validação em `/home/deniellmed/instagram_ads/app/schemas/` ou models

### **Solução Proposta:**

#### **Opção A: Flexibilizar Validação (RECOMENDADO)**
```python
# Pseudocódigo - ajustar no arquivo real

def validate_image_prompts(prompts: dict) -> tuple[bool, str]:
    """Valida prompts de imagem de forma flexível."""

    # Pelo menos UM prompt deve existir
    has_any = any([
        prompts.get('prompt_estado_atual'),
        prompts.get('prompt_estado_intermediario'),
        prompts.get('prompt_estado_aspiracional')
    ])

    if not has_any:
        return False, "Nenhum prompt de imagem fornecido"

    # Se tem atual + aspiracional, mas não intermediário = OK (before/after)
    # Se tem apenas aspiracional = OK (single image)
    # Se tem todos os 3 = OK (transformação completa)

    return True, ""
```

#### **Opção B: Gerar Prompts Faltantes Automaticamente**
```python
# Se apenas aspiracional existe, criar estados anteriores fictícios
if not prompts.get('prompt_estado_atual') and prompts.get('prompt_estado_aspiracional'):
    # Para single image, duplicar o aspiracional como fallback
    prompts['prompt_estado_atual'] = prompts['prompt_estado_aspiracional']
    prompts['prompt_estado_intermediario'] = prompts['prompt_estado_aspiracional']
```

### **Impacto:**
⚠️ **MODERADO** - Impede variações válidas de serem geradas, mas workaround é possível (sempre gerar 3 prompts).

---

## 🔍 Problema 3: Inconsistência nas Instruções do Agent

### **Observação:**
O agent `code_generator` para visuais não está seguindo consistentemente as instruções:
- **Variação 1**: Gerou apenas 1 prompt (aspiracional)
- **Variação 2**: Gerou 3 prompts corretamente
- **Variação 3**: Gerou 2 prompts (atual + aspiracional)

### **Causa Raiz Provável:**
O prompt system instruction do agent visual não é suficientemente explícito sobre SEMPRE gerar 3 prompts, OU a validação está bloqueando conceitos visuais válidos que não precisam de 3 estados.

### **Localização Provável:**

**Arquivo**: Algum agent de task em `/home/deniellmed/instagram_ads/app/agent.py` ou `/home/deniellmed/instagram_ads/app/agents/`

Procurar por agents relacionados a:
- `visual_draft`
- `image_generation`
- `VISUAL_DRAFT` (categoria de task)

### **Solução Proposta:**

#### **Opção A: Clarificar Instruction do Agent**
```python
# No agent de geração visual, reforçar instruction:
instruction = """
Você DEVE SEMPRE gerar 3 prompts, mesmo que o conceito visual seja simples:
1. prompt_estado_atual: Situação problema (antes)
2. prompt_estado_intermediario: Momento de transição (descoberta/ação)
3. prompt_estado_aspiracional: Transformação completa (depois)

Mesmo para single image, crie uma narrativa mínima de transformação.
"""
```

#### **Opção B: Adaptar Validação (preferível - ver Problema 2)**

### **Impacto:**
⚠️ **BAIXO** - Problema comportamental do LLM, não técnico. Pode ser resolvido via instruction ou validação flexível.

---

## 📋 Arquivos a Serem Modificados

### **1. Correção Crítica (Problema 1):**
```
/home/deniellmed/instagram_ads/app/tools/generate_transformation_images.py
```
- **Linha 24**: Alterar `_MODEL_NAME` para modelo válido
- **Método afetado**: Qualquer método que use `_MODEL_NAME`
- **Prioridade**: 🔴 CRÍTICA

### **2. Flexibilização de Validação (Problema 2):**
```
/home/deniellmed/instagram_ads/app/tools/generate_transformation_images.py
```
OU
```
/home/deniellmed/instagram_ads/app/callbacks/ (arquivo a ser identificado)
```
- **Método afetado**: Função de validação de prompts
- **Prioridade**: ⚠️ ALTA

### **3. Refinamento de Instruction (Problema 3 - Opcional):**
```
/home/deniellmed/instagram_ads/app/agent.py
```
- **Agentes afetados**: Agents de categoria `VISUAL_DRAFT`
- **Ajuste**: Instruction/prompt do agent
- **Prioridade**: ⚠️ MÉDIA

---

## 🧪 Testes Necessários Após Correção

### **Teste 1: Verificar Modelo Disponível**
```bash
# Listar modelos disponíveis no projeto
gcloud ai models list \
  --project=instagram-ads-472021 \
  --region=us-central1 \
  --filter="displayName:image OR displayName:imagen"
```

### **Teste 2: Teste Unitário de Geração de Imagem**
```python
# Criar script de teste isolado
from app.tools.generate_transformation_images import generate_transformation_images

result = generate_transformation_images(
    prompt_atual="Woman frustrated with wardrobe",
    prompt_intermediario="Woman discovering Loja Flamê online",
    prompt_aspiracional="Woman confident in Tricot Bicolor outfit",
    aspect_ratio="4:5"
)

assert result.success, f"Falha: {result.error}"
```

### **Teste 3: Teste End-to-End**
```bash
# Executar pipeline completo com ENABLE_IMAGE_GENERATION=true
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "landing_page_url": "https://www.lojaflame.com.br/",
    "formato_anuncio": "Feed",
    "foco": "Conjunto Tricot Bicolor",
    ...
  }'

# Verificar que JSON final contém URLs de imagens válidas
```

---

## 📊 Verificações de Qualidade

### **Checklist Pré-Implementação:**
- [ ] Confirmar modelo de imagem disponível via `gcloud ai models list`
- [ ] Revisar documentação Vertex AI sobre modelos de geração de imagem
- [ ] Identificar todos os lugares onde `_MODEL_NAME` é usado
- [ ] Verificar se há configuração de modelo em `app/.env` ou `app/config.py`

### **Checklist Pós-Implementação:**
- [ ] Teste unitário de geração de imagem passa
- [ ] Teste end-to-end gera 3 variações com imagens
- [ ] Nenhuma variação tem `image_generation_error`
- [ ] URLs de imagens são válidas e acessíveis
- [ ] Imagens respeitam aspect ratio 4:5
- [ ] Logs não mostram erros 404

---

## 🔗 Referências Úteis

1. **Vertex AI Model Versions**:
   https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions

2. **Imagen API Documentation**:
   https://cloud.google.com/vertex-ai/docs/generative-ai/image/overview

3. **ADK Documentation**:
   https://github.com/googleapis/genai-python-adk

4. **Project Configuration**:
   - Project ID: `instagram-ads-472021`
   - Region: `us-central1`
   - Service Account: Verificar em `app/.env` (GOOGLE_APPLICATION_CREDENTIALS)

---

## ⏱️ Estimativa de Esforço

| Tarefa | Complexidade | Tempo Estimado |
|--------|-------------|----------------|
| Identificar modelo correto | Baixa | 15 min |
| Alterar `_MODEL_NAME` | Trivial | 5 min |
| Testar geração de imagem | Média | 30 min |
| Flexibilizar validação | Média | 45 min |
| Testes end-to-end | Média | 30 min |
| **TOTAL** | - | **~2 horas** |

---

## 🎯 Próximos Passos Imediatos

1. **URGENTE**: Executar `gcloud ai models list` para identificar modelo disponível
2. **URGENTE**: Substituir modelo em `generate_transformation_images.py:24`
3. **IMPORTANTE**: Testar geração de imagem isoladamente
4. **OPCIONAL**: Flexibilizar validação de prompts
5. **OPCIONAL**: Ajustar instruction de agents visuais

---

## 📝 Notas Adicionais

### **Flag Relevante:**
```bash
# app/.env
ENABLE_IMAGE_GENERATION=true  # ✅ Está habilitada
```

### **StoryBrand Fallback:**
O fallback funcionou **perfeitamente**. Score 1.0 em todas as 16 seções. Nenhum problema no pipeline principal, apenas na geração de imagens.

### **Qualidade do Output:**
As 3 variações de copy geradas são de **alta qualidade**, todas aprovadas nos reviews com comentários "excelente" e "perfeitamente alinhado". O problema está exclusivamente na camada de geração visual.

---

**Fim do Relatório**
