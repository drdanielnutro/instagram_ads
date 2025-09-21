import { AlertCircle, LayoutDashboard } from 'lucide-react';

import { FORMATO_OPTIONS } from '@/constants/wizard.constants';
import { cn } from '@/utils';

interface FormatStepProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

export function FormatStep({ value, onChange, error }: FormatStepProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          Escolha o formato que combina com o criativo disponível e o posicionamento onde deseja anunciar.
        </p>
        <LayoutDashboard className="hidden h-8 w-8 text-primary/80 sm:block" />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {FORMATO_OPTIONS.map(option => {
          const isSelected = value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              className={cn(
                'flex flex-col items-start gap-1 rounded-2xl border px-4 py-4 text-left transition-all',
                'bg-card/80 hover:border-primary/60 hover:bg-primary/5',
                isSelected && 'border-primary bg-primary/10 shadow-md text-primary',
              )}
            >
              <span className="text-sm font-semibold text-foreground/90">
                {option.label}
              </span>
              <span className="text-xs text-muted-foreground">Proporção {option.ratio}</span>
              <span className="text-xs text-muted-foreground/80">{option.description}</span>
            </button>
          );
        })}
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/60 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}
    </div>
  );
}
