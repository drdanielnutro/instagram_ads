import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { WIZARD_STEPS } from '@/constants/wizard.constants';
import type { WizardFormState } from '@/types/wizard.types';

interface ReviewStepProps {
  formState: WizardFormState;
  onEdit: (field: keyof WizardFormState) => void;
}

export function ReviewStep({ formState, onEdit }: ReviewStepProps) {
  const fields = WIZARD_STEPS.filter(step => step.id !== 'review');

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Revise as informações antes de gerar os anúncios. Você pode editar qualquer etapa clicando em “Editar”.
      </p>

      <div className="space-y-3">
        {fields.map(step => {
          const fieldId = step.id as keyof WizardFormState;
          const value = formState[fieldId].trim();
          const isEmpty = value.length === 0;
          const displayValue = isEmpty
            ? step.id === 'sexo_cliente_alvo'
              ? 'Neutro (padrão)'
              : 'Não preenchido'
            : value;

          return (
            <div
              key={step.id}
              className="flex flex-col gap-2 rounded-xl border border-border/60 bg-card/60 p-4 sm:flex-row sm:items-start sm:justify-between"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-foreground/90">{step.title}</h3>
                  {step.isOptional && (
                    <Badge variant="outline" className="border-dashed border-border/60 text-xs text-muted-foreground">
                      Opcional
                    </Badge>
                  )}
                </div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">{step.subtitle}</p>
                <p className="text-sm text-muted-foreground/80">{step.description}</p>
              </div>

              <div className="flex flex-col items-start gap-3 sm:w-1/2">
                <div className="rounded-lg bg-background/80 px-3 py-2 text-sm text-foreground/90">
                  {isEmpty ? (
                    <span className="italic text-muted-foreground">{displayValue}</span>
                  ) : (
                    <span className="whitespace-pre-wrap break-words">{displayValue}</span>
                  )}
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => onEdit(fieldId)}
                  className="self-end"
                >
                  Editar
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
