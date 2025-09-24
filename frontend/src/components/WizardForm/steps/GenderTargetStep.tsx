import { AlertCircle, Venus } from 'lucide-react';

import { SEXO_CLIENTE_OPTIONS } from '@/constants/wizard.constants';
import { Button } from '@/components/ui/button';
import { cn } from '@/utils';

interface GenderTargetStepProps {
  value: string;
  error?: string;
  touched: boolean;
  onChange: (value: string) => void;
  onBlur: () => void;
}

export function GenderTargetStep({
  value,
  error,
  touched,
  onChange,
  onBlur,
}: GenderTargetStepProps) {
  const handleSelect = (option: string) => {
    onChange(option);
    onBlur();
  };

  const handleClear = () => {
    onChange('');
    onBlur();
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground/90">
          <Venus className="h-4 w-4 text-primary/70" />
          Há foco em um gênero específico?
        </div>
        <p className="text-sm text-muted-foreground">
          Selecione apenas se a comunicação do anúncio estiver direcionada para um público majoritariamente masculino ou
          feminino. Caso contrário, mantenha como neutro.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {SEXO_CLIENTE_OPTIONS.map(option => {
          const isSelected = value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => handleSelect(option.value)}
              className={cn(
                'flex flex-col items-start gap-1 rounded-2xl border px-4 py-4 text-left transition-all',
                'bg-card/80 hover:border-primary/60 hover:bg-primary/5',
                isSelected && 'border-primary bg-primary/10 shadow-md text-primary',
              )}
            >
              <span className="text-sm font-semibold text-foreground/90">{option.label}</span>
              <span className="text-xs text-muted-foreground">{option.description}</span>
            </button>
          );
        })}
      </div>

      <Button type="button" variant="ghost" size="sm" className="self-start text-xs" onClick={handleClear}>
        Limpar seleção
      </Button>

      {touched && error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/60 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}
    </div>
  );
}
