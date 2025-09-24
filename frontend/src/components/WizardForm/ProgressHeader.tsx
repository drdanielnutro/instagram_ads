import type { WizardStep } from '@/types/wizard.types';
import { cn } from '@/utils';

interface ProgressHeaderProps {
  steps: WizardStep[];
  currentStep: number;
  completedSteps: number[];
  orientation?: 'horizontal' | 'vertical';
  onStepClick?: (index: number) => void;
}

export function ProgressHeader({
  steps,
  currentStep,
  completedSteps,
  orientation = 'horizontal',
  onStepClick,
}: ProgressHeaderProps) {
  const totalSteps = steps.length;
  const progressValue = Math.max(0, Math.min(currentStep, totalSteps - 1));
  const progressPercentage = ((progressValue + 1) / totalSteps) * 100;

  const isVertical = orientation === 'vertical';

  return (
    <header className={cn('space-y-6', isVertical && 'pr-4')}> {/* pr para separar da borda da sidebar */}
      <div className="flex flex-col gap-2">
        <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
          Passo {Math.min(currentStep + 1, totalSteps)} de {totalSteps}
        </span>
      </div>

      {/* Barra de progresso permanece visível nas duas orientações */}
      <div className="h-2 w-full overflow-hidden rounded-full bg-border/70">
        <div
          className="h-full rounded-full bg-primary transition-all duration-300"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      <ol className={cn(isVertical ? 'flex flex-col gap-2' : 'flex flex-wrap items-center gap-4')}>
        {steps.map((step, index) => {
          const isActive = index === currentStep;
          const isCompleted = completedSteps.includes(index);

          const item = (
            <div
              className={cn(
                'flex items-center gap-3 rounded-xl border px-3 py-2 transition-colors text-sm',
                isActive && 'border-primary/60 bg-primary/10 text-primary',
                !isActive && 'border-border/60 bg-card/60 text-muted-foreground',
                isCompleted && !isActive && 'border-primary/50 bg-primary/10 text-primary',
                onStepClick && 'cursor-pointer hover:bg-card'
              )}
              onClick={() => onStepClick?.(index)}
            >
              <div className="flex items-center gap-2">
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
                <step.icon
                  className={cn(
                    'h-4 w-4 text-muted-foreground transition-colors',
                    (isActive || isCompleted) && 'text-primary',
                  )}
                />
              </div>
              <div className="flex flex-col">
                <span className="font-medium text-foreground/90">{step.title}</span>
              </div>
            </div>
          );

          return (
            <li key={step.id}>
              {item}
            </li>
          );
        })}
      </ol>
    </header>
  );
}
