import type { WizardStep } from '@/types/wizard.types';
import { cn } from '@/utils';

interface StepCardProps {
  step: WizardStep;
  children: React.ReactNode;
}

export function StepCard({ step, children }: StepCardProps) {
  return (
    <section
      className={cn(
        'bg-card border border-border/60 rounded-2xl shadow-lg relative',
        'p-8 flex flex-col gap-6 w-full',
      )}
    >
      <header className="flex items-start gap-4">
        <div className="rounded-xl bg-primary/15 text-primary p-3">
          <step.icon className="h-6 w-6" />
        </div>
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-foreground">{step.title}</h2>
          {step.subtitle && (
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
              {step.subtitle}
            </span>
          )}
          <p className="text-sm text-muted-foreground">{step.description}</p>
        </div>
      </header>
      <div>{children}</div>
    </section>
  );
}
