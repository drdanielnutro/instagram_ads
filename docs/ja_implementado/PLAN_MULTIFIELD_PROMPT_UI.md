# Plano: Refatorar Prompt Inicial em Campos Separados

## Objetivo
Transformar o formulário inicial da UI em cinco campos opcionais, facilitando o input estruturado sem exigir que o usuário lembre o formato textual completo.

## Campos Propostos
- `landing_page_url` (campo de texto).
- `perfil_cliente` (campo de texto multiline).
- `foco` (campo de texto multiline).
- `objetivo_final` (select com opções pré-definidas).
- `formato_anuncio` (select com opções pré-definidas).

## Opções do Select `objetivo_final`
1. agendamentos de consulta via WhatsApp
2. agendamentos de consulta via formulário
3. geração de leads qualificados
4. inscrições em evento/webinar
5. vendas diretas de produto/serviço
6. download de material rico (e-book, guia)

## Opções do Select `formato_anuncio`
- Feed
- Stories
- Reels
- Carrossel

## Etapas de Implementação
1. **Preparação do componente**: importar e configurar os componentes `Input`, `Textarea` e `Select` do shadcn/ui, além de definir estado local individual para cada campo.
2. **Renderização dos campos**: substituir o `Textarea` único por três campos de texto (com labels e placeholders curtos) e dois selects com as opções acima.
3. **Montagem do payload**: no `handleSubmit`, montar o prompt final concatenando apenas os campos preenchidos no formato `chave: valor`, mantendo compatibilidade com o backend.
4. **Tratamento de estados**: garantir que os campos sejam opcionais, limpar valores após envio bem-sucedido e manter desabilitado enquanto `isLoading` for verdadeiro.
5. **Ajustes de UX**: atualizar placeholders, ajuda textual e mensagens no `WelcomeScreen` (e no contexto de chat) para refletem o novo fluxo.
6. **Validação manual**: testar `make dev`, preencher combinações variadas (inclusive deixando campos vazios) e confirmar que o backend recebe o prompt formatado corretamente.

## Riscos e Mitigações
- **Compatibilidade com backend**: manter formato atual garante que nenhum ajuste de API seja necessário.
- **Acessibilidade/UX**: usar labels claros e placeholders breves para evitar confusão; considerar tooltips se necessário.
- **Expansão futura**: listas de opções declaradas em arrays para facilitar inclusão de novos objetivos ou formatos.

