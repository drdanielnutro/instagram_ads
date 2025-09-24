import { AlertCircle, Building2, Briefcase } from 'lucide-react';

import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

interface CompanyInfoStepProps {
  variant: 'name' | 'description';
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

const contentByVariant = {
  name: {
    label: 'Nome da empresa ou marca',
    description:
      'Esse nome será usado nos textos do anúncio. Utilize a forma como o público já reconhece a marca.',
    placeholder: 'Ex.: Clínica Bem Viver',
    Icon: Building2,
  },
  description: {
    label: 'Como você descreve a empresa?',
    description:
      'Resuma o que a empresa faz, principais produtos ou serviços em uma frase objetiva.',
    placeholder: 'Ex.: Clínica de nutrição especializada em emagrecimento saudável',
    Icon: Briefcase,
  },
} as const;

export function CompanyInfoStep({ variant, value, onChange, error }: CompanyInfoStepProps) {
  const { label, description, placeholder, Icon } = contentByVariant[variant];

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="flex items-center gap-2 text-sm font-medium text-foreground/90">
          <Icon className="h-4 w-4 text-primary/70" />
          {label}
        </label>
        {variant === 'name' ? (
          <Input
            value={value}
            onChange={event => onChange(event.target.value)}
            placeholder={placeholder}
            autoComplete="organization"
            maxLength={100}
          />
        ) : (
          <Textarea
            value={value}
            onChange={event => onChange(event.target.value)}
            rows={4}
            placeholder={placeholder}
            maxLength={200}
          />
        )}
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>

      {variant === 'description' && (
        <p className="text-xs text-muted-foreground">
          Dica: mencione diferenciais, público atendido ou resultados que reforcem a autoridade da empresa.
        </p>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/60 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}
    </div>
  );
}
