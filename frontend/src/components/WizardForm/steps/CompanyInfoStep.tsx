import { AlertCircle, Building2, Briefcase } from 'lucide-react';

import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

type CompanyField = 'nome_empresa' | 'o_que_a_empresa_faz';

interface CompanyInfoStepProps {
  field: CompanyField;
  value: string;
  error?: string;
  touched: boolean;
  onChange: (value: string) => void;
  onBlur: () => void;
}

const fieldConfig: Record<CompanyField, {
  label: string;
  description: string;
  placeholder: string;
  Icon: typeof Building2;
  hint?: string;
  multiline?: boolean;
}> = {
  nome_empresa: {
    label: 'Nome da empresa ou marca',
    description:
      'Esse nome será usado nos textos do anúncio. Utilize a forma como o público já reconhece a marca.',
    placeholder: 'Ex.: Clínica Bem Viver',
    Icon: Building2,
    multiline: false,
  },
  o_que_a_empresa_faz: {
    label: 'Como você descreve a empresa?',
    description:
      'Resuma o que a empresa faz, principais produtos ou serviços em uma frase objetiva.',
    placeholder: 'Ex.: Clínica de nutrição especializada em emagrecimento saudável',
    Icon: Briefcase,
    hint: 'Dica: mencione diferenciais, público atendido ou resultados que reforcem a autoridade da empresa.',
    multiline: true,
  },
};

export function CompanyInfoStep({
  field,
  value,
  error,
  touched,
  onChange,
  onBlur,
}: CompanyInfoStepProps) {
  const { label, description, placeholder, Icon, hint, multiline } = fieldConfig[field];

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="flex items-center gap-2 text-sm font-medium text-foreground/90">
          <Icon className="h-4 w-4 text-primary/70" />
          {label}
        </label>
        {multiline ? (
          <Textarea
            value={value}
            onChange={event => onChange(event.target.value)}
            onBlur={onBlur}
            rows={4}
            placeholder={placeholder}
            maxLength={200}
          />
        ) : (
          <Input
            value={value}
            onChange={event => onChange(event.target.value)}
            onBlur={onBlur}
            placeholder={placeholder}
            autoComplete="organization"
            maxLength={100}
          />
        )}
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>

      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}

      {touched && error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/60 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}
    </div>
  );
}
