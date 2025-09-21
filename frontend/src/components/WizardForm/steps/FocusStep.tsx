import { AlertCircle, Info } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';

interface FocusStepProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

export function FocusStep({ value, onChange, error }: FocusStepProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-foreground/90">
            Há alguma ênfase ou mensagem obrigatória?
          </label>
          <Badge variant="outline" className="border-dashed border-border/60 text-muted-foreground">
            Opcional
          </Badge>
        </div>
        <Textarea
          value={value}
          onChange={event => onChange(event.target.value)}
          rows={5}
          placeholder="Ex.: destaque para frete grátis, cupom promocional, benefícios ou temas que devem ser evitados."
        />
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Info className="h-4 w-4" />
          Este campo ajuda o assistente a reforçar diferenciais importantes, mas pode ser deixado em branco.
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
