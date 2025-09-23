# Revisão do Plano do Componente de Preview de Anúncios

A análise abaixo cobre **todas** as tarefas do arquivo `plan_preview_component/checklist.md`, confrontando o código atual com as instruções do plano `PLAN_PREVIEW_COMPONENT.md`.

## 1. Ativação do Preview
1. **Adicionar `VITE_ENABLE_ADS_PREVIEW=false` em `frontend/.env.example`** — ✅ Conforme. A variável foi incluída exatamente como descrito no plano. 【F:frontend/.env.example†L1-L11】
2. **Documentar a flag em `frontend/README.md`** — ✅ Conforme. A seção “Preview de Anúncios” descreve finalidade, ativação e rollback. 【F:frontend/README.md†L1-L25】
3. **Implementar helper `isPreviewEnabled` em `frontend/src/utils/featureFlags.ts`** — ✅ Conforme. A função delega para `readBooleanFlag` conforme indicado. 【F:frontend/src/utils/featureFlags.ts†L1-L38】
4. **Exibir botão `Preview` em `App.tsx` quando `deliveryMeta?.ok` estiver verdadeiro** — ❌ Inconsistente. O botão é renderizado sempre que a flag está ativada, ainda que `deliveryMeta?.ok` seja falso; apenas o `disabled` impede o clique, contrariando a condição de visibilidade exigida. 【F:frontend/src/App.tsx†L645-L684】
5. **Implementar handler `openPreview` que inicia o fluxo do modal** — ✅ Conforme. O handler confere as pré-condições e abre o modal quando atendidas. 【F:frontend/src/App.tsx†L63-L71】
6. **Realizar GET em `/api/delivery/final/download?user_id=<...>&session_id=<...>`** — ✅ Conforme. A busca ocorre dentro de `fetchPreviewData`. 【F:frontend/src/components/AdsPreview.tsx†L244-L291】
7. **Tratar respostas inline (JSON direto) e assinadas (`{ signed_url }`), normalizando para um único objeto** — ✅ Conforme. O código detecta `signed_url`, realiza o fetch adicional e converte o payload antes do parse. 【F:frontend/src/components/AdsPreview.tsx†L264-L279】
8. **Invocar parsing do JSON final e acionar abertura do modal** — ✅ Conforme. `normalizeVariations` garante um array e o modal abre via estado quando `openPreview` é chamado. 【F:frontend/src/components/AdsPreview.tsx†L136-L158】【F:frontend/src/App.tsx†L63-L71】【F:frontend/src/components/AdsPreview.tsx†L320-L327】

## 2. Estrutura Simplificada (MVP)
9. **Criar arquivo `frontend/src/components/AdsPreview.tsx` concentrando o MVP** — ✅ Conforme. O arquivo único contém toda a lógica do componente. 【F:frontend/src/components/AdsPreview.tsx†L1-L579】
10. **Postergar extração de subcomponentes até a necessidade de refatoração** — ✅ Conforme. Subpartes (`PromptBlock`, `ImageCarousel`) permanecem internas ao arquivo, sem divisão prematura. 【F:frontend/src/components/AdsPreview.tsx†L22-L134】

## 3. Componente Principal
11. **Declarar `AdsPreviewProps` com `userId`, `sessionId`, `isOpen`, `onClose`** — ✅ Conforme. A interface corresponde ao plano. 【F:frontend/src/components/AdsPreview.tsx†L11-L16】
12. **Definir estados internos (`variations`, `currentVariation`, `currentImageIndex`, `isFetchingPreview`, `imageErrors`)** — ✅ Conforme. Todos os estados aparecem exatamente como planejado (além de `fetchError`, complementar). 【F:frontend/src/components/AdsPreview.tsx†L228-L234】
13. **Garantir importação dos componentes UI (`Button`, `Badge`, `Card`, `CardContent`, `CardHeader`, `CardTitle`, `ScrollArea`, `Tabs`, `TabsList`, `TabsTrigger`)** — ✅ Conforme. Todas as importações requisitadas estão presentes. 【F:frontend/src/components/AdsPreview.tsx†L1-L9】

## 4. Layout do Modal
14. **Configurar `Dialog.Root`/`Dialog.Content` com tokens (`bg-card`, `border-border`, `shadow` etc.)** — ✅ Conforme. As classes utilizam os tokens recomendados. 【F:frontend/src/components/AdsPreview.tsx†L510-L576】
15. **Criar cabeçalho com título e botão de fechar (`variant="ghost"`)** — ✅ Conforme. O cabeçalho segue o layout indicado. 【F:frontend/src/components/AdsPreview.tsx†L519-L530】
16. **Renderizar lista dinâmica de variações via `Tabs` quando houver mais de uma** — ✅ Conforme. A renderização é condicional a `variations.length > 1`. 【F:frontend/src/components/AdsPreview.tsx†L533-L556】
17. **Dispor conteúdo principal em layout responsivo (`ScrollArea` para dispositivo e textos)** — ✅ Conforme. O corpo do modal utiliza duas `ScrollArea` conforme solicitado. 【F:frontend/src/components/AdsPreview.tsx†L559-L568】
18. **Incluir rodapé com botão “Recarregar dados” (`variant="outline"`)** — ✅ Conforme. O rodapé segue exatamente o especificado. 【F:frontend/src/components/AdsPreview.tsx†L571-L574】

## 5. Renderização por Formato
19. **Implementar `renderFeedDevice` usando moldura 4:5/1:1 com `ImageCarousel`** — ✅ Conforme. A função aplica `aspectRatioClass` proveniente do helper e usa o carrossel. 【F:frontend/src/components/AdsPreview.tsx†L333-L356】【F:frontend/src/components/AdsPreview.tsx†L169-L178】
20. **Implementar `renderVerticalDevice` com moldura arredondada e faixas de “safe zone”** — ✅ Conforme. As faixas são criadas com elementos posicionados na moldura. 【F:frontend/src/components/AdsPreview.tsx†L359-L389】
21. **Adicionar cards auxiliares para CTA/explicações conforme formato** — ✅ Conforme. Ambos os formatos exibem cartões de descrição orientando o uso visual. 【F:frontend/src/components/AdsPreview.tsx†L350-L389】
22. **Registrar observação sobre fallback textual enquanto não houver URLs de imagem** — ✅ Conforme. O placeholder informa o uso dos prompts como referência visual. 【F:frontend/src/components/AdsPreview.tsx†L100-L107】

## 6. Componente Carrossel
23. **Criar `ImageCarousel` recebendo lista opcional de imagens e aspecto** — ✅ Conforme. O carrossel aceita `images`, `prompts`, `aspectRatioClass` e callbacks. 【F:frontend/src/components/AdsPreview.tsx†L55-L134】
24. **Exibir placeholder temático quando não houver URLs disponíveis** — ✅ Conforme. O bloco sem imagens mostra badge e mensagem temática. 【F:frontend/src/components/AdsPreview.tsx†L100-L108】
25. **Ajustar botões/dots com tokens do tema** — ✅ Conforme. Os botões usam `border-border`, `bg-background/60`, `bg-primary` etc. 【F:frontend/src/components/AdsPreview.tsx†L113-L130】
26. **Destacar etapa atual (Estado Atual / Intermediário / Aspiracional)** — ✅ Conforme. O estado ativo recebe `bg-primary text-primary-foreground`. 【F:frontend/src/components/AdsPreview.tsx†L120-L128】

## 7. Área de Textos
27. **Estruturar cards para copy (headline, corpo, CTA com `Badge`)** — ✅ Conforme. O primeiro card cobre headline, corpo e CTA com badge. 【F:frontend/src/components/AdsPreview.tsx†L421-L441】
28. **Exibir metadados (formato, CTA IG, fluxo, link da landing)** — ✅ Conforme. O card de metadados apresenta os campos solicitados (CTA do Instagram aparece como fallback na badge anterior). 【F:frontend/src/components/AdsPreview.tsx†L444-L467】
29. **Apresentar descrição visual e prompts usando `PromptBlock`** — ✅ Conforme. Os prompts usam o componente dedicado dentro de `CardContent`. 【F:frontend/src/components/AdsPreview.tsx†L472-L487】
30. **Criar blocos colapsáveis (detalhes) para referências e StoryBrand** — ❌ Inconsistente. As seções de referências e StoryBrand são renderizadas como cards estáticos sem qualquer mecânica de colapso, divergindo da instrução explícita. 【F:frontend/src/components/AdsPreview.tsx†L444-L505】

## 8. Fetch e Atualização de Dados
31. **Resetar estados ao abrir modal (`variations`, índices, erros)** — ✅ Conforme. `resetState` limpa os estados e é chamado tanto na abertura quanto no fechamento. 【F:frontend/src/components/AdsPreview.tsx†L236-L327】
32. **Tentar endpoint principal, depois URL assinada se existir** — ✅ Conforme. A função busca o endpoint padrão e, quando presente, segue para a URL assinada. 【F:frontend/src/components/AdsPreview.tsx†L264-L279】
33. **Parsear resposta (string/JSON) e garantir que `variations` seja sempre array** — ✅ Conforme. `safeJsonParse` e `normalizeVariations` executam exatamente esse fluxo. 【F:frontend/src/components/AdsPreview.tsx†L136-L166】
34. **Encerrar com controle de loading e tratamento de erros (toast/log)** — ✅ Conforme. `isFetchingPreview` controla o carregamento e `fetchError` apresenta mensagem de erro. 【F:frontend/src/components/AdsPreview.tsx†L228-L288】【F:frontend/src/components/AdsPreview.tsx†L519-L524】

## 9. Tratamento de Erros de Imagem
35. **Mapear falhas por combinação variação+imagem** — ✅ Conforme. `imageErrors` usa chaves `${variationIndex}-${imageIndex}`. 【F:frontend/src/components/AdsPreview.tsx†L228-L299】
36. **Exibir placeholder com mensagem/ação “Tentar novamente”** — ✅ Conforme. O bloco de erro exibe mensagem e botão de retry. 【F:frontend/src/components/AdsPreview.tsx†L82-L90】
37. **Reutilizar `fetchPreviewData()` para recarregar imagens** — ✅ Conforme. O botão de retry invoca exatamente essa função. 【F:frontend/src/components/AdsPreview.tsx†L87-L90】

## 10. Responsividade
38. **Suportar modal fullscreen em mobile com layout vertical** — ✅ Conforme. `Dialog.Content` ocupa `fixed inset-0` com ajuste para telas pequenas. 【F:frontend/src/components/AdsPreview.tsx†L510-L518】
39. **Centralizar conteúdo e limitar altura (`md:h-[90vh]`) em desktop** — ✅ Conforme. As classes `md:h-[90vh]` e transformações centralizam o modal. 【F:frontend/src/components/AdsPreview.tsx†L510-L518】
40. **Garantir navegação confortável em diferentes breakpoints** — ✅ Conforme. O layout alterna entre coluna e linha (`lg:flex-row`) e define alturas responsivas para as áreas de scroll. 【F:frontend/src/components/AdsPreview.tsx†L559-L568】

## 11. Integração em `App.tsx`
41. **Adicionar estado `showPreview`** — ✅ Conforme. O estado é declarado com `useState`. 【F:frontend/src/App.tsx†L45-L71】
42. **Adicionar botão “Preview” ao lado de “Baixar JSON” na toolbar somente quando `isPreviewEnabled()`** — ✅ Conforme quanto à flag: o botão só é renderizado se `previewEnabled` for verdadeiro. 【F:frontend/src/App.tsx†L670-L677】
43. **Reutilizar `handleDownloadFinal` existente para downloads** — ✅ Conforme. O botão “Baixar JSON” mantém o mesmo handler. 【F:frontend/src/App.tsx†L679-L684】
44. **Renderizar `AdsPreview` conectado aos estados/props corretos** — ✅ Conforme. O componente recebe `userId`, `sessionId`, `isOpen` e `onClose`. 【F:frontend/src/App.tsx†L725-L730】

## 12. Tipos TypeScript
45. **Criar `frontend/src/types/ad-preview.ts` com `VisualInfo` e `AdVariation`** — ❌ Inconsistente parcialmente. O arquivo existe, porém os campos foram definidos como opcionais e `aspect_ratio` aceita `string` genérica, em desacordo com o contrato rígido estabelecido no plano (todos os atributos obrigatórios e `aspect_ratio` restrito ao union previsto). 【F:frontend/src/types/ad-preview.ts†L1-L27】【F:PLAN_PREVIEW_COMPONENT.md†L447-L471】
46. **Atualizar consumidores para usar os novos tipos** — ✅ Conforme. `AdsPreview.tsx` importa e utiliza `AdVariation` para tipar estado e helpers. 【F:frontend/src/components/AdsPreview.tsx†L8-L318】

## 13. Helpers
47. **Implementar `getAspectRatioClass`, `isVerticalFormat`, `getVariationImages`** — ✅ Conforme. As três funções estão presentes e seguem a lógica especificada. 【F:frontend/src/components/AdsPreview.tsx†L169-L199】
48. **Exportar `isPreviewEnabled` via `featureFlags.ts`** — ✅ Conforme. A função é exportada e utilizada em `App.tsx`. 【F:frontend/src/utils/featureFlags.ts†L28-L36】
49. **Documentar comportamento futuro para URLs de imagem** — ❌ Inconsistente. O código não contém comentários ou documentação mencionando o plano para `visual.images`, conforme exigido. 【F:frontend/src/components/AdsPreview.tsx†L169-L199】【F:PLAN_PREVIEW_COMPONENT.md†L521-L555】
50. **Disponibilizar `PromptBlock` para reutilização nos cards de texto** — ✅ Conforme. `PromptBlock` é definido como função reutilizável e aplicado na lista de prompts. 【F:frontend/src/components/AdsPreview.tsx†L22-L53】【F:frontend/src/components/AdsPreview.tsx†L472-L487】

## 14. Estilos e Temas
51. **Garantir uso de tokens do tema escuro (`bg-card`, `border-border`, etc.)** — ✅ Conforme. O componente faz uso extensivo dos tokens recomendados. 【F:frontend/src/components/AdsPreview.tsx†L350-L574】
52. **Aplicar sombras e bordas arredondadas alinhadas ao wizard** — ✅ Conforme. As classes incluem `rounded-[28px]`, `rounded-3xl` e `shadow-[...]`. 【F:frontend/src/components/AdsPreview.tsx†L73-L518】
53. **Utilizar variações com opacidade para profundidade** — ✅ Conforme. Há uso de `bg-card/70`, `bg-background/60`, `bg-muted/30`, etc. 【F:frontend/src/components/AdsPreview.tsx†L73-L574】

## 15. Considerações Finais
54. **Validar aderência ao MVP e extensibilidade pós-MVP** — ❌ Inconsistente. Não há registro ou documentação confirmando a validação solicitada; o plano previa uma checagem explícita. 【F:PLAN_PREVIEW_COMPONENT.md†L561-L571】
55. **Revisar consistência com guidelines do projeto e dados do JSON final** — ❌ Inconsistente. Não foi encontrada evidência de revisão/documentação dessa validação final. 【F:PLAN_PREVIEW_COMPONENT.md†L561-L571】
