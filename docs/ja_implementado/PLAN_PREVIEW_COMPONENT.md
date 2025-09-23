# PLANO ATUALIZADO: Componente de Preview de Anúncios

## 1. ATIVAÇÃO DO PREVIEW

### Flag de controle
- Adicionar `VITE_ENABLE_ADS_PREVIEW=false` em `frontend/.env.example` (replicar em `.env.local` quando necessário)
- Documentar a flag em `frontend/README.md` na seção de Feature Flags
- Criar helper `isPreviewEnabled` em `frontend/src/utils/featureFlags.ts` com base em `readBooleanFlag`

### Condição de exibição:
```typescript
// Em App.tsx, mostrar botão quando:
if (deliveryMeta?.ok && isPreviewEnabled()) {
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

// Imports necessários além do React:
// - Button, Badge, Card, CardContent, CardHeader, CardTitle, ScrollArea, Tabs, TabsList, TabsTrigger
//   a partir de `@/components/ui/...`
// - isPreviewEnabled (novo helper) em `@/utils/featureFlags`
```

## 4. LAYOUT DO MODAL

### Estrutura base (usando Radix Dialog + tema atual):
```tsx
<Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
  <Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 bg-background/80 backdrop-blur-sm" />
    <Dialog.Content
      className="fixed inset-0 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2
                 w-full h-full md:h-[90vh] md:max-h-[calc(100vh-4rem)]
                 max-w-[1100px] rounded-3xl border border-border/70 bg-card text-foreground
                 shadow-[0_45px_80px_-50px_rgba(6,12,24,0.65)] overflow-hidden"
    >
      <div className="flex items-center justify-between px-6 py-4 border-b border-border/60">
        <h2 className="text-lg font-semibold text-foreground/90">Preview das Variações</h2>
        <Dialog.Close asChild>
          <Button variant="ghost" size="icon" aria-label="Fechar">✕</Button>
        </Dialog.Close>
      </div>

      {/* Navegação dinâmica de variações */}
      {variations.length > 1 && (
        <div className="px-6 py-4 border-b border-border/60">
          <Tabs value={String(currentVariation)} onValueChange={(value) => {
            const index = Number(value);
            setCurrentVariation(index);
            setCurrentImageIndex(0);
          }} className="w-full">
            <TabsList className="grid grid-cols-3 gap-2 bg-muted/30 rounded-xl p-1">
              {variations.map((_, index) => (
                <TabsTrigger key={index} value={String(index)} className="rounded-lg">
                  Var. {index + 1}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6 px-6 py-6 overflow-hidden h-full">
        <ScrollArea className="lg:w-1/2 h-[45vh] md:h-[50vh] lg:h-full rounded-2xl border border-border/60 bg-background/60">
          {renderDevice()}
        </ScrollArea>

        <ScrollArea className="lg:flex-1 h-[45vh] md:h-[50vh] lg:h-full">
          {renderTextContent()}
        </ScrollArea>
      </div>

      <div className="px-6 py-4 border-t border-border/60 bg-card/80 flex justify-end gap-3">
        <Button variant="outline" onClick={fetchPreviewData} disabled={isFetchingPreview}>
          Recarregar dados
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
  const images = getVariationImages(variation);

  return (
    <div className="p-6">
      <div className="mx-auto max-w-sm rounded-3xl border-8 border-border/80 bg-background/80 overflow-hidden">
        <ImageCarousel
          images={images}
          aspectRatio={variation.visual.aspect_ratio}
          currentIndex={currentImageIndex}
          onIndexChange={setCurrentImageIndex}
          currentVariation={currentVariation}
          onError={handleImageError}
        />
      </div>

      <Card className="mt-6 bg-card/70 border-border/60">
        <CardContent className="space-y-4 py-6">
          <h3 className="text-base font-semibold text-foreground/90">{variation.copy.headline}</h3>
          <p className="text-sm text-muted-foreground whitespace-pre-line">{variation.copy.corpo}</p>
          <Button size="lg" className="w-full md:w-auto">{variation.copy.cta_texto}</Button>
        </CardContent>
      </Card>
    </div>
  );
}
```

> ℹ️ Enquanto o backend não disponibilizar URLs de imagens no JSON final, `getVariationImages` retornará um array vazio e o carrossel exibirá o placeholder temático com os prompts e instruções.

### Reels/Stories (9:16):
```tsx
function renderVerticalDevice() {
  const variation = variations[currentVariation];
  const images = getVariationImages(variation);

  return (
    <div className="p-6">
      <div className="mx-auto max-w-xs rounded-[2.75rem] border-8 border-border/80 bg-background/80 overflow-hidden relative">
        <ImageCarousel
          images={images}
          aspectRatio={variation.visual.aspect_ratio}
          currentIndex={currentImageIndex}
          onIndexChange={setCurrentImageIndex}
          currentVariation={currentVariation}
          onError={handleImageError}
        />

        {/* Safe zones */}
        <div className="pointer-events-none absolute inset-0">
          <div className="h-[14%] bg-background/35" />
          <div className="absolute bottom-0 w-full h-[25%] bg-background/40" />
        </div>
      </div>

      <Card className="mt-6 bg-muted/30 border-border/50">
        <CardContent className="py-4">
          <p className="text-xs text-muted-foreground/80">
            💡 Em formatos verticais, os textos aparecem sobrepostos no dispositivo real. Utilize o preview para conferir prompts e áreas seguras.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

## 6. COMPONENTE CARROSSEL

```tsx
interface ImageCarouselProps {
  images?: string[];
  aspectRatio: string;
  currentIndex: number;
  onIndexChange: (index: number) => void;
  currentVariation: number;
  onError: (variation: number, imageIndex: number) => void;
}

function ImageCarousel({ images, aspectRatio, currentIndex, onIndexChange, currentVariation, onError }: ImageCarouselProps) {
  const hasImages = images && images.length > 0;

  return (
    <div className={`relative ${getAspectRatioClass(aspectRatio)}`}>
      {hasImages ? (
        <img
          src={images[currentIndex]}
          onError={() => onError(currentVariation, currentIndex)}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full bg-muted/40 flex flex-col items-center justify-center gap-3 text-center px-6">
          <Badge variant="outline" className="border-dashed border-border/60">Imagem não disponível</Badge>
          <p className="text-sm text-muted-foreground">
            Utilize a descrição e os prompts abaixo para gerar o visual manualmente.
          </p>
        </div>
      )}

      {/* Navegação com botões desabilitados nos limites */}
      <button
        onClick={() => onIndexChange(currentIndex - 1)}
        disabled={!hasImages || currentIndex === 0}
        className="absolute left-3 top-1/2 -translate-y-1/2 bg-background/70 text-foreground p-2 rounded-full border border-border/60 disabled:opacity-30"
      >←</button>
      <button
        onClick={() => onIndexChange(currentIndex + 1)}
        disabled={!hasImages || currentIndex === (images?.length ?? 1) - 1}
        className="absolute right-3 top-1/2 -translate-y-1/2 bg-background/70 text-foreground p-2 rounded-full border border-border/60 disabled:opacity-30"
      >→</button>

      {/* Dots */}
      {hasImages && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
          {images.map((_, i) => (
            <button
              key={i}
              onClick={() => onIndexChange(i)}
              className={`h-2 w-2 rounded-full ${i === currentIndex ? 'bg-primary' : 'bg-primary/40'}`}
            />
          ))}
        </div>
      )}

      {/* Labels das etapas */}
      <div className="absolute top-4 left-4 bg-background/70 text-foreground px-2 py-1 rounded-full text-xs border border-border/60">
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
      <Card className="bg-card/80 border-border/60">
        <CardHeader>
          <CardTitle className="text-sm tracking-wide text-muted-foreground uppercase">Copy do anúncio</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <section>
            <h4 className="text-xs text-muted-foreground uppercase">Headline</h4>
            <p className="text-sm font-medium text-foreground/90">{v.copy.headline}</p>
          </section>
          <section>
            <h4 className="text-xs text-muted-foreground uppercase">Corpo</h4>
            <p className="text-sm text-muted-foreground whitespace-pre-line">{v.copy.corpo}</p>
          </section>
          <section className="flex items-center gap-2">
            <h4 className="text-xs text-muted-foreground uppercase">CTA</h4>
            <Badge variant="outline" className="border-primary/40 text-primary">{v.copy.cta_texto}</Badge>
          </section>
        </CardContent>
      </Card>

      <Card className="bg-card/80 border-border/60">
        <CardHeader>
          <CardTitle className="text-sm tracking-wide text-muted-foreground uppercase">Prompts e descrição visual</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <section>
            <h4 className="text-xs uppercase text-muted-foreground/80">Descrição</h4>
            <p className="whitespace-pre-line text-foreground/80">{v.visual.descricao_imagem}</p>
          </section>
          <section className="space-y-2">
            <PromptBlock label="Estado atual" text={v.visual.prompt_estado_atual} />
            <PromptBlock label="Estado intermediário" text={v.visual.prompt_estado_intermediario} />
            <PromptBlock label="Estado aspiracional" text={v.visual.prompt_estado_aspiracional} />
          </section>
        </CardContent>
      </Card>

      <Card className="bg-card/80 border-border/60">
        <CardHeader>
          <CardTitle className="text-sm tracking-wide text-muted-foreground uppercase">Metadados</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="space-y-3 text-sm text-muted-foreground">
            <div className="flex items-center justify-between">
              <dt>Formato</dt>
              <dd className="text-foreground/90 font-medium">{v.formato}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>CTA Instagram</dt>
              <dd className="text-foreground/80">{v.cta_instagram}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>Fluxo</dt>
              <dd className="text-foreground/80">{v.fluxo}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>Landing</dt>
              <dd>
                <a href={v.landing_page_url} target="_blank" rel="noreferrer" className="text-primary underline">
                  Abrir página
                </a>
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <div className="space-y-3">
        <details className="group rounded-2xl border border-border/60 bg-card/70 px-6 py-4">
          <summary className="cursor-pointer text-sm font-medium text-foreground/90 list-none flex items-center justify-between">
            Referências e padrões
            <span className="transition-transform group-open:rotate-180">⌃</span>
          </summary>
          <div className="pt-4 text-sm text-muted-foreground whitespace-pre-line">
            {v.referencia_padroes}
          </div>
        </details>

        <details className="group rounded-2xl border border-border/60 bg-card/70 px-6 py-4">
          <summary className="cursor-pointer text-sm font-medium text-foreground/90 list-none flex items-center justify-between">
            Contexto StoryBrand
            <span className="transition-transform group-open:rotate-180">⌃</span>
          </summary>
          <div className="pt-4 text-sm text-muted-foreground whitespace-pre-line">
            {v.contexto_landing}
          </div>
        </details>
      </div>
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

    const dataArray = Array.isArray(jsonData) ? jsonData : [jsonData];
    setVariations(dataArray);
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
  <div className="flex items-center justify-center h-full bg-muted/30">
    <div className="text-center space-y-2">
      <p className="text-sm text-muted-foreground">Não foi possível carregar esta etapa</p>
      <Button onClick={() => fetchPreviewData()} size="sm" variant="outline">
        Tentar novamente
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
{deliveryMeta?.ok && isPreviewEnabled() && (
  <div className="ml-auto flex gap-2">
    <Button onClick={handleDownloadFinal} variant="outline">Baixar JSON</Button>
    <Button onClick={() => setShowPreview(true)} className="bg-primary text-primary-foreground">
      Preview
    </Button>
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

> Nota: importe `isPreviewEnabled` de `@/utils/featureFlags` e mantenha o preview protegido pela flag para permitir rollback imediato caso surjam regressões.

## 12. TIPOS TYPESCRIPT

```typescript
// frontend/src/types/ad-preview.ts
interface VisualInfo {
  descricao_imagem: string;
  prompt_estado_atual: string;
  prompt_estado_intermediario: string;
  prompt_estado_aspiracional: string;
  aspect_ratio: "4:5" | "9:16" | "1:1";
}

interface AdVariation {
  landing_page_url: string;
  formato: "Feed" | "Reels" | "Stories";
  copy: {
    headline: string;
    corpo: string;
    cta_texto: string;
  };
  visual: VisualInfo;
  cta_instagram: string;
  fluxo: string;
  referencia_padroes: string;
  contexto_landing: string;
}
```

## 13. HELPERS

```typescript
// frontend/src/utils/featureFlags.ts
export function isPreviewEnabled(defaultValue = false): boolean {
  return readBooleanFlag("VITE_ENABLE_ADS_PREVIEW", defaultValue);
}
```

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

// Extrair possíveis URLs de imagens (quando existirem)
function getVariationImages(variation: AdVariation): string[] {
  const images: string[] = [];
  const maybeImages = (variation as any).visual?.images ?? [];
  if (Array.isArray(maybeImages)) {
    maybeImages.forEach((url: string) => {
      if (url) images.push(url);
    });
  }
  return images;
}

// Quando o backend passar a incluir URLs explícitas, armazená-las em `visual.images` (string[])
// para alimentar o carrossel. Enquanto isso, o preview usa os prompts como fallback.

function PromptBlock({ label, text }: { label: string; text: string }) {
  return (
    <div className="space-y-1 rounded-xl border border-border/50 bg-background/40 px-4 py-3">
      <span className="text-xs uppercase tracking-wide text-muted-foreground/80">{label}</span>
      <p className="text-sm text-muted-foreground whitespace-pre-line">{text}</p>
    </div>
  );
}

```

## 14. ESTILOS E TEMAS

- Reutilizar tokens existentes: `bg-card`, `bg-background`, `border-border`, `text-muted-foreground`, `text-primary`.
- Utilizar variações com opacidade (`bg-card/70`, `bg-muted/30`) para separar blocos mantendo contraste adequado.
- Aplicar `shadow-[0_45px_80px_-50px_rgba(6,12,24,0.65)]` ou `shadow-xl` conforme padrão do wizard.
- Transições suaves (`transition-all`, `animate-in`) e `backdrop-blur-sm` no overlay para consistência com o restante da UI escura.
- Bordas arredondadas grandes (`rounded-3xl`, `rounded-2xl`) seguindo o visual do wizard.

## 15. CONSIDERAÇÕES FINAIS

Este plano está totalmente alinhado com:
- As diretrizes do Codex para o MVP
- A pesquisa sobre formatos do Instagram
- A estrutura atual do projeto
- Os dados disponíveis no JSON final

O componente é extensível e pode ser refinado incrementalmente após o MVP funcionar.
