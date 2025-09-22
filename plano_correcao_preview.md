# Plano de Correção - Preview de Anúncios

## Problema Identificado

### Diagnóstico
O sistema de preview não está exibindo as imagens dos anúncios, mesmo que elas existam no GCS.

### Causa Raiz
**Incompatibilidade de estrutura de dados** entre backend e frontend:

#### Backend envia (formato atual):
```json
{
  "visual": {
    "image_estado_atual_url": "https://storage.googleapis.com/...",
    "image_estado_intermediario_url": "https://storage.googleapis.com/...",
    "image_estado_aspiracional_url": "https://storage.googleapis.com/..."
  }
}
```

#### Frontend espera (formato esperado):
```json
{
  "visual": {
    "images": [
      "https://storage.googleapis.com/...",
      "https://storage.googleapis.com/...",
      "https://storage.googleapis.com/..."
    ]
  }
}
```

### Evidências
1. **JSON no GCS confirmado** com 22KB contendo URLs válidas
2. **Campos verificados** via `gsutil` e `grep`:
   - ✅ `image_estado_atual_url` presente
   - ✅ `image_estado_intermediario_url` presente
   - ✅ `image_estado_aspiracional_url` presente
   - ❌ `images[]` ausente
3. **Função `getVariationImages`** busca apenas em `visual.images`

## Solução Proposta

### Arquivo a Modificar
- **Caminho:** `/Users/institutorecriare/VSCodeProjects/instagram_ads/frontend/src/components/AdsPreview.tsx`
- **Função:** `getVariationImages` (linhas 336-347)
- **Tipo de mudança:** Adaptativa e retrocompatível

### Implementação

#### Código Atual (problemático):
```typescript
function getVariationImages(variation?: AdVariation): string[] {
  if (!variation || !variation.visual) {
    return [];
  }

  // Defesa contra campo images ausente ou undefined
  if (!variation.visual.images || !Array.isArray(variation.visual.images)) {
    return [];
  }

  return variation.visual.images;
}
```

#### Código Proposto (solução):
```typescript
function getVariationImages(variation?: AdVariation): string[] {
  if (!variation || !variation.visual) {
    return [];
  }

  // Primeiro tenta usar o campo images se existir (compatibilidade futura)
  if (variation.visual.images && Array.isArray(variation.visual.images)) {
    return variation.visual.images;
  }

  // Fallback: procura campos individuais de URL (formato atual do backend)
  const images: string[] = [];
  const visual = variation.visual as any;

  // Ordem mantida: estado_atual → estado_intermediario → estado_aspiracional
  if (visual.image_estado_atual_url) {
    images.push(visual.image_estado_atual_url);
  }
  if (visual.image_estado_intermediario_url) {
    images.push(visual.image_estado_intermediario_url);
  }
  if (visual.image_estado_aspiracional_url) {
    images.push(visual.image_estado_aspiracional_url);
  }

  return images;
}
```

### Vantagens da Solução

1. **Retrocompatível**: Continua funcionando se o backend mudar para `images[]`
2. **Não invasiva**: Mudança isolada em uma única função
3. **Ordem preservada**: Mantém sequência lógica (atual → intermediário → aspiracional)
4. **Robusta**: Trata ambos os formatos sem quebrar
5. **Sem mudanças no backend**: Resolve o problema apenas no frontend

## Fluxo de Dados Corrigido

```
GCS (JSON com URLs individuais)
    ↓
Backend /api/delivery/final/download
    ↓
Frontend fetchPreviewData()
    ↓
normalizeVariations()
    ↓
getVariationImages() [MODIFICADO]
    ↓
ImageCarousel (recebe array correto)
    ↓
<img src={images[0|1|2]} /> ✅
```

## Testes de Validação

### Pré-condições
- JSON no GCS contendo URLs válidas (já confirmado)
- Meta.json apontando para arquivo correto

### Procedimento de Teste
1. Aplicar a modificação no arquivo `AdsPreview.tsx`
2. Reiniciar o frontend: `make dev`
3. Abrir o preview no navegador
4. Verificar:
   - [ ] Imagens aparecem no carrossel
   - [ ] Navegação entre 3 etapas funciona
   - [ ] Labels corretos (Estado Atual, Intermediário, Aspiracional)
   - [ ] Sem erros no console

### Critérios de Sucesso
- Todas as 3 imagens de cada variação devem carregar
- Navegação fluida entre imagens
- Sem mensagens de erro no console

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| URLs expiradas | Baixa | Alto | Signed URLs têm 24h de validade |
| Campos diferentes em produção | Baixa | Médio | Código trata ambos formatos |
| Quebra de tipos TypeScript | Nenhuma | - | Uso de `as any` localizado |

## Alternativas Consideradas

1. **Modificar o backend** para enviar `images[]`
   - ❌ Rejeitada: Mais complexo, afeta múltiplos componentes

2. **Criar transformer no frontend**
   - ❌ Rejeitada: Adiciona camada desnecessária

3. **Modificar tipo `VisualInfo`**
   - ❌ Rejeitada: Quebra contratos TypeScript

## Conclusão

Esta solução resolve o problema imediato com mínimo impacto e máxima compatibilidade. A modificação é cirúrgica, testável e mantém o sistema funcionando para ambos os formatos de dados.

## Próximos Passos

1. ✅ Revisar este plano
2. ⏳ Aplicar modificação em `getVariationImages`
3. ⏳ Testar no ambiente local
4. ⏳ Confirmar funcionamento
5. ⏳ Commit das mudanças

---

**Data:** 2025-09-22
**Autor:** Claude + Usuario
**Versão:** 1.0