import { useCallback, useEffect, useMemo, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AdVariation } from "@/types/ad-preview";
import { cn } from "@/utils";

interface AdsPreviewProps {
  userId: string;
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface FetchSignedUrlResponse {
  signed_url?: string;
}

interface PromptBlockProps {
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

function PromptBlock({ label, text }: PromptBlockProps) {
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
  const activePrompt = prompts[currentIndex];

  return (
    <div className="space-y-4">
      <div
        className={cn(
          "relative w-full overflow-hidden rounded-[28px] border border-border/60 bg-gradient-to-br from-background/70 to-background/40 shadow-inner",
          aspectRatioClass,
        )}
      >
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
        ) : hasImages ? (
          <img
            key={`${variationIndex}-${currentIndex}`}
            src={images[currentIndex]}
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

  if (Array.isArray(normalizedPayload)) {
    return normalizedPayload as AdVariation[];
  }

  if (typeof normalizedPayload === "object" && normalizedPayload !== null) {
    const maybeVariations = (normalizedPayload as Record<string, unknown>).variations
      ?? (normalizedPayload as Record<string, unknown>).variacoes
      ?? (normalizedPayload as Record<string, unknown>).ads;

    if (Array.isArray(maybeVariations)) {
      return maybeVariations as AdVariation[];
    }
  }

  return [];
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
  if (!variation?.visual) {
    return [];
  }

  const maybeImages = (variation.visual as Record<string, unknown>).images;
  if (!Array.isArray(maybeImages)) {
    return [];
  }

  return maybeImages.filter((url): url is string => typeof url === "string" && url.length > 0);
}

function getContextEntries(contexto: unknown): { label: string; value: string }[] {
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

    const baseUrl = `/api/delivery/final/download?user_id=${encodeURIComponent(userId)}&session_id=${encodeURIComponent(sessionId)}`;

    try {
      const response = await fetch(baseUrl);
      if (!response.ok) {
        throw new Error(`Falha ao buscar preview: ${response.status}`);
      }

      const contentType = response.headers.get("content-type") ?? "";
      let payload: unknown;

      if (contentType.includes("application/json")) {
        const data = await response.json();
        const maybeSigned = data as FetchSignedUrlResponse;
        if (maybeSigned?.signed_url) {
          const signedResponse = await fetch(maybeSigned.signed_url);
          const signedContentType = signedResponse.headers.get("content-type") ?? "";
          if (signedContentType.includes("application/json")) {
            payload = await signedResponse.json();
          } else {
            payload = safeJsonParse(await signedResponse.text());
          }
        } else {
          payload = data;
        }
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
  const aspectRatioClass = getAspectRatioClass(activeVariation?.visual?.aspect_ratio);
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
    <div className="flex h-full flex-col justify-between gap-6 p-6">
      <div>
        <p className="text-sm font-medium text-muted-foreground/80">Dispositivo (Feed)</p>
      </div>
      <ImageCarousel
        variationIndex={currentVariation}
        images={variationImages}
        prompts={prompts.length ? prompts : [{ label: "Descrição", text: activeVariation?.visual?.descricao_imagem }]}
        aspectRatioClass={aspectRatioClass}
        currentIndex={currentImageIndex}
        onIndexChange={setCurrentImageIndex}
        onImageError={(index) => handleImageError(currentVariation, index)}
        onRetry={fetchPreviewData}
        hasError={hasImageError}
        isLoading={isFetchingPreview}
      />
      <div className="rounded-2xl border border-border/50 bg-background/60 p-4">
        <p className="text-xs uppercase tracking-wide text-muted-foreground/70">Descrição visual</p>
        <p className="mt-2 text-sm text-muted-foreground whitespace-pre-line">
          {activeVariation?.visual?.descricao_imagem || "Os prompts descrevem a sequência sugerida para o criativo."}
        </p>
      </div>
    </div>
  );

  const renderVerticalDevice = () => (
    <div className="flex h-full flex-col gap-6 p-6">
      <div>
        <p className="text-sm font-medium text-muted-foreground/80">Dispositivo (Vertical)</p>
      </div>
      <div className="relative">
        <div className="pointer-events-none absolute inset-x-8 top-10 z-10 h-12 rounded-full border border-primary/40 bg-primary/10 text-center text-xs leading-[3rem] text-primary">
          Safe zone — texto principal
        </div>
        <ImageCarousel
          variationIndex={currentVariation}
          images={variationImages}
          prompts={prompts.length ? prompts : [{ label: "Descrição", text: activeVariation?.visual?.descricao_imagem }]}
          aspectRatioClass={aspectRatioClass}
          currentIndex={currentImageIndex}
          onIndexChange={setCurrentImageIndex}
          onImageError={(index) => handleImageError(currentVariation, index)}
          onRetry={fetchPreviewData}
          hasError={hasImageError}
          isLoading={isFetchingPreview}
        />
        <div className="pointer-events-none absolute inset-x-8 bottom-10 z-10 h-12 rounded-full border border-primary/40 bg-primary/10 text-center text-xs leading-[3rem] text-primary">
          Safe zone — CTA / logo
        </div>
      </div>
      <div className="rounded-2xl border border-border/50 bg-background/60 p-4">
        <p className="text-xs uppercase tracking-wide text-muted-foreground/70">Descrição visual</p>
        <p className="mt-2 text-sm text-muted-foreground whitespace-pre-line">
          {activeVariation?.visual?.descricao_imagem || "Utilize as zonas destacadas para manter textos legíveis em formatos verticais."}
        </p>
      </div>
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
              {activeVariation.copy?.headline || "Headline não informada"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground whitespace-pre-line">
              {activeVariation.copy?.corpo || "O corpo do anúncio será exibido aqui quando disponível."}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-muted-foreground/80">CTA</span>
              <Badge className="bg-primary/10 text-primary">
                {activeVariation.copy?.cta_texto || activeVariation.cta_instagram || "Definir CTA"}
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
              <p className="text-xs uppercase tracking-wide text-muted-foreground/70">Fluxo</p>
              <p className="mt-1 text-foreground/80">{activeVariation.fluxo || "—"}</p>
            </div>
            <div className="md:col-span-2">
              <p className="text-xs uppercase tracking-wide text-muted-foreground/70">Landing Page</p>
              <p className="mt-1 break-words text-primary/90">
                {activeVariation.landing_page_url || "Sem URL cadastrada"}
              </p>
            </div>
            <div className="md:col-span-2">
              <p className="text-xs uppercase tracking-wide text-muted-foreground/70">Referências</p>
              <p className="mt-1 whitespace-pre-line text-muted-foreground/90">
                {activeVariation.referencia_padroes || "Referências visuais serão exibidas aqui."}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/70">
          <CardHeader>
            <CardTitle className="text-base text-foreground/90">Prompts visuais</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {prompts.length > 0 ? (
              prompts.map((prompt) => (
                <PromptBlock key={prompt.label} label={prompt.label} text={prompt.text} />
              ))
            ) : (
              <p className="text-sm text-muted-foreground/80">
                Os prompts detalhados serão exibidos quando fornecidos pelo backend.
              </p>
            )}
          </CardContent>
        </Card>

        {contextEntries.length > 0 && (
          <Card className="border-border/60 bg-card/70">
            <CardHeader>
              <CardTitle className="text-base text-foreground/90">StoryBrand & Contexto</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              {contextEntries.map((entry) => (
                <div key={entry.label} className="space-y-1 rounded-xl border border-border/40 bg-background/50 px-4 py-3">
                  <span className="text-xs uppercase tracking-wide text-muted-foreground/80">
                    {entry.label}
                  </span>
                  <p className="whitespace-pre-line text-muted-foreground/90">{entry.value}</p>
                </div>
              ))}
            </CardContent>
          </Card>
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
