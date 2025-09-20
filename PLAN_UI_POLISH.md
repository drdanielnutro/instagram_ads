# Plano: Refinar Estética da Interface

## Objetivo
Elevar a apresentação do front-end para um nível mais profissional mantendo o layout limpo, reforçando hierarquia visual e clarificando o fluxo de geração de anúncios.

## Diretrizes de Identidade Visual
- **Fonte primária**: `Inter` (UI), com fallback sans-serif; **Fonte de destaque**: `Space Grotesk` para títulos.
- **Paleta neutra**: `background` #0e1219, `surface` #141927, `borda` rgba(255,255,255,0.04).
- **Cor de destaque**: `primary` #7f5bff; `primary-hover` #9b7fff; texto secundário `#9aa3b5`.
- **Espaçamento base**: múltiplos de 4 (ex.: 12, 16, 24, 40 px). Sombra consistente `0 30px 60px -20px rgba(12,18,31,0.55)`.
- **Componentes reutilizáveis**: `SectionCard` (card com título/descrição), `StatusBadge`, `StatPill`.

## Ações Planejadas

### 1. Layout Geral
- Criar estrutura em duas colunas: sidebar lateral (status, histórico breve, passos) e área principal (formulário/chat).
- Garantir responsividade: empilhar colunas < 1024px; manter paddings fluidos (`px-6`, `lg:px-12`).
- Adicionar topo com branding simples e indicador de sessão/usuário.

### 2. WelcomeScreen & Formulário Inicial
- Encapsular formulário em `SectionCard` com background translúcido, bordas suaves e gradiente sutil.
- Revisar tipografia de títulos/subtítulos com `Space Grotesk` e scale harmonizado (`text-4xl` → `text-3xl` em telas menores).
- Aplicar grid `md:grid-cols-2` para alinhas selects/inputs, com ícones sutis (ex.: `Link`, `Target`, `Users`).
- Ajustar botão principal com variante `primary` personalizada (`bg-primary` / `hover:bg-primary-hover`, texto bold).

### 3. ChatMessagesView
- Substituir fundo neutro por painel `surface` com borda e sombra; inserir cabeçalho com breadcrumbs da stage atual.
- Revisar bolhas: cantos arredondados uniformes, gradiente leve para mensagens do sistema, ícones consistentes para copiar/loader.
- Incluir barra inferior com `StatPill` mostrando tokens usados e tempo aproximado quando disponível.

### 4. Estados e Micro-interações
- Inputs/Selects: `focus:ring-2 focus:ring-primary/40 focus:border-primary/60`, transições 200ms.
- Botões: usar `transition-all transform` com leve `translate-y-[1px]` ao pressionar.
- Carregamento: loader sutil com `Spinner` + legenda; status global replicado em barra superior.
- Notificações: adotar `toast` leve ou `StatusBadge` com cores (azul progresso, verde pronto, amarelo atenção).

### 5. Ajustes de Tema/Tailwind
- Adicionar variáveis CSS globais (em `src/global.css`): `--color-background`, `--color-surface`, `--color-primary` etc.
- Criar utilitário `.glass-surface` (combinação de `bg` + `backdrop-blur`) para reutilização.
- Atualizar `tailwind.config` se necessário para incluir fontes e sombras novas.

### 6. QA Visual e Funcional
- Rodar `npm run lint` e `npm run build` para garantir Tipos sem regressão.
- Testar manualmente breakpoints (360px, 768px, 1024px, 1440px).
- Verificar acessibilidade básica: contraste (usar plugin ou DevTools), foco navegável com teclado.

## Dependências / Considerações
- Instalar fontes via CSS import (Google Fonts ou self-host). Verificar licenças.
- Confirmar que os novos tokens de cor respeitam guidelines do projeto (ajustar se backend usa outros).
- Coordenar com squad de copy/branding para aprovar texto e nomenclatura de seções.

## Entregáveis
- Código refatorado nos componentes `WelcomeScreen`, `InputForm`, `ChatMessagesView` (+ novos componentes utilitários).
- Atualização de estilos (`global.css`, `tailwind.config.js` se necessário).
- Checklist de QA com capturas dos principais estados.

