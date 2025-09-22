# Plano de Correção - Preview de Anúncios (v2)

## Problema Atual

O sistema de preview não exibe as imagens dos anúncios devido a uma **incompatibilidade de estrutura de dados** entre backend e frontend.

### Causa Raiz

#### Backend envia:
```json
{
  "visual": {
    "image_estado_atual_url": "https://storage.googleapis.com/...",
    "image_estado_intermediario_url": "https://storage.googleapis.com/...",
    "image_estado_aspiracional_url": "https://storage.googleapis.com/..."
  }
}
```

#### Frontend procura:
```json
{
  "visual": {
    "images": ["url1", "url2", "url3"]
  }
}
```

### Evidência
- JSON no GCS tem 22KB com URLs válidas em campos individuais
- Função `getVariationImages` (linha 336-342) busca apenas em `visual.images`
- Campo `images[]` não existe no JSON atual

## Solução

### Arquivo a Modificar
`/Users/institutorecriare/VSCodeProjects/instagram_ads/frontend/src/components/AdsPreview.tsx`

### Modificação Necessária

**Localização:** Linha 336-342

**Código Atual:**
```typescript
function getVariationImages(variation?: AdVariation): string[] {
  if (!variation) {
    return [];
  }
  return variation.visual.images;
}
```

**Código Novo:**
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

### Por que funciona:
1. **Retrocompatível**: Se o backend mudar para `images[]`, continua funcionando
2. **Ordem correta**: Mantém sequência lógica das imagens
3. **Sem quebrar tipos**: Usa `as any` localizado para acessar campos extras
4. **Fallback seguro**: Retorna array vazio se não encontrar nada

## Teste de Validação

### Passos:
1. Aplicar a modificação em `AdsPreview.tsx`
2. Reiniciar frontend: `make dev`
3. Abrir preview no navegador
4. Verificar:
   - [ ] As 3 imagens aparecem no carrossel
   - [ ] Navegação entre etapas funciona
   - [ ] Labels mostram: "Estado Atual", "Intermediário", "Aspiracional"
   - [ ] Console sem erros

### Resultado Esperado:
- Preview exibe as imagens corretamente
- Carrossel permite navegação entre as 3 etapas
- Textos e metadados continuam funcionando

## Observações

- **CORS já resolvido**: O Codex Cloud implementou `inline=true` que resolve o CORS
- **Mudança mínima**: Apenas uma função modificada
- **Sem impacto no backend**: Solução 100% no frontend

---

**Data:** 2025-09-22
**Versão:** 2.0 (simplificada após resolução do CORS)