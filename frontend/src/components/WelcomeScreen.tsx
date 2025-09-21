import { ArrowRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { InputForm } from "@/components/InputForm";
import { WizardForm } from "@/components/WizardForm";

interface WelcomeScreenProps {
  handleSubmit: (query: string) => void;
  isLoading: boolean;
  onCancel: () => void;
}

export function WelcomeScreen({
  handleSubmit,
  isLoading,
  onCancel,
}: WelcomeScreenProps) {
  const wizardEnabled = (import.meta.env.VITE_ENABLE_WIZARD ?? "false")
    .toString()
    .toLowerCase() === "true";

  if (wizardEnabled) {
    return (
    <div
      className="w-full flex justify-center px-6 md:px-12 xl:px-20"
      data-wizard-enabled
    >
        <WizardForm onSubmit={handleSubmit} isLoading={isLoading} onCancel={onCancel} />
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4 py-12 lg:px-8"
      data-wizard-enabled={wizardEnabled}
    >
      <div className="w-full max-w-4xl space-y-8 text-center">
        <div className="flex flex-col items-center gap-3">
          <StatusBadge
            variant="info"
            icon={<Sparkles className="h-4 w-4" />}
          >
            Instagram Ads com Vertex AI
          </StatusBadge>
          <h1 className="text-4xl font-semibold text-foreground/95 tracking-tight md:text-5xl">
            Crie campanhas completas em minutos
          </h1>
          <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
            Informe os elementos principais da campanha e receba automaticamente três variações alinhadas ao formato, persona e objetivo do anúncio.
          </p>
        </div>

        <SectionCard
          className="text-left bg-card/95 border border-border/50 shadow-2xl backdrop-blur-sm"
          title="Briefing do anúncio"
          description="Preencha apenas o que tiver em mãos. O assistente complementa o restante."
          headerAction={
            <Button variant="outline" size="sm" type="button" className="gap-2 hover:border-primary/50 transition-colors">
              <Sparkles className="h-4 w-4" />
              Ver exemplo
            </Button>
          }
          contentClassName="space-y-8 pb-8"
        >
          <InputForm onSubmit={handleSubmit} isLoading={isLoading} context="homepage" />
          {isLoading && (
            <div className="mt-6 flex justify-end">
              <Button
                variant="ghost"
                onClick={onCancel}
                className="text-destructive hover:text-destructive/80 gap-2"
              >
                Cancelar geração
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
