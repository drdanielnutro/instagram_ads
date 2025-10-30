## Ajuste do Preview com Overlays Instagram-Like

### 1. Confirmar Dados Disponíveis
- Arquivos: `frontend/src/components/AdsPreview.tsx`, `frontend/src/types/ad-preview.ts`, `json_completo_que_deu_certo.json` (referência).
- Garantir que `sanitizeVariation` fornece:
  - `copy.headline`, `copy.cta_texto`.
  - `cta_instagram`, `landing_page_url`.
  - `visual.images` ou fallback (`image_estado_atual_url`, `image_estado_intermediario_url`, `image_estado_aspiracional_url`).
  - Ordens: índice `0` = estado atual, `1` = intermediário, `2` = aspiracional.
- Definir função utilitária para extrair domínio: `empresa = new URL(landing_page_url).hostname` com fallback vazio.

### 2. Modelar Overlays por Etapa
- Alterar `ImageCarousel` (mesmo arquivo) para envolver `<img>` em container `relative` permitindo componentes `absolute`.
- Regras por índice:
  - **0 – Estado atual**
    - Renderizar faixa translúcida superior (`absolute top-0 left-0 right-0`), gradiente escuro, texto `headline`.
    - Tipografia: `text-base font-semibold`, `text-white`, `line-clamp-2`.
    - Renderizar apenas se `headline` existir.
  - **1 – Intermediário**
    - Adicionar selo com domínio (`empresa`) sobreposto próximo ao badge existente (canto superior esquerdo, `absolute left-4 top-12`, z-index inferior ao badge principal).
    - Estilo: `rounded-full px-3 py-1 bg-background/85 border border-border/60 text-xs`.
    - Ocultar se domínio vazio.
  - **2 – Aspiracional**
    - Colocar botão CTA (`copy.cta_texto || cta_instagram`) no canto inferior direito (`absolute bottom-5 right-5`).
    - Utilizar `<Button size="sm">`, aplicar `shadow-lg`. Fallback central (`left-1/2 translate-x-[-50%]`) em telas muito estreitas (`w < 320px` via CSS utilitário responsivo).
    - Não renderizar sem texto.
- Ajustar z-index dos botões de navegação (já usam `z-10`) para ficar acima da faixa.

### 3. Manter Compatibilidade/Acessibilidade
- Sobrescrever apenas nos ramos onde `hasImages && imageSrc`.
- No fallback textual (`!hasImages`), não renderizar overlays.
- CTA deve ter `aria-label`/`title` descrevendo a ação.
- Garantir que badge `stageLabel` continue visível (talvez deslocar faixa headline para não sobrepor).
- Verificar que overlays não surgem durante `isLoading`/`hasError`.

### 4. Revisar Tipos & Utilitários
- Se necessário, estender `AdVariation` para incluir `landing_page_url` (já existente) e possíveis campos futuros.
- Criar helper dentro de `AdsPreview.tsx` para obter domínio com try/catch (evitar erro em URLs inválidas).

### 5. Teste Manual Rápido
- Cenário com imagens válidas: confirmar overlays em cada etapa.
- Cenário sem imagens (apenas prompts): preview segue funcionando sem overlays.
- Testar variação sem headline/CTA → overlays correspondentes ocultos.
- Responsividade: verificar breakpoints ~375px e >=768px.
