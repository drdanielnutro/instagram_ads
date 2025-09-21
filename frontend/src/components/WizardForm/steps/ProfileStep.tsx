import { AlertCircle } from 'lucide-react';

import { Textarea } from '@/components/ui/textarea';

interface ProfileStepProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

const MAX_CHARACTERS = 500;
const WARNING_THRESHOLD = Math.floor(MAX_CHARACTERS * 0.9);

export function ProfileStep({ value, onChange, error }: ProfileStepProps) {
  const charactersUsed = value.length;
  const isNearLimit = charactersUsed >= WARNING_THRESHOLD;

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground/90">
          Quem é o cliente ideal?
        </label>
        <Textarea
          value={value}
          onChange={event => onChange(event.target.value)}
          rows={6}
          placeholder="Descreva persona, desafios, preferências, tom de voz e diferenciais que importam para a campanha."
        />
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Inclua detalhes sobre dores, desejos e gatilhos de decisão.
          </span>
          <span className={isNearLimit ? 'text-amber-500' : undefined}>
            {charactersUsed}/{MAX_CHARACTERS}
          </span>
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
