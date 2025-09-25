import type { WizardStep } from '@/types/wizard.types';
import { cn } from '@/utils';

interface StepsListProps {
  steps: WizardStep[];
  currentStep: number;
  completedSteps: number[];
  onStepClick?: (index: number) => void;
}

export function StepsList({
  steps,
  currentStep,
  completedSteps,
  onStepClick,
}: StepsListProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
          Passo {Math.min(currentStep + 1, steps.length)} de {steps.length}
        </span>
      </div>

      <ol className="flex-1 flex flex-col justify-between">
        {steps.map((step, index) => {
          const isActive = index === currentStep;
          const isCompleted = completedSteps.includes(index);

          return (
            <li key={step.id}>
              <div
                className={cn(
                  'flex items-center gap-3 rounded-xl border px-3 py-2 transition-colors text-sm',
                  isActive && 'border-primary/60 bg-primary/10 text-primary',
                  !isActive && isCompleted && 'border-primary/20 bg-primary/5 text-primary/70',
                  !isActive && !isCompleted && 'border-border/60 bg-card/60 text-muted-foreground',
                  onStepClick && 'cursor-pointer hover:bg-card',
                )}
                onClick={() => onStepClick?.(index)}
              >
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold',
                      isActive && 'border-primary/40 bg-primary text-primary-foreground',
                      !isActive && isCompleted && 'border-primary/40 bg-primary/90 text-primary-foreground',
                      !isActive && !isCompleted && 'border-border/80 bg-card text-muted-foreground',
                    )}
                  >
                    {index + 1}
                  </div>
                  <step.icon
                    className={cn(
                      'h-4 w-4 transition-colors',
                      isActive ? 'text-primary' : 'text-muted-foreground',
                      isCompleted && !isActive && 'text-primary/70',
                    )}
                    aria-hidden="true"
                  />
                </div>
                <div className="flex flex-col">
                  <span className="font-medium text-foreground/90">{step.title}</span>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}