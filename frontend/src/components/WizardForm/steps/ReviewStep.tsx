import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { WIZARD_STEPS } from '@/constants/wizard.constants';
import type { WizardFormState, WizardStepId } from '@/types/wizard.types';
import type { UseReferenceImagesReturn } from '@/state/useReferenceImages';

interface ReviewStepProps {
  formState: WizardFormState;
  referenceImages: UseReferenceImagesReturn;
  onEdit: (field: WizardStepId) => void;
}

export function ReviewStep({ formState, referenceImages, onEdit }: ReviewStepProps) {
  const fields = WIZARD_STEPS.filter(step => step.id !== 'review');

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Revise as informações antes de gerar os anúncios. Você pode editar qualquer etapa clicando em “Editar”.
      </p>

      <div className="space-y-3">
        {fields.map(step => {
          const isUploadStep = step.kind === 'upload';
          let displayValue = '';
          let isEmpty = false;

          if (isUploadStep) {
            const entry =
              step.id === 'reference_image_character'
                ? referenceImages.character
                : referenceImages.product;

            const lines: string[] = [];
            if (entry.id) {
              lines.push(entry.fileName ? `Arquivo: ${entry.fileName}` : 'Arquivo enviado.');
            }
            if (entry.userDescription.trim()) {
              lines.push(`Descrição: ${entry.userDescription.trim()}`);
            }
            if (entry.labels.length > 0) {
              lines.push(`Labels detectados: ${entry.labels.join(', ')}`);
            }
            if (entry.error) {
              lines.push(`Erro: ${entry.error}`);
            }

            if (lines.length === 0) {
              lines.push('Nenhuma referência enviada.');
              isEmpty = true;
            } else {
              isEmpty = false;
            }

            displayValue = lines.join('\n');
          } else {
            const fieldId = step.id as keyof WizardFormState;
            const value = formState[fieldId].trim();
            isEmpty = value.length === 0;
            displayValue = isEmpty ? 'Não preenchido' : value;
          }

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
                  onClick={() => onEdit(step.id)}
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
