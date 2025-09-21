import { AlertCircle, Sparkles } from 'lucide-react';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface LandingPageStepProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

const examples = [
  'https://minhaempresa.com/consultas',
  'https://lojaonline.com/ofertas',
  'https://agenciaxyz.com/contato',
];

export function LandingPageStep({ value, onChange, error }: LandingPageStepProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground/90">
          URL da página de destino
          <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
            <Sparkles className="h-3 w-3" />
            Otimize conversões
          </span>
        </div>
        <Input
          type="url"
          value={value}
          onChange={event => onChange(event.target.value)}
          placeholder="https://exemplo.com/pagina"
          autoComplete="url"
        />
        <p className="text-sm text-muted-foreground">
          Dica: utilize uma URL específica da campanha para acompanhar métricas com maior precisão.
        </p>
      </div>

      <div className="space-y-2">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">
          Exemplos rápidos
        </span>
        <div className="flex flex-wrap gap-2">
          {examples.map(example => (
            <Button
              key={example}
              type="button"
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => onChange(example)}
            >
              {example}
            </Button>
          ))}
        </div>
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
