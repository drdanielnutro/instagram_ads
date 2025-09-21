# Auditoria Codex CLI – Preview de Anúncios

## 1. Ativação do Preview
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 1.1 | Conforme | `frontend/.env.example:8` define `VITE_ENABLE_ADS_PREVIEW=false` conforme especificado.
| 1.2 | Conforme | A seção de feature flags documenta finalidade, ativação, desativação e reinício do preview (`frontend/README.md:16-24`).
| 1.3 | Conforme | Helper `isPreviewEnabled` utiliza `readBooleanFlag` para normalizar a flag (`frontend/src/utils/featureFlags.ts:21-26`).
| 1.4 | Inconsistente | O botão `Preview` é renderizado sempre que a flag está ativa, mesmo com `deliveryMeta?.ok` falso, ficando apenas desabilitado (`frontend/src/App.tsx:670-678`), contrariando o plano que exige exibição somente quando os dados estiverem prontos.
| 1.5 | Conforme | `openPreview` valida flag, meta e identificadores antes de abrir o modal (`frontend/src/App.tsx:65-71`).
| 1.6 | Conforme | `fetchPreviewData` faz `GET` em `/api/delivery/final/download` com parâmetros codificados (`frontend/src/components/AdsPreview.tsx:244-279`).
| 1.7 | Conforme | A rotina trata respostas JSON diretas e assinadas, normalizando o payload (`frontend/src/components/AdsPreview.tsx:264-280`).
| 1.8 | Conforme | `normalizeVariations` garante array e o efeito dispara o carregamento ao abrir o modal (`frontend/src/components/AdsPreview.tsx:282-327`).

## 2. Estrutura Simplificada (MVP)
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 2.1 | Conforme | O MVP está centralizado em `frontend/src/components/AdsPreview.tsx`, conforme planejado (linhas 1-579).
| 2.2 | Conforme | Não houve extração de subcomponentes para arquivos separados; helpers e renders permanecem no mesmo arquivo (`frontend/src/components/AdsPreview.tsx:55-508`).

## 3. Componente Principal
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 3.1 | Conforme | `AdsPreviewProps` define `userId`, `sessionId`, `isOpen` e `onClose` (`frontend/src/components/AdsPreview.tsx:11-15`).
| 3.2 | Conforme | Estados `variations`, `currentVariation`, `currentImageIndex`, `isFetchingPreview` e `imageErrors` estão presentes (`frontend/src/components/AdsPreview.tsx:228-234`).
| 3.3 | Conforme | Imports incluem `Button`, `Badge`, `Card`, `CardContent`, `CardHeader`, `CardTitle`, `ScrollArea`, `Tabs`, `TabsList` e `TabsTrigger` (`frontend/src/components/AdsPreview.tsx:2-7`).

## 4. Layout do Modal
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 4.1 | Conforme | `Dialog.Root`/`Dialog.Content` usam overlay `bg-background/80`, `bg-card`, borda e sombra conforme o plano (`frontend/src/components/AdsPreview.tsx:510-518`).
| 4.2 | Conforme | Cabeçalho com título e botão `Fechar` (`variant="ghost"`, `size="icon"`) implementado (`frontend/src/components/AdsPreview.tsx:519-530`).
| 4.3 | Conforme | Tabs dinâmicas de variações aparecem quando há mais de uma (`frontend/src/components/AdsPreview.tsx:533-557`).
| 4.4 | Conforme | Layout principal usa `ScrollArea` para dispositivo e textos em estrutura responsiva (`frontend/src/components/AdsPreview.tsx:559-568`).
| 4.5 | Conforme | Rodapé apresenta botão `Recarregar dados` com estado de loading (`frontend/src/components/AdsPreview.tsx:571-574`).

## 5. Renderização por Formato
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 5.1 | Inconsistente | `renderFeedDevice` não contém o card com copy e CTA mostrado no plano; apenas um bloco genérico de descrição (`frontend/src/components/AdsPreview.tsx:333-355`).
| 5.2 | Conforme | `renderVerticalDevice` usa moldura arredondada e faixas de safe zone sobre o carrossel (`frontend/src/components/AdsPreview.tsx:359-388`).
| 5.3 | Inconsistente | Faltam cards auxiliares de CTA/explicações conforme formatos; os renders não adicionam os elementos previstos no plano (`frontend/src/components/AdsPreview.tsx:333-389`).
| 5.4 | Conforme | Há aviso textual sobre ausência de imagens tanto no carrossel quanto na descrição (`frontend/src/components/AdsPreview.tsx:100-106`, `353-354`).

## 6. Componente Carrossel
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 6.1 | Conforme | `ImageCarousel` recebe imagens opcionais, aspecto, callbacks e índice atual (`frontend/src/components/AdsPreview.tsx:55-134`).
| 6.2 | Conforme | Placeholder orientativo exibido quando não há URLs (`frontend/src/components/AdsPreview.tsx:100-106`).
| 6.3 | Inconsistente | O carrossel não possui controles laterais nem dots; apenas botões de prompt, divergindo do layout especificado (`frontend/src/components/AdsPreview.tsx:70-133`).
| 6.4 | Inconsistente | Falta destaque visual permanente das etapas sobre a imagem quando há URLs, diferente da etiqueta planejada (`frontend/src/components/AdsPreview.tsx:70-133`).

## 7. Área de Textos
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 7.1 | Conforme | Card de copy com headline, corpo e CTA em `Badge` implementado (`frontend/src/components/AdsPreview.tsx:422-439`).
| 7.2 | Inconsistente | Metadados não exibem `cta_instagram` nem link clicável para a landing, ao contrário do plano (`frontend/src/components/AdsPreview.tsx:444-467`).
| 7.3 | Conforme | Descrição visual e prompts utilizam `PromptBlock` (`frontend/src/components/AdsPreview.tsx:472-485`).
| 7.4 | Inconsistente | Referências e StoryBrand são cards estáticos; faltam blocos colapsáveis com `<details>` (`frontend/src/components/AdsPreview.tsx:489-505`).

## 8. Fetch e Atualização de Dados
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 8.1 | Conforme | Estados são resetados ao abrir/fechar o modal (`frontend/src/components/AdsPreview.tsx:320-327`).
| 8.2 | Conforme | Fluxo tenta endpoint principal e, se necessário, a URL assinada (`frontend/src/components/AdsPreview.tsx:264-280`).
| 8.3 | Conforme | `normalizeVariations` e o set garantem que `variations` seja um array (`frontend/src/components/AdsPreview.tsx:136-158`, `282-288`).
| 8.4 | Conforme | Loading e erros são tratados com estado e mensagem exibida no cabeçalho (`frontend/src/components/AdsPreview.tsx:249-291`, `522-524`).

## 9. Tratamento de Erros de Imagem
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 9.1 | Conforme | Falhas mapeadas por chave `variação-imagem` em `Map` (`frontend/src/components/AdsPreview.tsx:294-299`).
| 9.2 | Conforme | Placeholder de erro informa o usuário e oferece ação de retry (`frontend/src/components/AdsPreview.tsx:82-89`).
| 9.3 | Conforme | `fetchPreviewData()` é reutilizado na tentativa de recarregar imagens (`frontend/src/components/AdsPreview.tsx:87-88`).

## 10. Responsividade
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 10.1 | Conforme | Modal ocupa fullscreen no mobile com `fixed inset-0` e `rounded-none` (`frontend/src/components/AdsPreview.tsx:517-518`).
| 10.2 | Conforme | Versão desktop centralizada com `md:h-[90vh]` e `md:max-w-[1100px]` (`frontend/src/components/AdsPreview.tsx:517-518`).
| 10.3 | Conforme | Layout alterna entre colunas e linhas garantindo navegação em múltiplos breakpoints (`frontend/src/components/AdsPreview.tsx:559-568`).

## 11. Integração em `App.tsx`
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 11.1 | Conforme | Estado `showPreview` criado para controlar o modal (`frontend/src/App.tsx:59`).
| 11.2 | Inconsistente | Botão `Preview` aparece com a flag ativa mesmo sem `deliveryMeta?.ok`, apenas desabilitado; o plano exige renderização condicionada ao `ok` (`frontend/src/App.tsx:670-678`).
| 11.3 | Conforme | `handleDownloadFinal` continua sendo usado para downloads (`frontend/src/App.tsx:679-684`).
| 11.4 | Conforme | `AdsPreview` é renderizado com `userId`, `sessionId`, `isOpen` e `onClose` corretos (`frontend/src/App.tsx:725-731`).

## 12. Tipos TypeScript
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 12.1 | Inconsistente | `VisualInfo` e `AdVariation` foram definidos com campos opcionais e variantes genéricas adicionais, enfraquecendo o contrato especificado no plano (`frontend/src/types/ad-preview.ts:1-26`).
| 12.2 | Conforme | `AdsPreview` consome os novos tipos (`frontend/src/components/AdsPreview.tsx:8`, `228-234`).

## 13. Helpers
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 13.1 | Conforme | Helpers `getAspectRatioClass`, `isVerticalFormat` e `getVariationImages` implementados (`frontend/src/components/AdsPreview.tsx:169-199`).
| 13.2 | Conforme | `isPreviewEnabled` é exportado pelo utilitário de flags (`frontend/src/utils/featureFlags.ts:23-26`).
| 13.3 | Inconsistente | Não há documentação sobre o comportamento futuro das URLs de imagem como indicado no plano (nenhum comentário em `frontend/src/components/AdsPreview.tsx`).
| 13.4 | Inconsistente | `PromptBlock` não foi disponibilizado para reutilização fora do componente; permanece escopo local (`frontend/src/components/AdsPreview.tsx:22-53`).

## 14. Estilos e Temas
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 14.1 | Conforme | Modal usa tokens do tema escuro (`bg-card`, `border-border`, `text-muted-foreground`) (`frontend/src/components/AdsPreview.tsx:510-574`).
| 14.2 | Conforme | Bordas arredondadas amplas e sombra profunda estão aplicadas (`frontend/src/components/AdsPreview.tsx:517-574`).
| 14.3 | Conforme | Variações com opacidade (`bg-card/70`, `bg-background/60`, `bg-primary/10`) são utilizadas para profundidade (`frontend/src/components/AdsPreview.tsx:333-575`).

## 15. Considerações Finais
| Item | Status | Evidências e observações |
| --- | --- | --- |
| 15.1 | Inconsistente | Não há registro de validação formal de aderência ao MVP ou nota de conclusão; nenhum artefato/documentação encontrado.
| 15.2 | Inconsistente | Não foram localizadas evidências de revisão de consistência com guidelines do projeto ou com o JSON final.
