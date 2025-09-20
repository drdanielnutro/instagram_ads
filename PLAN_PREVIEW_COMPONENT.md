# PLANO ATUALIZADO: Componente de Preview de Anúncios

## 1. ATIVAÇÃO DO PREVIEW

### Condição de exibição:
```typescript
// Em App.tsx, mostrar botão quando:
if (deliveryMeta?.ok) {
  <Button onClick={openPreview}>Preview</Button>
}
```

### Fluxo de dados:
1. Clicar no botão "Preview"
2. Fazer GET `/api/delivery/final/download?user_id=${userId}&session_id=${sessionId}`
3. Se resposta for JSON direto → usar
4. Se resposta for `{ signed_url: "..." }` → fazer fetch adicional
5. Parsear JSON e abrir modal com dados

## 2. ESTRUTURA SIMPLIFICADA (MVP)

### Arquivo único inicial:
```
frontend/src/components/AdsPreview.tsx
```
Contendo todos os sub-componentes internos. Só extrair se ficar complexo demais.

## 3. COMPONENTE PRINCIPAL

```typescript
interface AdsPreviewProps {
  userId: string;
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

// Estado interno:
const [variations, setVariations] = useState<AdVariation[]>([]);
const [currentVariation, setCurrentVariation] = useState(0);
const [currentImageIndex, setCurrentImageIndex] = useState(0);
const [isFetchingPreview, setIsFetchingPreview] = useState(false);
const [imageErrors, setImageErrors] = useState<Map<string, boolean>>(new Map());
```

## 4. LAYOUT DO MODAL

### Estrutura base (usando Radix Dialog):
```tsx
<Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
  <Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 bg-black/50" />
    <Dialog.Content className="fixed inset-0 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 bg-white rounded-lg max-w-4xl w-full h-full md:h-[90vh] overflow-hidden">

      {/* Header com X para fechar */}
      <div className="flex justify-between p-4 border-b">
        <h2>Preview do Anúncio</h2>
        <Dialog.Close asChild>
          <Button variant="ghost" size="icon">✕</Button>
        </Dialog.Close>
      </div>

      {/* Navegação de variações */}
      <div className="flex gap-2 p-4 justify-center">
        <Button
          variant={currentVariation === 0 ? "default" : "outline"}
          onClick={() => {
            setCurrentVariation(0);
            setCurrentImageIndex(0);
          }}
        >1</Button>
        <Button
          variant={currentVariation === 1 ? "default" : "outline"}
          onClick={() => {
            setCurrentVariation(1);
            setCurrentImageIndex(0);
          }}
        >2</Button>
        <Button
          variant={currentVariation === 2 ? "default" : "outline"}
          onClick={() => {
            setCurrentVariation(2);
            setCurrentImageIndex(0);
          }}
        >3</Button>
      </div>

      {/* Conteúdo principal */}
      <div className="flex flex-col md:flex-row gap-4 p-4 overflow-auto">
        {/* Lado esquerdo: Dispositivo com carrossel */}
        <div className="flex-1">
          {renderDevice()}
        </div>

        {/* Lado direito: Textos */}
        <div className="flex-1 space-y-4">
          {renderTextContent()}
        </div>
      </div>

      {/* Botão atualizar */}
      <div className="p-4 border-t">
        <Button onClick={fetchPreviewData} disabled={isFetchingPreview}>
          Atualizar imagens
        </Button>
      </div>

    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
```

## 5. RENDERIZAÇÃO POR FORMATO

### Feed (4:5 ou 1:1):
```tsx
function renderFeedDevice() {
  const variation = variations[currentVariation];

  return (
    <div className="mx-auto max-w-sm">
      {/* Moldura simples */}
      <div className="rounded-lg border-8 border-gray-900 overflow-hidden">
        {/* Carrossel de imagens */}
        <ImageCarousel
          images={[
            variation.visual.image_estado_atual_url,
            variation.visual.image_estado_intermediario_url,
            variation.visual.image_estado_aspiracional_url
          ]}
          aspectRatio={variation.visual.aspect_ratio}
          currentIndex={currentImageIndex}
          onIndexChange={setCurrentImageIndex}
          currentVariation={currentVariation}
          onError={handleImageError}
        />
      </div>

      {/* Texto abaixo como no Instagram Feed */}
      <div className="mt-4 p-4 bg-gray-50 rounded">
        <p className="font-bold">{variation.copy.headline}</p>
        <p className="text-sm mt-2">{variation.copy.corpo}</p>
        <Button className="mt-3">{variation.copy.cta_texto}</Button>
      </div>
    </div>
  );
}
```

### Reels/Stories (9:16):
```tsx
function renderVerticalDevice() {
  const variation = variations[currentVariation];

  return (
    <div className="mx-auto max-w-xs">
      <div className="rounded-[2.5rem] border-8 border-gray-900 overflow-hidden relative">
        {/* Carrossel */}
        <ImageCarousel
          images={[
            variation.visual.image_estado_atual_url,
            variation.visual.image_estado_intermediario_url,
            variation.visual.image_estado_aspiracional_url
          ]}
          aspectRatio={variation.visual.aspect_ratio}
          currentIndex={currentImageIndex}
          onIndexChange={setCurrentImageIndex}
          currentVariation={currentVariation}
          onError={handleImageError}
        />

        {/* Safe zones overlay */}
        <div className="absolute inset-0 pointer-events-none">
          {/* Topo 14% */}
          <div className="h-[14%] bg-black/20" />
          {/* Rodapé 25% */}
          <div className="absolute bottom-0 w-full h-[25%] bg-black/20" />
        </div>
      </div>

      {/* Nota sobre texto */}
      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
        <p className="text-xs">💡 Em Reels/Stories, o texto apareceria sobreposto na área central da imagem</p>
      </div>
    </div>
  );
}
```

## 6. COMPONENTE CARROSSEL

```tsx
interface ImageCarouselProps {
  images: string[];
  aspectRatio: string;
  currentIndex: number;
  onIndexChange: (index: number) => void;
  currentVariation: number;
  onError: (variation: number, imageIndex: number) => void;
}

function ImageCarousel({ images, aspectRatio, currentIndex, onIndexChange, currentVariation, onError }: ImageCarouselProps) {
  return (
    <div className={`relative ${getAspectRatioClass(aspectRatio)}`}>
      {/* Imagem atual */}
      <img
        src={images[currentIndex]}
        onError={() => onError(currentVariation, currentIndex)}
        className="w-full h-full object-cover"
      />

      {/* Navegação com botões desabilitados nos limites */}
      <button
        onClick={() => onIndexChange(currentIndex - 1)}
        disabled={currentIndex === 0}
        className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 text-white p-2 rounded-full disabled:opacity-30"
      >←</button>
      <button
        onClick={() => onIndexChange(currentIndex + 1)}
        disabled={currentIndex === 2}
        className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 text-white p-2 rounded-full disabled:opacity-30"
      >→</button>

      {/* Dots */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
        {images.map((_, i) => (
          <button
            key={i}
            onClick={() => onIndexChange(i)}
            className={`w-2 h-2 rounded-full ${i === currentIndex ? 'bg-white' : 'bg-white/50'}`}
          />
        ))}
      </div>

      {/* Labels das etapas */}
      <div className="absolute top-4 left-4 bg-black/50 text-white px-2 py-1 rounded text-xs">
        {['Estado Atual', 'Intermediário', 'Aspiracional'][currentIndex]}
      </div>
    </div>
  );
}
```

## 7. ÁREA DE TEXTOS

```tsx
function renderTextContent() {
  const v = variations[currentVariation];

  return (
    <div className="space-y-4">
      {/* Informações principais */}
      <Card>
        <CardHeader>Copy do Anúncio</CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-gray-500">Headline</label>
              <p className="font-semibold">{v.copy.headline}</p>
            </div>
            <div>
              <label className="text-xs text-gray-500">Corpo</label>
              <p>{v.copy.corpo}</p>
            </div>
            <div>
              <label className="text-xs text-gray-500">CTA</label>
              <p className="text-blue-600">{v.copy.cta_texto}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metadados */}
      <Card>
        <CardHeader>Informações do Anúncio</CardHeader>
        <CardContent>
          <dl className="space-y-1 text-sm">
            <div><dt className="inline text-gray-500">Formato:</dt> <dd className="inline">{v.formato}</dd></div>
            <div><dt className="inline text-gray-500">CTA Instagram:</dt> <dd className="inline">{v.cta_instagram}</dd></div>
            <div><dt className="inline text-gray-500">Fluxo:</dt> <dd className="inline">{v.fluxo}</dd></div>
            <div><dt className="inline text-gray-500">Landing:</dt> <dd className="inline"><a href={v.landing_page_url} className="text-blue-600 underline">Ver página</a></dd></div>
          </dl>
        </CardContent>
      </Card>

      {/* Referência (colapsável) */}
      <details className="border rounded p-3">
        <summary className="cursor-pointer font-medium">Referências e Padrões</summary>
        <p className="mt-2 text-sm text-gray-600">{v.referencia_padroes}</p>
      </details>

      {/* StoryBrand (opcional, colapsável) */}
      <details className="border rounded p-3">
        <summary className="cursor-pointer font-medium">Contexto StoryBrand</summary>
        <pre className="mt-2 text-xs overflow-auto">
          {JSON.stringify(v.contexto_landing, null, 2)}
        </pre>
      </details>
    </div>
  );
}
```

## 8. FETCH E ATUALIZAÇÃO DE DADOS

```typescript
async function fetchPreviewData() {
  setIsFetchingPreview(true);
  setImageErrors(new Map()); // Limpar erros anteriores

  // Resetar índices para evitar out of bounds
  setCurrentVariation(0);
  setCurrentImageIndex(0);

  try {
    // Fetch inicial
    const response = await fetch(`/api/delivery/final/download?user_id=${userId}&session_id=${sessionId}`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const contentType = response.headers.get('content-type');
    let jsonData;

    if (contentType?.includes('application/json')) {
      const data = await response.json();

      if (data.signed_url) {
        // Fetch adicional se necessário
        const signedResponse = await fetch(data.signed_url);

        if (!signedResponse.ok) {
          throw new Error(`Failed to fetch from signed URL: ${signedResponse.status}`);
        }

        const signedContentType = signedResponse.headers.get('content-type');

        if (signedContentType?.includes('application/json')) {
          jsonData = await signedResponse.json();
        } else {
          // Para streams ou outros tipos
          const text = await signedResponse.text();
          jsonData = JSON.parse(text);
        }
      } else {
        jsonData = data;
      }
    } else {
      // Para application/octet-stream ou similar
      const text = await response.text();
      jsonData = JSON.parse(text);
    }

    setVariations(jsonData);
  } catch (error) {
    console.error('Erro ao carregar preview:', error);
    // Mostrar toast de erro
  } finally {
    setIsFetchingPreview(false);
  }
}

// Chamar ao abrir o modal
useEffect(() => {
  if (isOpen) {
    fetchPreviewData();
  }
}, [isOpen, userId, sessionId]);
```

## 9. TRATAMENTO DE ERROS DE IMAGEM

```tsx
function handleImageError(variationIdx: number, imageIdx: number) {
  setImageErrors(prev => {
    const next = new Map(prev);
    next.set(`${variationIdx}-${imageIdx}`, true);
    return next;
  });
}

// No carrossel, mostrar placeholder se houver erro:
{imageErrors.get(`${currentVariation}-${currentImageIndex}`) ? (
  <div className="flex items-center justify-center h-full bg-gray-100">
    <div className="text-center">
      <p>Não foi possível carregar esta etapa</p>
      <Button onClick={() => fetchPreviewData()} size="sm" className="mt-2">
        Atualizar
      </Button>
    </div>
  </div>
) : (
  <img src={imageUrl} onError={handleError} />
)}
```

## 10. RESPONSIVIDADE

### Mobile:
- Modal fullscreen
- Layout vertical (imagem em cima, textos embaixo)
- Navegação de variações como tabs fixas no topo

### Desktop:
- Modal centralizado com max-width
- Layout lado a lado (dispositivo à esquerda, textos à direita)
- Mais espaço para informações detalhadas

## 11. INTEGRAÇÃO NO App.tsx

```tsx
// Em App.tsx
const [showPreview, setShowPreview] = useState(false);

{/* Botão aparece quando JSON está pronto */}
{deliveryMeta?.ok && (
  <div className="flex gap-2">
    <Button onClick={downloadJson}>Baixar JSON</Button>
    <Button onClick={() => setShowPreview(true)}>Preview</Button>
  </div>
)}

{/* Componente do preview */}
<AdsPreview
  userId={userId}
  sessionId={sessionId}
  isOpen={showPreview}
  onClose={() => setShowPreview(false)}
/>
```

## 12. TIPOS TYPESCRIPT

```typescript
// frontend/src/types/ad-preview.ts
interface AdVariation {
  landing_page_url: string;
  formato: "Feed" | "Reels" | "Stories";
  copy: {
    headline: string;
    corpo: string;
    cta_texto: string;
  };
  visual: {
    descricao_imagem: string;
    prompt_estado_atual: string;
    prompt_estado_intermediario: string;
    prompt_estado_aspiracional: string;
    aspect_ratio: "4:5" | "9:16" | "1:1";
    image_estado_atual_gcs: string;
    image_estado_atual_url: string;
    image_estado_intermediario_gcs: string;
    image_estado_intermediario_url: string;
    image_estado_aspiracional_gcs: string;
    image_estado_aspiracional_url: string;
  };
  cta_instagram: string;
  fluxo: string;
  referencia_padroes: string;
  contexto_landing: {
    storybrand_persona: string;
    storybrand_dores: string[];
    storybrand_proposta: string;
    storybrand_autoridade: string;
    storybrand_beneficios: string[];
    storybrand_transformacao: string;
    storybrand_cta_principal: string;
    storybrand_urgencia: string[];
  };
}
```

## 13. HELPERS

```typescript
// Função para obter classe Tailwind do aspect ratio
function getAspectRatioClass(ratio: string): string {
  switch(ratio) {
    case "9:16": return "aspect-[9/16]";
    case "4:5": return "aspect-[4/5]";
    case "1:1": return "aspect-square";
    default: return "aspect-[4/5]";
  }
}

// Função para determinar se é formato vertical
function isVerticalFormat(formato: string): boolean {
  return formato === "Reels" || formato === "Stories";
}
```

## 14. ESTILOS E TEMAS

- Usar cores neutras já presentes no app (tons de cinza)
- Acentos suaves para elementos interativos
- Transições suaves (fade-in/out para modal, slide para carrossel)
- Sombras leves para profundidade
- Bordas arredondadas consistentes com o design existente

## 15. CONSIDERAÇÕES FINAIS

Este plano está totalmente alinhado com:
- As diretrizes do Codex para o MVP
- A pesquisa sobre formatos do Instagram
- A estrutura atual do projeto
- Os dados disponíveis no JSON final

O componente é extensível e pode ser refinado incrementalmente após o MVP funcionar.