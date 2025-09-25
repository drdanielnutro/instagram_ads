import { Button } from '@/components/ui/button';
import { cn } from '@/utils';

interface NavigationFooterProps {
  currentStep: number;
  totalSteps: number;
  onNext: () => void;
  onBack: () => void;
  onSubmit: () => void;
  onCancel: () => void;
  canProceed: boolean;
  isLoading: boolean;
  isOptional: boolean;
}

export function NavigationFooter({
  currentStep,
  totalSteps,
  onNext,
  onBack,
  onSubmit,
  onCancel,
  canProceed,
  isLoading,
  isOptional,
}: NavigationFooterProps) {
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === totalSteps - 1;

  return (
    <footer className="flex-shrink-0 border-t border-border/60 py-3 px-6 md:px-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          {!isFirstStep && (
            <Button
              type="button"
              variant="ghost"
              className="gap-2 text-muted-foreground hover:text-foreground"
              disabled={isLoading}
              onClick={onBack}
            >
              Voltar
            </Button>
          )}
          <span className="hidden text-xs uppercase tracking-wider text-muted-foreground/80 md:inline">
            Passo {Math.min(currentStep + 1, totalSteps)} de {totalSteps}
          </span>
          {isOptional && (
            <span className="inline-flex items-center rounded-full border border-dashed border-border/60 px-3 py-1 text-xs text-muted-foreground">
              Etapa opcional
            </span>
          )}
        </div>

        <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-end">
          {isLoading && (
            <Button
              type="button"
              variant="ghost"
              onClick={onCancel}
              className="justify-center text-destructive hover:text-destructive/80"
            >
              Cancelar geração
            </Button>
          )}
          <Button
            type="button"
            size="lg"
            className={cn(
              'min-w-[160px] justify-center font-medium transition-colors',
              !canProceed && 'opacity-60',
            )}
            disabled={!canProceed || isLoading}
            onClick={isLastStep ? onSubmit : onNext}
          >
            {isLastStep ? 'Gerar anúncios' : 'Próximo passo'}
          </Button>
        </div>
      </div>
    </footer>
  );
}
