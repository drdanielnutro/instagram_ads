import type { WizardStep } from '@/types/wizard.types';
import { cn } from '@/utils';

interface ProgressHeaderProps {
  steps: WizardStep[];
  currentStep: number;
  completedSteps: number[];
}

export function ProgressHeader({
  steps,
  currentStep,
  completedSteps,
}: ProgressHeaderProps) {
  const totalSteps = steps.length;
  const progressValue = Math.max(0, Math.min(currentStep, totalSteps - 1));
  const progressPercentage = ((progressValue + 1) / totalSteps) * 100;

  return (
    <header className="space-y-6">
      <div className="flex flex-col gap-2">
        <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
          Passo {Math.min(currentStep + 1, totalSteps)} de {totalSteps}
        </span>
        <h1 className="text-2xl font-semibold text-foreground">
          Monte seu briefing guiado
        </h1>
        <p className="text-sm text-muted-foreground">
          Avance pelas etapas para garantir que todos os dados essenciais sejam preenchidos
          antes de gerar as recomendações de anúncios.
        </p>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-border/70">
        <div
          className="h-full rounded-full bg-primary transition-all duration-300"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      <ol className="flex flex-wrap items-center gap-4">
        {steps.map((step, index) => {
          const isActive = index === currentStep;
          const isCompleted = completedSteps.includes(index);

          return (
            <li
              key={step.id}
              className={cn(
                'flex items-center gap-3 rounded-xl border px-3 py-2 transition-colors text-sm',
                isActive && 'border-primary/60 bg-primary/10 text-primary',
                !isActive && 'border-border/60 bg-card/60 text-muted-foreground',
                isCompleted && !isActive && 'border-primary/50 bg-primary/10 text-primary',
              )}
            >
              <div
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold',
                  isActive && 'border-primary/40 bg-primary text-primary-foreground',
                  isCompleted && !isActive && 'border-primary/40 bg-primary/90 text-primary-foreground',
                  !isActive && !isCompleted && 'border-border/80 bg-card text-muted-foreground',
                )}
              >
                {index + 1}
              </div>
              <div className="flex flex-col">
                <span className="font-medium text-foreground/90">{step.title}</span>
                {step.subtitle && (
                  <span className="text-xs text-muted-foreground">{step.subtitle}</span>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </header>
  );
}
