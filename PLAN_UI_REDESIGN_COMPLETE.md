# Plano Completo de Redesign da UI - Instagram Ads Generator

## Sumário Executivo

Este documento detalha um plano abrangente para elevar a interface do Instagram Ads Generator a um padrão profissional de excelência, seguindo princípios fundamentais de design UI/UX, acessibilidade e experiência do usuário.

### Objetivos Principais
1. **Estabelecer hierarquia visual clara** através de contraste e espaçamento adequados
2. **Criar identidade visual distintiva** com paleta de cores bem definida
3. **Implementar microinterações** que guiem e encantem o usuário
4. **Garantir acessibilidade** seguindo padrões WCAG 2.1 AA
5. **Otimizar a experiência** com feedback visual imediato e transições suaves

---

## 1. Análise dos Problemas Identificados

### 1.1 Problema de Contraste e Hierarquia Visual

#### Situação Atual
As capturas de tela revelam que o SectionCard principal e os cards internos (passos do formulário) apresentam cores muito similares ao background, criando uma experiência visual "flat" sem profundidade ou hierarquia clara.

#### Código Problemático
```tsx
// frontend/src/components/WelcomeScreen.tsx
<SectionCard
  className="text-left bg-card/95 border border-border/50 shadow-2xl backdrop-blur-sm"
  // ...
>
```

```css
/* frontend/src/global.css */
--background: #0a0d14;
--card: rgba(23, 29, 45, 0.95);
--surface: rgba(18, 24, 38, 0.88);
```

#### Análise Técnica
- **Diferença de luminosidade insuficiente**: Background (#0a0d14) vs Card (rgba(23, 29, 45)) = ~8% de diferença
- **Ratio de contraste**: 1.3:1 (abaixo do mínimo WCAG de 3:1 para elementos UI)
- **Opacidade excessiva**: Cards com 95% opacidade reduzem ainda mais o contraste

---

### 1.2 Problema de Espaçamento e Centralização

#### Situação Atual
O conteúdo não está adequadamente centralizado verticalmente, com excesso de espaço no topo e falta de respiro visual no rodapé.

#### Código Problemático
```tsx
// frontend/src/components/WelcomeScreen.tsx
<div className="min-h-screen flex flex-col items-center justify-center px-4 py-12 lg:px-8">
  <div className="w-full max-w-4xl space-y-8 text-center">
```

#### Análise Técnica
- **Centralização falha**: `justify-center` não funciona adequadamente com conteúdo muito alto
- **Padding assimétrico**: `py-12` é insuficiente para criar equilíbrio visual
- **Container muito largo**: `max-w-4xl` (56rem) é excessivo para formulários

---

### 1.3 Problema dos Cards Internos (Passos do Formulário)

#### Situação Atual
Os cards dos passos 1-5 se confundem com o SectionCard principal, criando confusão visual.

#### Código Problemático
```tsx
// frontend/src/components/InputForm.tsx
<div className="rounded-xl border border-border/60 bg-gradient-to-br from-card/80 to-card/60 px-6 py-5 shadow-lg backdrop-blur-sm transition-all hover:border-primary/30 hover:shadow-xl">
```

#### Análise Técnica
- **Gradiente ineficaz**: `from-card/80 to-card/60` não cria contraste suficiente
- **Bordas muito sutis**: `border-border/60` com border color em rgba(255, 255, 255, 0.12)
- **Sombras perdidas**: Em background escuro, sombras não são efetivas

---

### 1.4 Problema da Área de Ação (Botão Submit)

#### Situação Atual
O botão "Iniciar geração" e sua seção container não têm destaque suficiente.

#### Código Problemático
```tsx
// frontend/src/components/InputForm.tsx
<div className="mt-8 flex flex-col gap-4 rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10 px-6 py-5 md:flex-row md:items-center md:justify-between shadow-sm">
```

#### Análise Técnica
- **Opacidade excessiva**: `border-primary/20` e `from-primary/5` são sutis demais
- **Falta de contraste**: Background com 5-10% de opacidade é quase invisível

---

## 2. Soluções Propostas - Design System Completo

### 2.1 Nova Paleta de Cores e Sistema de Contraste

#### Princípios de Design
1. **Contraste Progressivo**: 3 níveis distintos de elevação
2. **Cores Semânticas**: Cada cor tem propósito específico
3. **Acessibilidade WCAG AA**: Todos os contrastes atendem padrões mínimos

#### Nova Implementação
```css
/* frontend/src/global.css */
:root {
  /* Base Colors - High Contrast System */
  --background: #050508;           /* Pure dark background */
  --background-elevated: #0f1114;  /* Slightly elevated */
  --foreground: #fafbff;           /* High contrast text */
  --foreground-muted: #b8c0d4;     /* Secondary text */

  /* Card System - Clear Hierarchy */
  --card: #1a1e28;                 /* Primary card - solid color */
  --card-elevated: #232833;        /* Elevated card */
  --card-hover: #2a2f3d;           /* Hover state */
  --card-foreground: #f8faff;      /* Card text */

  /* Interactive Elements */
  --primary: #7c5cff;               /* Primary actions */
  --primary-hover: #8e70ff;        /* Hover state */
  --primary-muted: #7c5cff20;      /* Subtle primary */
  --primary-foreground: #ffffff;    /* Text on primary */

  /* Surface & Borders */
  --surface: #12151c;              /* Input backgrounds */
  --surface-elevated: #1a1e28;     /* Elevated inputs */
  --border: rgba(255, 255, 255, 0.15);     /* Default border */
  --border-strong: rgba(255, 255, 255, 0.25); /* Strong border */
  --border-primary: rgba(124, 92, 255, 0.4);  /* Primary border */

  /* Semantic Colors */
  --success: #4ade80;
  --warning: #fbbf24;
  --error: #ef4444;
  --info: #3b82f6;

  /* Shadows for depth */
  --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.4);
  --shadow-md: 0 8px 16px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 16px 48px rgba(0, 0, 0, 0.6);
  --shadow-xl: 0 24px 64px rgba(0, 0, 0, 0.7);
  --shadow-glow: 0 0 24px rgba(124, 92, 255, 0.2);
}

.dark {
  /* Dark mode adjustments */
  --background: #000000;
  --background-elevated: #0a0c10;
  --card: #16191f;
  --card-elevated: #1f232b;
  --card-hover: #262b35;
  /* ... rest of dark mode */
}
```

---

### 2.2 Redesign do SectionCard Principal

#### Princípios de Design
1. **Destaque máximo**: Card principal deve ser o elemento mais proeminente
2. **Glassmorphism sutil**: Usar blur e transparência com moderação
3. **Bordas luminosas**: Criar sensação de "glow" sutil

#### Nova Implementação
```tsx
// frontend/src/components/WelcomeScreen.tsx
<SectionCard
  className={`
    text-left
    bg-card
    border border-border-strong
    shadow-xl
    relative
    overflow-hidden
    before:absolute
    before:inset-0
    before:bg-gradient-to-br
    before:from-primary/10
    before:via-transparent
    before:to-transparent
    before:pointer-events-none
    after:absolute
    after:inset-0
    after:bg-gradient-radial
    after:from-transparent
    after:via-transparent
    after:to-primary/5
    after:pointer-events-none
    hover:shadow-glow
    hover:border-border-primary
    transition-all
    duration-300
  `}
  title="Briefing do anúncio"
  description="Preencha apenas o que tiver em mãos. O assistente complementa o restante."
  headerAction={
    <Button
      variant="outline"
      size="sm"
      type="button"
      className={`
        gap-2
        border-primary/30
        hover:border-primary/60
        hover:bg-primary/10
        transition-all
        duration-200
        group
      `}
    >
      <Sparkles className="h-4 w-4 group-hover:rotate-12 transition-transform" />
      Ver exemplo
    </Button>
  }
  contentClassName="space-y-6 pb-8"
>
```

#### CSS Adicional para SectionCard
```css
/* Adicionar ao global.css */
@layer utilities {
  .bg-gradient-radial {
    background: radial-gradient(
      ellipse at center,
      var(--tw-gradient-from),
      var(--tw-gradient-via),
      var(--tw-gradient-to)
    );
  }

  .shadow-glow {
    box-shadow:
      var(--shadow-xl),
      0 0 48px rgba(124, 92, 255, 0.15);
  }
}
```

---

### 2.3 Redesign dos Cards Internos (Passos)

#### Princípios de Design
1. **Hierarquia clara**: Cards internos devem ser visivelmente subordinados
2. **Estados interativos**: Hover, focus e active bem definidos
3. **Numeração destacada**: Números dos passos como elementos de design

#### Nova Implementação
```tsx
// frontend/src/components/InputForm.tsx

// Template para cada card de passo
<div className={`
  relative
  rounded-lg
  border
  border-border/80
  bg-surface-elevated
  px-6
  py-5
  shadow-md
  transition-all
  duration-200
  hover:bg-card-hover
  hover:border-border-strong
  hover:shadow-lg
  hover:translate-y-[-2px]
  focus-within:border-primary/40
  focus-within:shadow-glow
  group
`}>
  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-4">
    <span className={`
      flex
      h-10
      w-10
      items-center
      justify-center
      rounded-full
      bg-gradient-to-br
      from-primary
      to-primary/70
      text-sm
      font-bold
      text-white
      shadow-md
      ring-2
      ring-primary/20
      ring-offset-2
      ring-offset-background
      group-hover:ring-primary/40
      group-hover:scale-110
      transition-all
      duration-200
    `}>
      {stepNumber}
    </span>
    <div className="flex-1 space-y-2">
      <h3 className="text-base font-semibold text-foreground">
        {stepTitle}
      </h3>
      <p className="text-sm text-foreground-muted leading-relaxed">
        {stepDescription}
      </p>
    </div>
  </div>
  <div className="mt-4 space-y-3">
    {/* Input fields com novo design */}
    <div className="relative">
      <Input
        className={`
          bg-background
          border-border/60
          hover:border-border-strong
          focus:border-primary/60
          focus:bg-background-elevated
          focus:shadow-sm
          transition-all
          duration-200
          pl-11
          h-11
        `}
        placeholder={placeholder}
      />
      <Icon className={`
        pointer-events-none
        absolute
        left-3
        top-1/2
        h-4
        w-4
        -translate-y-1/2
        text-foreground-muted
        transition-colors
        peer-focus:text-primary
      `} />
    </div>
  </div>
</div>
```

---

### 2.4 Redesign da Área de Ação (Footer do Formulário)

#### Princípios de Design
1. **Call-to-action proeminente**: Botão deve ser impossível de ignorar
2. **Contexto visual**: Área deve parecer "especial"
3. **Microinterações**: Animações que guiam a atenção

#### Nova Implementação
```tsx
// frontend/src/components/InputForm.tsx

<div className={`
  mt-10
  relative
  rounded-xl
  border
  border-primary/30
  bg-gradient-to-r
  from-primary/10
  via-primary/5
  to-transparent
  px-6
  py-6
  shadow-lg
  backdrop-blur-sm
  before:absolute
  before:inset-0
  before:bg-gradient-to-r
  before:from-primary/20
  before:to-transparent
  before:blur-xl
  before:-z-10
  md:flex
  md:items-center
  md:justify-between
  md:gap-6
`}>
  <div className="flex-1 space-y-1 mb-4 md:mb-0">
    <p className="text-sm font-semibold text-foreground">
      Pronto para começar?
    </p>
    <p className="text-sm text-foreground-muted">
      Campos em branco serão preenchidos com as melhores práticas do formato.
    </p>
  </div>

  <Button
    type="submit"
    size="lg"
    disabled={isLoading}
    className={`
      relative
      min-w-[200px]
      bg-primary
      hover:bg-primary-hover
      text-primary-foreground
      font-semibold
      shadow-lg
      hover:shadow-xl
      hover:scale-105
      active:scale-100
      disabled:opacity-50
      disabled:cursor-not-allowed
      disabled:hover:scale-100
      transition-all
      duration-200
      group
      overflow-hidden
      before:absolute
      before:inset-0
      before:bg-gradient-to-r
      before:from-transparent
      before:via-white/20
      before:to-transparent
      before:translate-x-[-200%]
      hover:before:translate-x-[200%]
      before:transition-transform
      before:duration-700
    `}
  >
    {isLoading ? (
      <>
        <Loader2 className="h-4 w-4 animate-spin mr-2" />
        <span className="animate-pulse">Gerando anúncios...</span>
      </>
    ) : (
      <>
        <span>Iniciar geração</span>
        <ArrowRight className={`
          ml-2
          h-4
          w-4
          transition-all
          duration-200
          group-hover:translate-x-1
          group-hover:scale-110
        `} />
      </>
    )}
  </Button>
</div>
```

---

### 2.5 Layout Geral e Centralização

#### Princípios de Design
1. **Golden ratio**: Usar proporções harmônicas
2. **Responsive design**: Adaptação elegante em todas telas
3. **Breathing room**: Espaço adequado em todas direções

#### Nova Implementação
```tsx
// frontend/src/components/WelcomeScreen.tsx

export function WelcomeScreen({
  handleSubmit,
  isLoading,
  onCancel,
}: WelcomeScreenProps) {
  return (
    <div className={`
      min-h-screen
      flex
      flex-col
      bg-gradient-to-b
      from-background
      via-background
      to-background-elevated
      relative
      overflow-hidden
    `}>
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className={`
          absolute
          -top-1/2
          -right-1/2
          w-full
          h-full
          bg-gradient-radial
          from-primary/5
          to-transparent
          blur-3xl
        `} />
        <div className={`
          absolute
          -bottom-1/2
          -left-1/2
          w-full
          h-full
          bg-gradient-radial
          from-primary/5
          to-transparent
          blur-3xl
        `} />
      </div>

      {/* Main content */}
      <div className={`
        flex-1
        flex
        items-center
        justify-center
        px-4
        py-16
        sm:px-6
        lg:px-8
        relative
        z-10
      `}>
        <div className={`
          w-full
          max-w-3xl
          space-y-8
        `}>
          {/* Header section */}
          <div className="text-center space-y-4 animate-fadeInUp">
            <StatusBadge
              variant="info"
              icon={<Sparkles className="h-4 w-4" />}
              className={`
                inline-flex
                shadow-md
                backdrop-blur-sm
                border-primary/30
                bg-primary/10
              `}
            >
              Instagram Ads com Vertex AI
            </StatusBadge>

            <h1 className={`
              text-4xl
              md:text-5xl
              lg:text-6xl
              font-bold
              tracking-tight
              bg-gradient-to-r
              from-foreground
              via-foreground
              to-foreground-muted
              bg-clip-text
              text-transparent
              animate-gradient
            `}>
              Crie campanhas completas
              <span className="block text-primary mt-2">
                em minutos
              </span>
            </h1>

            <p className={`
              max-w-2xl
              mx-auto
              text-base
              md:text-lg
              leading-relaxed
              text-foreground-muted
              animate-fadeIn
              animation-delay-200
            `}>
              Informe os elementos principais da campanha e receba
              automaticamente três variações alinhadas ao formato,
              persona e objetivo do anúncio.
            </p>
          </div>

          {/* Form section */}
          <div className="animate-fadeInUp animation-delay-400">
            <SectionCard
              {/* ... configurações do SectionCard ... */}
            >
              <InputForm
                onSubmit={handleSubmit}
                isLoading={isLoading}
                context="homepage"
              />
            </SectionCard>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## 3. Microinterações e Animações

### 3.1 Sistema de Animações

#### Implementação
```css
/* Adicionar ao global.css */

@layer utilities {
  /* Keyframes */
  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes gradient {
    0%, 100% {
      background-position: 0% 50%;
    }
    50% {
      background-position: 100% 50%;
    }
  }

  @keyframes pulse-glow {
    0%, 100% {
      box-shadow:
        0 0 20px rgba(124, 92, 255, 0.2),
        0 0 40px rgba(124, 92, 255, 0.1);
    }
    50% {
      box-shadow:
        0 0 30px rgba(124, 92, 255, 0.3),
        0 0 60px rgba(124, 92, 255, 0.15);
    }
  }

  /* Animation classes */
  .animate-fadeIn {
    animation: fadeIn 0.5s ease-out forwards;
  }

  .animate-fadeInUp {
    animation: fadeInUp 0.6s ease-out forwards;
  }

  .animate-gradient {
    background-size: 200% 200%;
    animation: gradient 3s ease infinite;
  }

  .animate-pulse-glow {
    animation: pulse-glow 2s ease-in-out infinite;
  }

  /* Delays */
  .animation-delay-100 { animation-delay: 0.1s; }
  .animation-delay-200 { animation-delay: 0.2s; }
  .animation-delay-300 { animation-delay: 0.3s; }
  .animation-delay-400 { animation-delay: 0.4s; }
  .animation-delay-500 { animation-delay: 0.5s; }

  /* Smooth scroll */
  @media (prefers-reduced-motion: no-preference) {
    html {
      scroll-behavior: smooth;
    }
  }
}
```

---

## 4. Componentes Auxiliares

### 4.1 StatusBadge Aprimorado

```tsx
// frontend/src/components/ui/status-badge.tsx

import { cn } from "@/utils";
import { ReactNode } from "react";

interface StatusBadgeProps {
  children: ReactNode;
  variant?: "info" | "success" | "warning" | "error";
  icon?: ReactNode;
  className?: string;
}

export function StatusBadge({
  children,
  variant = "info",
  icon,
  className
}: StatusBadgeProps) {
  const variants = {
    info: "bg-blue-500/10 text-blue-400 border-blue-500/30",
    success: "bg-green-500/10 text-green-400 border-green-500/30",
    warning: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
    error: "bg-red-500/10 text-red-400 border-red-500/30",
  };

  return (
    <div className={cn(
      "inline-flex items-center gap-2 px-3 py-1.5",
      "rounded-full border backdrop-blur-sm",
      "text-xs font-semibold tracking-wide uppercase",
      "transition-all duration-200",
      "hover:scale-105",
      variants[variant],
      className
    )}>
      {icon && (
        <span className="animate-pulse">
          {icon}
        </span>
      )}
      {children}
    </div>
  );
}
```

### 4.2 SectionCard Aprimorado

```tsx
// frontend/src/components/ui/section-card.tsx

import { cn } from "@/utils";
import { ReactNode } from "react";

interface SectionCardProps {
  title: string;
  description?: string;
  children: ReactNode;
  headerAction?: ReactNode;
  className?: string;
  contentClassName?: string;
}

export function SectionCard({
  title,
  description,
  children,
  headerAction,
  className,
  contentClassName,
}: SectionCardProps) {
  return (
    <div className={cn(
      "relative rounded-2xl overflow-hidden",
      "bg-card border border-border-strong",
      "shadow-xl",
      "transition-all duration-300",
      className
    )}>
      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />

      {/* Header */}
      <div className="relative px-8 py-6 border-b border-border/50">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-xl font-bold text-foreground">
              {title}
            </h2>
            {description && (
              <p className="text-sm text-foreground-muted">
                {description}
              </p>
            )}
          </div>
          {headerAction && (
            <div className="flex-shrink-0">
              {headerAction}
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className={cn(
        "relative px-8 py-6",
        contentClassName
      )}>
        {children}
      </div>
    </div>
  );
}
```

---

## 5. Responsividade e Acessibilidade

### 5.1 Breakpoints e Grid System

```tsx
// Utility classes para responsividade
const responsiveClasses = {
  container: "px-4 sm:px-6 lg:px-8",
  maxWidth: "max-w-sm sm:max-w-md md:max-w-lg lg:max-w-xl xl:max-w-2xl",
  grid: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6",
  stack: "space-y-4 sm:space-y-6 lg:space-y-8",
  text: "text-sm sm:text-base lg:text-lg",
  heading: "text-2xl sm:text-3xl md:text-4xl lg:text-5xl",
};
```

### 5.2 Acessibilidade (WCAG 2.1 AA)

```tsx
// Componente com acessibilidade completa
<Button
  type="submit"
  disabled={isLoading}
  aria-label="Iniciar geração de anúncios"
  aria-busy={isLoading}
  aria-disabled={isLoading}
  className={buttonClasses}
>
  {/* ... */}
</Button>

// Inputs com labels adequados
<label htmlFor="landing-page-url" className="sr-only">
  URL da Landing Page
</label>
<Input
  id="landing-page-url"
  aria-describedby="landing-page-help"
  aria-required="false"
  // ...
/>
<span id="landing-page-help" className="sr-only">
  Informe a URL da página que será usada como referência
</span>
```

---

## 6. Performance e Otimizações

### 6.1 CSS Optimization

```css
/* Usar CSS variables para reduzir repetição */
@layer base {
  :root {
    --transition-base: all 0.2s ease-out;
    --transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    --transition-bounce: all 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
  }

  * {
    transition: var(--transition-base);
  }
}
```

### 6.2 Component Memoization

```tsx
// Usar React.memo para componentes pesados
import { memo } from 'react';

export const InputForm = memo(function InputForm({
  onSubmit,
  isLoading,
  context
}: InputFormProps) {
  // ... component implementation
});
```

---

## 7. Testing e Validação

### 7.1 Checklist de Validação UI/UX

- [ ] **Contraste**: Todos os textos atendem WCAG AA (4.5:1 para texto normal, 3:1 para texto grande)
- [ ] **Hierarquia**: 3 níveis visuais distintos (background, card principal, cards internos)
- [ ] **Interatividade**: Estados hover/focus/active em todos elementos interativos
- [ ] **Responsividade**: Layout funciona de 320px a 4K
- [ ] **Performance**: First Contentful Paint < 1.5s
- [ ] **Acessibilidade**: Navegação completa via teclado
- [ ] **Microinterações**: Animações suaves e com propósito
- [ ] **Feedback**: Estados de loading e erro claros

### 7.2 Métricas de Sucesso

1. **Tempo de conclusão do formulário**: Redução de 30%
2. **Taxa de abandono**: Redução de 40%
3. **Satisfação do usuário**: Score NPS > 8
4. **Acessibilidade**: Score Lighthouse > 95
5. **Performance**: LCP < 2.5s, FID < 100ms, CLS < 0.1

---

## 8. Implementação Progressiva

### Fase 1: Foundation (Semana 1)
1. Implementar novo sistema de cores
2. Ajustar espaçamentos e layout base
3. Corrigir hierarquia visual

### Fase 2: Enhancement (Semana 2)
1. Adicionar microinterações
2. Implementar animações
3. Melhorar estados interativos

### Fase 3: Polish (Semana 3)
1. Otimizar performance
2. Garantir acessibilidade completa
3. Testes com usuários

### Fase 4: Refinement (Semana 4)
1. Ajustes baseados em feedback
2. Documentação completa
3. Deploy e monitoramento

---

## 9. Conclusão

Este redesign transformará a interface do Instagram Ads Generator em uma experiência premium que:

1. **Encanta visualmente** através de hierarquia clara e estética moderna
2. **Guia intuitivamente** o usuário através do processo
3. **Responde instantaneamente** com feedback visual rico
4. **Adapta-se perfeitamente** a qualquer dispositivo
5. **Inclui todos** através de acessibilidade exemplar

O resultado será uma interface que não apenas funciona, mas que estabelece um novo padrão de excelência em ferramentas de geração de anúncios, elevando a percepção de qualidade e profissionalismo do produto.

---

## Anexos

### A. Referências de Design
- Material Design 3.0
- Apple Human Interface Guidelines
- IBM Carbon Design System
- Tailwind UI

### B. Ferramentas Recomendadas
- **Análise de Contraste**: WebAIM Contrast Checker
- **Acessibilidade**: axe DevTools
- **Performance**: Lighthouse
- **Animações**: Framer Motion

### C. Recursos Adicionais
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Web.dev Performance](https://web.dev/performance/)
- [A11y Project](https://www.a11yproject.com/)
- [Motion Design Principles](https://material.io/design/motion/)