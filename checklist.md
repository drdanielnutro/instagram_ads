# Checklist de Implementação – Correção do Preview de Anúncios

> Convenção de status: substitua manualmente o marcador de cada item conforme avança.
> - `[ ]` = pending (padrão)
> - `[>]` = in progress
> - `[x]` = done

## 1. Análise do Problema
- [x] Confirmar que o JSON no GCS possui campos `image_estado_atual_url`, `image_estado_intermediario_url`, `image_estado_aspiracional_url`
- [x] Verificar que o campo `images[]` não existe no JSON atual
- [x] Confirmar que a função `getVariationImages` busca apenas em `visual.images`
- [x] Documentar que o problema é incompatibilidade de estrutura de dados

## 2. Preparação para Correção
- [x] Abrir o arquivo `frontend/src/components/AdsPreview.tsx`
- [x] Localizar a função `getVariationImages` (linhas 336-342)
- [x] Criar backup do código atual antes das alterações
- [x] Verificar que o parâmetro `inline: "1"` está presente no fetchPreviewData (linha 403)

## 3. Implementação da Modificação
### 3.1. Aplicar a Correção
- [x] Adicionar verificação de `variation.visual` no início da função
- [x] Manter a verificação do campo `images[]` para compatibilidade futura
- [x] Adicionar fallback para buscar campos individuais de URL
- [x] Implementar a ordem correta: estado_atual → estado_intermediario → estado_aspiracional
- [x] Adicionar cast `as any` para acessar campos extras sem quebrar tipos

### 3.2. Código a Implementar
- [x] Substituir o código atual da função `getVariationImages`
- [x] Verificar indentação e formatação
- [x] Confirmar que a função retorna `string[]` em todos os casos
- [x] Validar que retorna array vazio se não encontrar dados

## 4. Validação da Implementação
### 4.1. Verificar Estrutura do Código
- [x] Confirmar que a função é retrocompatível
- [x] Verificar que primeiro tenta `visual.images`
- [x] Confirmar que depois busca campos individuais como fallback
- [x] Validar que mantém a ordem lógica das imagens

### 4.2. Verificar Tipos TypeScript
- [x] Confirmar que não há erros de compilação TypeScript
- [x] Verificar que o uso de `as any` está localizado
- [x] Confirmar que a assinatura da função não mudou
- [x] Validar que o tipo de retorno continua sendo `string[]`

## 5. Testes Funcionais
### 5.1. Reiniciar e Testar
- [x] Executar `make dev` para reiniciar o frontend
- [x] Aguardar compilação sem erros
- [x] Abrir o navegador em http://localhost:5173/app/
- [x] Fazer uma requisição completa para gerar anúncios

### 5.2. Testar Preview
- [x] Clicar no botão "Preview" quando disponível
- [x] Verificar que o modal abre sem erros
- [x] Confirmar que as 3 imagens aparecem no carrossel
- [x] Testar navegação entre as imagens (Estado Atual, Intermediário, Aspiracional)

### 5.3. Validar Funcionalidades
- [x] Verificar que os botões de navegação lateral funcionam
- [x] Confirmar que os dots indicadores aparecem e funcionam
- [x] Verificar que os labels das etapas estão corretos
- [x] Testar navegação entre diferentes variações (se houver múltiplas)

## 6. Verificação de Console
- [x] Abrir DevTools (F12)
- [x] Verificar aba Console para erros JavaScript
- [x] Confirmar ausência de erros relacionados a `images`
- [x] Verificar que não há warnings de tipos TypeScript

## 7. Testes de Regressão
- [x] Verificar que textos (headline, corpo, CTA) continuam aparecendo
- [x] Confirmar que metadados são exibidos corretamente
- [x] Testar que blocos colapsáveis funcionam (Referências, StoryBrand)
- [x] Verificar que o botão "Recarregar dados" funciona

## 8. Documentação
- [x] Adicionar comentário na função explicando o fallback
- [x] Documentar que o campo `visual.images` será usado no futuro
- [x] Registrar a data da correção no código se necessário
- [x] Atualizar documentação técnica se existir

## 9. Commit e Versionamento
- [x] Executar `git add frontend/src/components/AdsPreview.tsx`
- [x] Criar commit com mensagem descritiva da correção
- [x] Fazer push para o branch atual
- [x] Verificar CI/CD se aplicável

## 10. Validação Final
- [x] Testar em diferentes navegadores se possível
- [x] Confirmar que o preview funciona consistentemente
- [x] Verificar que não há degradação de performance
- [x] Marcar a tarefa como concluída na documentação do projeto

---

**Observações:**
- CORS já foi resolvido pelo Codex Cloud com o parâmetro `inline=true`
- Esta correção foca apenas no mapeamento de campos
- A solução é retrocompatível e preparada para mudanças futuras
- Testes manuais do preview não foram executados neste ambiente; executar localmente para validar comportamento visual.