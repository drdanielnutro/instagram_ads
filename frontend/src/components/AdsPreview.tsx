import { useCallback, useEffect, useMemo, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AdVariation,
  AspectRatio,
  ContextInfo,
  CopyInfo,
  VisualInfo,
  VariationFormat,
} from "@/types/ad-preview";
import { cn } from "@/utils";

interface AdsPreviewProps {
  userId: string;
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

export interface PromptBlockProps {
  label: string;
  text?: string;
}

interface ImageCarouselProps {
  variationIndex: number;
  images: string[];
  prompts: { label: string; text?: string }[];
  aspectRatioClass: string;
  currentIndex: number;
  onIndexChange: (index: number) => void;
  onImageError: (imageIndex: number) => void;
  onRetry: () => void;
  hasError: boolean;
  isLoading: boolean;
}

const VARIATION_TAB_CLASS = "rounded-lg data-[state=active]:bg-card/80 data-[state=active]:text-foreground";
const FALLBACK_FORMAT: VariationFormat = "Feed";
const FALLBACK_ASPECT_RATIO: AspectRatio = "4:5";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function coerceString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function coerceAspectRatio(value: unknown): AspectRatio {
  if (value === "9:16" || value === "1:1" || value === "4:5") {
    return value as AspectRatio;
  }
  return FALLBACK_ASPECT_RATIO;
}

function coerceFormat(value: unknown): VariationFormat {
  if (value === "Reels" || value === "Stories" || value === "Feed") {
    return value as VariationFormat;
  }
  return FALLBACK_FORMAT;
}

function coerceImages(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string" && item.length > 0);
}

function buildCopy(raw: unknown): CopyInfo {
  const copy = isRecord(raw) ? raw : {};
  return {
    headline: coerceString(copy.headline),
    corpo: coerceString(copy.corpo),
    cta_texto: coerceString(copy.cta_texto),
  };
}

function buildVisual(raw: unknown): VisualInfo {
  const visual = isRecord(raw) ? raw : {};
  return {
    descricao_imagem: coerceString(visual.descricao_imagem),
    prompt_estado_atual: coerceString(visual.prompt_estado_atual),
    prompt_estado_intermediario: coerceString(visual.prompt_estado_intermediario),
    prompt_estado_aspiracional: coerceString(visual.prompt_estado_aspiracional),
    aspect_ratio: coerceAspectRatio(visual.aspect_ratio),
    // Futuro: o backend irá popular visual.images com as URLs finais para o carrossel.
    images: coerceImages(visual.images),
  };
}

function buildContext(raw: unknown): ContextInfo {
  if (typeof raw === "string" || Array.isArray(raw) || isRecord(raw)) {
    return raw as ContextInfo;
  }
  return "";
}

function sanitizeVariation(raw: unknown): AdVariation | null {
  if (!isRecord(raw)) {
    return null;
  }

  const copy = buildCopy(raw.copy);
  const visual = buildVisual(raw.visual);

  return {
    landing_page_url: coerceString(raw.landing_page_url),
    formato: coerceFormat(raw.formato),
    copy,
    visual,
    cta_instagram: coerceString(raw.cta_instagram),
    fluxo: coerceString(raw.fluxo),
    referencia_padroes: coerceString(raw.referencia_padroes),
    contexto_landing: buildContext(raw.contexto_landing),
  };
}

export function PromptBlock({ label, text }: PromptBlockProps) {
  if (!text) {
    return null;
  }

  return (
    <div className="space-y-1 rounded-xl border border-border/50 bg-background/40 px-4 py-3">
      <span className="text-xs uppercase tracking-wide text-muted-foreground/80">{label}</span>
      <p className="text-sm text-muted-foreground whitespace-pre-line">{text}</p>
    </div>
  );
}

function ImageCarousel({
  variationIndex,
  images,
  prompts,
  aspectRatioClass,
  currentIndex,
  onIndexChange,
  onImageError,
  onRetry,
  hasError,
  isLoading,
}: ImageCarouselProps) {
  const hasImages = images.length > 0;
  const totalSlides = Math.max(prompts.length, hasImages ? images.length : 1);
  const stageLabel = prompts[currentIndex]?.label ?? "Descrição visual";
  const activePrompt = prompts[currentIndex];
  const imageSrc = images[currentIndex];

  const canGoPrev = currentIndex > 0;
  const canGoNext = currentIndex < totalSlides - 1;

  const handlePrev = () => {
    if (canGoPrev) {
      onIndexChange(currentIndex - 1);
    }
  };

  const handleNext = () => {
    if (canGoNext) {
      onIndexChange(currentIndex + 1);
    }
  };

  return (
    <div className="space-y-4">
      <div
        className={cn(
          "relative w-full overflow-hidden rounded-[28px] border border-border/60 bg-gradient-to-br from-background/70 to-background/40 shadow-inner",
          aspectRatioClass,
        )}
      >
        <div className="absolute left-4 top-4 z-10 rounded-full border border-border/60 bg-background/80 px-3 py-1 text-xs font-medium text-foreground/80">
          {stageLabel}
        </div>
        <button
          type="button"
          onClick={handlePrev}
          disabled={!canGoPrev}
          aria-label="Visual anterior"
          className="absolute left-3 top-1/2 z-10 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border border-border/60 bg-background/80 text-sm text-foreground transition disabled:opacity-30"
        >
          ←
        </button>
        <button
          type="button"
          onClick={handleNext}
          disabled={!canGoNext}
          aria-label="Próximo visual"
          className="absolute right-3 top-1/2 z-10 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border border-border/60 bg-background/80 text-sm text-foreground transition disabled:opacity-30"
        >
          →
        </button>
        {isLoading ? (
          <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground/80">
            Carregando preview…
          </div>
        ) : hasError ? (
          <div className="flex h-full w-full flex-col items-center justify-center gap-3 bg-background/90 px-6 text-center">
            <p className="text-sm text-muted-foreground">
              Não foi possível carregar as imagens desta variação.
            </p>
            <Button variant="outline" size="sm" onClick={onRetry}>
              Tentar novamente
            </Button>
          </div>
        ) : hasImages && imageSrc ? (
          <img
            key={`${variationIndex}-${currentIndex}`}
            src={imageSrc}
            alt={`Variação ${variationIndex + 1} - imagem ${currentIndex + 1}`}
            className="h-full w-full object-cover"
            onError={() => onImageError(currentIndex)}
          />
        ) : (
          <div className="flex h-full flex-col justify-end gap-4 p-6 text-left">
            <Badge variant="outline" className="w-fit bg-background/70 text-xs">
              {activePrompt?.label ?? "Descrição visual"}
            </Badge>
            <p className="text-sm text-muted-foreground/90 whitespace-pre-line">
              {activePrompt?.text || "As imagens finais ainda não estão disponíveis. Utilize os prompts como referência visual."}
            </p>
          </div>
        )}
        {!hasImages && (
          <div className="pointer-events-none absolute inset-0 rounded-[28px] border border-border/40" />
        )}
        {totalSlides > 1 && (
          <div className="absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 gap-2">
            {Array.from({ length: totalSlides }).map((_, index) => (
              <button
                key={`${variationIndex}-dot-${index}`}
                type="button"
                onClick={() => onIndexChange(index)}
                aria-label={`Ir para ${prompts[index]?.label ?? `etapa ${index + 1}`}`}
                className={cn(
                  "h-2 w-2 rounded-full border border-border/60 transition",
                  index === currentIndex ? "bg-primary" : "bg-primary/30",
                )}
              />
            ))}
          </div>
        )}
      </div>
      {(hasImages || prompts.length > 1) && (
        <div className="flex items-center justify-center gap-2">
          {prompts.map((prompt, index) => (
            <button
              key={`${variationIndex}-${index}`}
              type="button"
              onClick={() => onIndexChange(index)}
              className={cn(
                "flex min-w-[90px] items-center justify-center rounded-full border border-border/60 px-3 py-1 text-xs transition-colors",
                index === currentIndex
                  ? "bg-primary text-primary-foreground"
                  : "bg-background/60 text-muted-foreground hover:bg-background/80",
              )}
            >
              {prompt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function normalizeVariations(payload: unknown): AdVariation[] {
  if (!payload) {
    return [];
  }

  const normalizedPayload = typeof payload === "string" ? safeJsonParse(payload) : payload;
  let variationSource: unknown[] | null = null;

  if (Array.isArray(normalizedPayload)) {
    variationSource = normalizedPayload;
  } else if (isRecord(normalizedPayload)) {
    const maybeVariations = normalizedPayload.variations ?? normalizedPayload.variacoes ?? normalizedPayload.ads;
    if (Array.isArray(maybeVariations)) {
      variationSource = maybeVariations;
    } else {
      variationSource = [normalizedPayload];
    }
  }

  if (!Array.isArray(variationSource)) {
    return [];
  }

  return variationSource
    .map((item) => sanitizeVariation(item))
    .filter((item): item is AdVariation => Boolean(item));
}

function safeJsonParse(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch (error) {
    console.error("Falha ao parsear JSON do preview", error);
    return null;
  }
}

function getAspectRatioClass(ratio?: string): string {
  switch (ratio) {
    case "9:16":
      return "aspect-[9/16]";
    case "1:1":
      return "aspect-square";
    case "4:5":
    default:
      return "aspect-[4/5]";
  }
}

function isVerticalFormat(formato?: string): boolean {
  if (!formato) {
    return false;
  }

  return formato === "Reels" || formato === "Stories";
}

function getVariationImages(variation?: AdVariation): string[] {
  if (!variation) {
    return [];
  }

  return variation.visual.images;
}

function getContextEntries(contexto: ContextInfo): { label: string; value: string }[] {
  if (!contexto) {
    return [];
  }

  if (typeof contexto === "string") {
    return [{ label: "Contexto", value: contexto }];
  }

  if (Array.isArray(contexto)) {
    return contexto.map((value, index) => ({
      label: `Item ${index + 1}`,
      value: typeof value === "string" ? value : JSON.stringify(value, null, 2),
    }));
  }

  if (typeof contexto === "object") {
    return Object.entries(contexto as Record<string, unknown>).map(([key, value]) => ({
      label: key.replace(/_/g, " "),
      value: typeof value === "string" ? value : JSON.stringify(value, null, 2),
    }));
  }

  return [];
}

export function AdsPreview({ userId, sessionId, isOpen, onClose }: AdsPreviewProps) {
  const [variations, setVariations] = useState<AdVariation[]>([]);
  const [currentVariation, setCurrentVariation] = useState(0);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [isFetchingPreview, setIsFetchingPreview] = useState(false);
  const [imageErrors, setImageErrors] = useState<Map<string, boolean>>(new Map());
  const [fetchError, setFetchError] = useState<string | null>(null);

  const resetState = useCallback(() => {
    setVariations([]);
    setCurrentVariation(0);
    setCurrentImageIndex(0);
    setImageErrors(new Map());
    setFetchError(null);
  }, []);

  const fetchPreviewData = useCallback(async () => {
    if (!userId || !sessionId) {
      return;
    }

    setIsFetchingPreview(true);
    setFetchError(null);
    setImageErrors(new Map());

    const params = new URLSearchParams({
      user_id: userId,
      session_id: sessionId,
      inline: "1",
    });
    const baseUrl = `/api/delivery/final/download?${params.toString()}`;

    try {
      const response = await fetch(baseUrl);
      if (!response.ok) {
        throw new Error(`Falha ao buscar preview: ${response.status}`);
      }

      const contentType = response.headers.get("content-type") ?? "";
      let payload: unknown;

      if (contentType.includes("application/json")) {
        payload = await response.json();
      } else {
        payload = safeJsonParse(await response.text());
      }

      const parsedVariations = normalizeVariations(payload);
      setVariations(parsedVariations);
      setCurrentVariation(0);
      setCurrentImageIndex(0);
    } catch (error) {
      console.error("Erro ao buscar dados do preview", error);
      setFetchError("Não foi possível carregar o preview. Tente novamente.");
    } finally {
      setIsFetchingPreview(false);
    }
  }, [sessionId, userId]);

  const handleImageError = useCallback((variationIndex: number, imageIndex: number) => {
    setImageErrors((prev) => {
      const next = new Map(prev);
      next.set(`${variationIndex}-${imageIndex}`, true);
      return next;
    });
  }, []);

  const activeVariation = useMemo(() => variations[currentVariation], [variations, currentVariation]);

  const prompts = useMemo(() => {
    if (!activeVariation?.visual) {
      return [];
    }

    return [
      { label: "Estado atual", text: activeVariation.visual.prompt_estado_atual },
      { label: "Intermediário", text: activeVariation.visual.prompt_estado_intermediario },
      { label: "Aspiracional", text: activeVariation.visual.prompt_estado_aspiracional },
    ].filter((prompt) => prompt.text && prompt.text.length > 0);
  }, [activeVariation]);

  const variationImages = useMemo(() => getVariationImages(activeVariation), [activeVariation]);
  const aspectRatioClass = getAspectRatioClass(activeVariation?.visual.aspect_ratio);
  const hasImageError = imageErrors.get(`${currentVariation}-${currentImageIndex}`) ?? false;

  useEffect(() => {
    if (isOpen) {
      resetState();
      fetchPreviewData();
    } else {
      resetState();
    }
  }, [fetchPreviewData, isOpen, resetState]);

  useEffect(() => {
    setCurrentImageIndex(0);
  }, [currentVariation]);

  const renderFeedDevice = () => (
    <div className="flex h-full flex-col gap-6 p-6">
      <div>
        <p className="text-sm font-medium text-muted-foreground/80">Dispositivo (Feed)</p>
      </div>
      <ImageCarousel
        variationIndex={currentVariation}
        images={variationImages}
        prompts={prompts.length ? prompts : [{ label: "Descrição", text: activeVariation.visual.descricao_imagem }]}
        aspectRatioClass={aspectRatioClass}
        currentIndex={currentImageIndex}
        onIndexChange={setCurrentImageIndex}
        onImageError={(index) => handleImageError(currentVariation, index)}
        onRetry={fetchPreviewData}
        hasError={hasImageError}
        isLoading={isFetchingPreview}
      />
      <Card className="rounded-2xl border border-border/60 bg-card/80 shadow-sm">
        <CardContent className="space-y-4 py-6">
          <div className="space-y-2">
            <h3 className="text-base font-semibold text-foreground/90">
              {activeVariation.copy.headline || "Headline não informada"}
            </h3>
            <p className="text-sm text-muted-foreground whitespace-pre-line">
              {activeVariation.copy.corpo || "O corpo do anúncio será exibido aqui quando disponível."}
            </p>
          </div>
          <Button size="lg" className="w-full md:w-auto">
            {activeVariation.copy.cta_texto || activeVariation.cta_instagram || "Definir CTA"}
          </Button>
          {variationImages.length === 0 && (
            <p className="text-xs text-muted-foreground/80">
              Enquanto as imagens não chegam pelo backend, utilize os prompts abaixo como referência visual.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );

  const renderVerticalDevice = () => (
    <div className="flex h-full flex-col gap-6 p-6">
      <div>
        <p className="text-sm font-medium text-muted-foreground/80">Dispositivo (Vertical)</p>
      </div>
      <div className="relative">
        <ImageCarousel
          variationIndex={currentVariation}
          images={variationImages}
          prompts={prompts.length ? prompts : [{ label: "Descrição", text: activeVariation.visual.descricao_imagem }]}
          aspectRatioClass={aspectRatioClass}
          currentIndex={currentImageIndex}
          onIndexChange={setCurrentImageIndex}
          onImageError={(index) => handleImageError(currentVariation, index)}
          onRetry={fetchPreviewData}
          hasError={hasImageError}
          isLoading={isFetchingPreview}
        />
        <div className="pointer-events-none absolute inset-0">
          <div className="flex justify-center">
            <div className="mt-8 rounded-full border border-border/60 bg-background/40 px-4 py-2 text-xs font-medium text-muted-foreground/80">
              Safe zone — texto principal
            </div>
          </div>
          <div className="absolute bottom-8 left-1/2 w-[calc(100%-4rem)] -translate-x-1/2 rounded-full border border-border/60 bg-background/45 px-4 py-2 text-center text-xs font-medium text-muted-foreground/80">
            Safe zone — CTA / logo
          </div>
        </div>
      </div>
      <Card className="rounded-2xl border border-border/50 bg-muted/30">
        <CardContent className="space-y-2 py-4 text-sm text-muted-foreground">
          <p>
            💡 Em formatos verticais, a interface do Instagram sobrepõe elementos do criativo. Use o preview para garantir que textos fiquem dentro das áreas seguras.
          </p>
          {variationImages.length === 0 && (
            <p>
              Enquanto não houver imagens renderizadas, utilize os prompts e descrições abaixo para guiar a produção manual.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );

  const renderDevice = () => {
    if (!activeVariation) {
      return (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground/80">
          Nenhum dado disponível.
        </div>
      );
    }

    if (isVerticalFormat(activeVariation.formato)) {
      return renderVerticalDevice();
    }

    return renderFeedDevice();
  };

  const renderTextContent = () => {
    if (!activeVariation) {
      return (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground/80">
          Aguarde o carregamento do preview.
        </div>
      );
    }

    const contextEntries = getContextEntries(activeVariation.contexto_landing);

    return (
      <div className="space-y-6 pr-2">
        <Card className="border-border/60 bg-card/70">
          <CardHeader className="space-y-1">
            <Badge variant="secondary" className="w-fit bg-muted/40 text-xs">
              Copy principal
            </Badge>
            <CardTitle className="text-lg text-foreground/90">
              {activeVariation.copy.headline || "Headline não informada"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground whitespace-pre-line">
              {activeVariation.copy.corpo || "O corpo do anúncio será exibido aqui quando disponível."}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-muted-foreground/80">CTA</span>
              <Badge className="bg-primary/10 text-primary">
                {activeVariation.copy.cta_texto || activeVariation.cta_instagram || "Definir CTA"}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/70">
          <CardHeader>
            <CardTitle className="text-base text-foreground/90">Metadados</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 text-sm text-muted-foreground md:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground/70">Formato</p>
              <p className="mt-1 text-foreground/80">{activeVariation.formato || "—"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground/70">CTA Instagram</p>
              <p className="mt-1 text-foreground/80">{activeVariation.cta_instagram || "—"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground/70">Fluxo</p>
              <p className="mt-1 text-foreground/80">{activeVariation.fluxo || "—"}</p>
            </div>
            <div className="md:col-span-2">
              <p className="text-xs uppercase tracking-wide text-muted-foreground/70">Landing Page</p>
              {activeVariation.landing_page_url ? (
                <a
                  href={activeVariation.landing_page_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-block break-words text-primary underline"
                >
                  Abrir página
                </a>
              ) : (
                <p className="mt-1 text-foreground/70">Sem URL cadastrada</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/70">
          <CardHeader>
            <CardTitle className="text-base text-foreground/90">Prompts e descrição visual</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <section>
              <h4 className="text-xs uppercase tracking-wide text-muted-foreground/80">Descrição visual</h4>
              <p className="mt-1 text-sm text-muted-foreground whitespace-pre-line">
                {activeVariation.visual.descricao_imagem || "Os prompts detalhados serão exibidos quando fornecidos pelo backend."}
              </p>
            </section>
            <section className="space-y-3">
              {prompts.length > 0 ? (
                prompts.map((prompt) => (
                  <PromptBlock key={prompt.label} label={prompt.label} text={prompt.text} />
                ))
              ) : (
                <p className="text-sm text-muted-foreground/80">
                  Os prompts detalhados serão exibidos quando fornecidos pelo backend.
                </p>
              )}
            </section>
          </CardContent>
        </Card>

        {activeVariation.referencia_padroes && (
          <details className="group rounded-2xl border border-border/60 bg-card/70 px-6 py-4">
            <summary className="flex cursor-pointer items-center justify-between text-sm font-medium text-foreground/90 list-none">
              Referências e padrões
              <span className="transition-transform group-open:rotate-180">⌃</span>
            </summary>
            <div className="pt-4 text-sm text-muted-foreground whitespace-pre-line">
              {activeVariation.referencia_padroes}
            </div>
          </details>
        )}

        {contextEntries.length > 0 && (
          <details className="group rounded-2xl border border-border/60 bg-card/70 px-6 py-4">
            <summary className="flex cursor-pointer items-center justify-between text-sm font-medium text-foreground/90 list-none">
              StoryBrand & Contexto
              <span className="transition-transform group-open:rotate-180">⌃</span>
            </summary>
            <div className="space-y-4 pt-4 text-sm text-muted-foreground">
              {contextEntries.map((entry) => (
                <div key={entry.label} className="space-y-1 rounded-xl border border-border/40 bg-background/50 px-4 py-3">
                  <span className="text-xs uppercase tracking-wide text-muted-foreground/80">
                    {entry.label}
                  </span>
                  <p className="whitespace-pre-line text-muted-foreground/90">{entry.value}</p>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    );
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay asChild>
          <div className="fixed inset-0 bg-background/80 backdrop-blur-sm" />
        </Dialog.Overlay>
        <Dialog.Content
          className="fixed inset-0 z-50 h-full w-full overflow-hidden rounded-none border border-border/70 bg-card text-foreground shadow-[0_45px_80px_-50px_rgba(6,12,24,0.65)] md:inset-auto md:top-1/2 md:left-1/2 md:h-[90vh] md:w-full md:max-h-[calc(100vh-4rem)] md:max-w-[1100px] md:-translate-x-1/2 md:-translate-y-1/2 md:rounded-3xl"
        >
          <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
            <div>
              <h2 className="text-lg font-semibold text-foreground/90">Preview das Variações</h2>
              {fetchError && (
                <p className="mt-1 text-sm text-red-400">{fetchError}</p>
              )}
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Fechar">
                ✕
              </Button>
            </Dialog.Close>
          </div>

          {variations.length > 1 && (
            <div className="border-b border-border/60 px-6 py-4">
              <Tabs
                value={String(currentVariation)}
                onValueChange={(value: string) => {
                  const index = Number(value);
                  setCurrentVariation(index);
                  setCurrentImageIndex(0);
                }}
                className="w-full"
              >
                <TabsList className="grid grid-cols-3 gap-2 bg-muted/30 p-1">
                  {variations.map((_, index) => (
                    <TabsTrigger
                      key={index}
                      value={String(index)}
                      className={VARIATION_TAB_CLASS}
                    >
                      Var. {index + 1}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
            </div>
          )}

          <div className="flex h-full flex-col gap-6 overflow-hidden px-6 py-6 lg:flex-row">
            <ScrollArea className="h-[45vh] rounded-2xl border border-border/60 bg-background/60 md:h-[50vh] lg:h-full lg:w-1/2">
              <div className="h-full w-full">
                {renderDevice()}
              </div>
            </ScrollArea>

            <ScrollArea className="h-[45vh] md:h-[50vh] lg:h-full lg:flex-1">
              {renderTextContent()}
            </ScrollArea>
          </div>

          <div className="flex justify-end gap-3 border-t border-border/60 bg-card/80 px-6 py-4">
            <Button variant="outline" onClick={fetchPreviewData} disabled={isFetchingPreview}>
              {isFetchingPreview ? "Recarregando…" : "Recarregar dados"}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
