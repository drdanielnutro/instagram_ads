# 📋 PLANO DETALHADO DE REFATORAÇÃO - SISTEMA DE ANÚNCIOS INSTAGRAM

## **RESUMO EXECUTIVO**
Refatoração completa do sistema de geração de anúncios para Instagram, focando em:
- Extração automática de conteúdo da landing page
- Controle do formato pelo usuário
- Remoção de vídeos (apenas imagens)
- Melhoria dos loops de qualidade
- Geração de múltiplas variações

---

## **1. CRIAR AGENTE `landing_page_analyzer`** 🔍

**Localização:** Após linha 287 (depois do `TaskIncrementer`)

**Implementação:**
```python
class LandingPageAnalyzer(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name=name)
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # Extrair URL do estado
        # Usar google_search com prompt específico para extrair conteúdo
        # Armazenar em ctx.session.state["landing_page_context"]
```

**Alternativa usando LlmAgent:**
```python
landing_page_analyzer = LlmAgent(
    model=config.worker_model,
    name="landing_page_analyzer",
    description="Extrai e analisa conteúdo da landing page",
    instruction="""[instruções para usar google_search e extrair]""",
    tools=[google_search],
    output_key="landing_page_context"
)
```

**Dados a extrair:**
- Título principal (H1)
- Proposta de valor
- Lista de benefícios
- CTAs principais
- Preços/ofertas
- Depoimentos/provas sociais
- Tom de voz da marca

---

## **2. MODIFICAR `input_processor` (linha 612-655)** ✏️

**Adicionar novo campo obrigatório:**

**Linha 624, adicionar:**
```python
- formato_anuncio (OBRIGATÓRIO: "Reels", "Stories" ou "Feed")
```

**Linha 628, modificar para:**
```python
- Tags: [landing_page_url]...[/landing_page_url], [objetivo_final]...[/objetivo_final], 
        [perfil_cliente]...[/perfil_cliente], [formato_anuncio]...[/formato_anuncio]
```

**Linha 643-645, adicionar:**
```python
"formato_anuncio": "string|null",
```

**Linha 154-156, adicionar no callback `unpack_extracted_input_callback`:**
```python
for k in ["landing_page_url", "objetivo_final", "perfil_cliente", "formato_anuncio"]:
```

---

## **3. MODIFICAR CLASSES DE MODELO (linhas 54-67)** 📦

**Classe `AdVisual` (linha 54-57):**
```python
class AdVisual(BaseModel):
    descricao_imagem: str  # MUDANÇA: era descricao
    aspect_ratio: Literal["9:16", "1:1", "4:5", "16:9"]
    # REMOVER: duracao
```

**Classe `AdItem` (linha 60-67):**
```python
class AdItem(BaseModel):
    landing_page_url: str
    formato: Literal["Reels", "Stories", "Feed"]
    copy: AdCopy  # Manter renomeado
    visual: AdVisual
    cta_instagram: Literal["Saiba mais", "Enviar mensagem", "Ligar", "Comprar agora", "Cadastre-se"]
    fluxo: str
    referencia_padroes: str
    contexto_landing: str  # NOVO CAMPO
```

---

## **4. ATUALIZAR PIPELINE `complete_pipeline` (linha 749-757)** 🔄

```python
complete_pipeline = SequentialAgent(
    name="complete_pipeline",
    description="Pipeline completo (Ads): input → análise LP → planejamento → execução → montagem → validação.",
    sub_agents=[
        input_processor,
        landing_page_analyzer,  # NOVO: adicionar aqui
        planning_pipeline,
        execution_pipeline
    ],
)
```

---

## **5. MODIFICAR `context_synthesizer` (linha 293-321)** 🔧

**Linha 302, adicionar:**
```python
- landing_page_context: {landing_page_context}
- formato_anuncio: {formato_anuncio}
```

**Linha 306, modificar para:**
```python
3) Formato definido pelo usuário: {formato_anuncio} - criar estratégia específica
```

---

## **6. ATUALIZAR `code_generator` (linha 375-453)** 🎨

**Linha 384, adicionar:**
```python
- landing_page_context: {landing_page_context}
- formato_anuncio: {formato_anuncio}
```

**Linha 425-433, modificar VISUAL_DRAFT:**
```python
- VISUAL_DRAFT:
  {
    "visual": {
      "descricao_imagem": "Descrição detalhada da imagem estática...",
      "aspect_ratio": "automático baseado em {formato_anuncio}"
    },
    "formato": "{formato_anuncio}"  # Usar o especificado pelo usuário
  }
```

**Remover todas as referências a "duracao"**

---

## **7. MELHORAR LOOPS DE QUALIDADE** 🔁

**Linha 664 (`plan_review_loop`):**
```python
max_iterations=5,  # Era 3
```

**Linha 687 (`code_review_loop`):**
```python
max_iterations=5,  # Era 3
```

**Linha 723 (`final_validation_loop`):**
```python
max_iterations=5,  # Era 3
```

---

## **8. ATUALIZAR `code_reviewer` (linha 455-499)** ✅

**Linha 462, adicionar validação:**
```python
Analise {generated_code} para a tarefa {current_task_info}. 
VALIDE ALINHAMENTO com {landing_page_context}
```

**Adicionar novo critério:**
```python
- ALINHAMENTO_LP:
  * Copy consistente com landing page?
  * Benefícios mencionados existem na página?
  * Tom de voz alinhado?
```

---

## **9. MODIFICAR `final_assembler` (linha 534-557)** 📝

**Linha 541, modificar para:**
```python
Monte **3 variações** de anúncio combinando `approved_code_snippets`.
```

**Linha 547, modificar:**
```python
- "visual": { "descricao_imagem", "aspect_ratio" } (sem duracao)
```

---

## **10. ATUALIZAR `final_validator` (linha 560-585)** ✔️

**Linha 571, modificar:**
```python
landing_page_url, formato, copy{headline,corpo,cta_texto}, 
visual{descricao_imagem,aspect_ratio}, cta_instagram, fluxo, referencia_padroes
```

**Linha 576, remover:**
```python
# REMOVER: 4) "duracao" combina regex ^\d{1,3}s$
```

---

## **11. MODIFICAR `config.py`** ⚙️

**Adicionar (se não existir):**
```python
max_web_fetch_retries: int = 3
enable_landing_page_analysis: bool = True
```

---

## **ORDEM DE EXECUÇÃO DO PLANO:**

1. ✅ Modificar classes de modelo (`AdVisual`, `AdItem`)
2. ✅ Atualizar `input_processor` para aceitar `formato_anuncio`
3. ✅ Criar `landing_page_analyzer`
4. ✅ Integrar no `complete_pipeline`
5. ✅ Atualizar todos os agentes LLM com novo contexto
6. ✅ Aumentar iterações dos loops
7. ✅ Ajustar validadores
8. ✅ Testar sistema completo

---

## **BENEFÍCIOS ESPERADOS:**

### **Antes:**
- ❌ Sem contexto da landing page
- ❌ Formato decidido pelo sistema
- ❌ Gera vídeos desnecessários
- ❌ Loop de qualidade limitado
- ❌ Apenas 1 anúncio por vez

### **Depois:**
- ✅ Extração automática da landing page
- ✅ Usuário controla o formato
- ✅ Apenas imagens (mais simples)
- ✅ Loop de qualidade robusto (5 iterações)
- ✅ 3 variações por execução

---

## **EXEMPLO DE USO APÓS REFATORAÇÃO:**

```
landing_page_url: https://clinicasaude.com.br
objetivo_final: agendamentos
perfil_cliente: Mulheres 30-50 anos, classe B, preocupadas com saúde preventiva
formato_anuncio: Feed
```

**Sistema irá:**
1. Analisar a landing page automaticamente
2. Extrair proposta de valor, benefícios, CTAs
3. Gerar 3 variações de anúncio para Feed
4. Cada uma alinhada com o conteúdo real da página
5. Passar por 5 iterações de qualidade

---

## **RISCOS E MITIGAÇÕES:**

| Risco | Mitigação |
|-------|-----------|
| google_search pode não extrair bem o conteúdo | Implementar fallback com prompt melhorado |
| Aumento de tempo de processamento | Paralelizar onde possível |
| Maior consumo de tokens | Otimizar prompts e cachear resultados |

---

## **MÉTRICAS DE SUCESSO:**

- [ ] Taxa de alinhamento copy/landing page > 90%
- [ ] Tempo de geração < 3 minutos
- [ ] Aprovação na primeira tentativa > 70%
- [ ] Satisfação do usuário com controle do formato
- [ ] Qualidade das 3 variações geradas

---

**Este plano está 100% baseado no código real, com números de linha exatos e nomes corretos!**

**Data de criação:** 2025-09-12
**Versão:** 1.0
**Autor:** Sistema de Análise ADK