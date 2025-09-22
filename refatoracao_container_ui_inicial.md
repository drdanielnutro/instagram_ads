# Plano de Refatoração – Container Responsivo do Wizard de Onboarding

## 1. Objetivo

Corrigir a quebra de layout no componente `WizardForm` que ocorre em telas menores ou quando conteúdo dinâmico (como mensagens de erro) aumenta a altura do card principal. A implementação garantirá que o cabeçalho (`ProgressHeader`) e o rodapé (`NavigationFooter`) permaneçam fixos e visíveis, enquanto apenas a área de conteúdo central (`StepCard`) se torne rolável quando necessário.

## 2. Arquivo-Alvo

-   **Caminho:** `frontend/src/components/WizardForm/WizardForm.tsx`

## 3. Componente Principal Afetado

-   **Nome:** `WizardForm`

## 4. Análise do Problema (O "Porquê" da Mudança)

Atualmente, o layout do `WizardForm` é construído com um container Flexbox (`flex-col`) que ocupa a altura da tela (`min-h-screen`). Seus três filhos diretos — `ProgressHeader`, `StepCard` e `NavigationFooter` — são empilhados verticalmente.

O problema fundamental é que **nenhum destes filhos foi designado para lidar com o transbordamento de conteúdo (overflow)**. Quando o conteúdo dentro do `StepCard` cresce (por exemplo, com o surgimento de uma mensagem de erro), o `StepCard` aumenta sua própria altura. Como ele está em um fluxo de coluna, ele inevitavelmente empurra o `NavigationFooter` para baixo, muitas vezes para fora da área visível da tela.

A correção é necessária para criar uma experiência de usuário robusta, onde os controles de navegação primários (`NavigationFooter`) nunca fiquem inacessíveis, independentemente da altura do conteúdo dinâmico.

## 5. Plano de Ação Técnico

A solução consiste em uma única e precisa alteração na estrutura JSX do componente `WizardForm`, envolvendo a criação de um container wrapper para a área de conteúdo.

### Passo 1: Isolar a Área de Conteúdo e Torná-la Rolável

No arquivo `frontend/src/components/WizardForm/WizardForm.tsx`, localizaremos o `return` do componente e aplicaremos a seguinte alteração:

**Estrutura Atual:**
```tsx
<div className="mx-auto w-full max-w-4xl lg:max-w-5xl flex-1 flex flex-col gap-6">
  <ProgressHeader ... />
  <StepCard ...>
    {renderStepContent()}
  </StepCard>
  <NavigationFooter ... />
</div>
```

**Nova Estrutura Proposta:**
```tsx
<div className="mx-auto w-full max-w-4xl lg:max-w-5xl flex-1 flex flex-col gap-6">
  <ProgressHeader ... />

  {/* Wrapper para a área de conteúdo */}
  <div className="flex-1 min-h-0 overflow-y-auto">
    <StepCard ...>
      {renderStepContent()}
    </StepCard>
  </div>

  <NavigationFooter ... />
</div>
```

### Justificativa das Classes Adicionadas ao Novo `div`:

-   **`flex-1`**: Esta classe é a mais importante. Ela instrui este novo container a se expandir e ocupar todo o espaço vertical que estiver disponível entre o `ProgressHeader` e o `NavigationFooter`.
-   **`min-h-0`**: Esta é uma classe crucial para o correto funcionamento do `flex-1` em um container com overflow. Por padrão, um item flex não encolhe para um tamanho menor que o seu conteúdo. `min-h-0` sobrescreve esse comportamento, permitindo que o container `flex-1` possa de fato encolher e ser contido pelos limites do pai, em vez de expandir indefinidamente com seu conteúdo. É isso que impede que ele empurre o `NavigationFooter` para fora.
-   **`overflow-y-auto`**: Esta classe aplica a funcionalidade de rolagem. Uma barra de rolagem vertical aparecerá automaticamente *neste `div`* se, e somente se, o conteúdo do `StepCard` (que está dentro dele) se tornar mais alto que o espaço disponível.

### Passo 2: Manter Componentes Fixos

-   **Componentes:** `ProgressHeader` e `NavigationFooter`.
-   **Ação:** Nenhuma alteração é necessária nestes componentes.
-   **Justificativa:** Eles já estão corretamente posicionados como itens não-flexíveis no início e no fim do container `flex-col` principal. A alteração no Passo 1 garante que eles permanecerão fixos em suas posições enquanto a área central rola.

## 6. Resultado Esperado

Após a implementação, o `NavigationFooter` (com os botões "Voltar", "Próximo" e "Gerar anúncios") permanecerá sempre visível e "ancorado" na parte inferior do container do wizard. Apenas a área do `StepCard` se tornará rolável quando seu conteúdo exceder a altura disponível, proporcionando uma experiência de usuário fluida e sem quebras de layout.
