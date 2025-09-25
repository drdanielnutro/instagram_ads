import type { WizardStep } from '@/types/wizard.types';
import { cn } from '@/utils';

interface StepCardProps {
  step: WizardStep;
  children: React.ReactNode;
  currentStep?: number;
  totalSteps?: number;
}

export function StepCard({ step, children, currentStep, totalSteps }: StepCardProps) {
  const showProgress = currentStep !== undefined && totalSteps !== undefined;
  const progressPercentage = showProgress
    ? ((currentStep + 1) / totalSteps) * 100
    : 0;

  return (
    <section
      className={cn(
        'bg-card border border-border/60 rounded-2xl shadow-lg relative',
        'p-6 flex flex-col gap-5 w-full max-w-4xl mx-auto',
      )}
    >
      {showProgress && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-border/30 rounded-t-2xl overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      )}

      <header className="flex items-start gap-3">
        <div className="rounded-lg bg-primary/15 text-primary p-2.5">
          <step.icon className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-foreground">{step.title}</h2>
              <span className="text-xs uppercase tracking-wide text-muted-foreground">
                Passo {currentStep !== undefined ? currentStep + 1 : ''}{step.subtitle ? ` - ${step.subtitle}` : ''}
              </span>
              <p className="text-sm text-muted-foreground">{step.description}</p>
            </div>
            {showProgress && (
              <div className="text-right">
                <span className="text-xs text-muted-foreground">
                  {currentStep + 1} de {totalSteps}
                </span>
              </div>
            )}
          </div>
        </div>
      </header>
      <div>{children}</div>
    </section>
  );
}
