# Plano de Atualização — Detalhamento de Prompts e Uso de Referências Visuais

## 0. Objetivo Geral
- **Meta**: Atualizar o documento `imagem_roupa.md` para descrever, com nível operacional, como referências visuais opcionais (personagem e produto) devem ser tratadas, incluindo condicionais nos prompts e critérios para manipulação de expressões faciais.
- **Escopo**: Somente edição do plano existente (`imagem_roupa.md`). Não envolve alterações de código ou configuração.

---
## Fase 1 — Levantamento e Diagnóstico do Documento Atual

### Objetivo específico
Garantir entendimento profundo do estado atual do plano e identificar todas as lacunas narrativas e técnicas relacionadas ao uso de referências visuais, servindo de insumo para as fases posteriores.

### Atividades detalhadas
1. **Leitura estruturada**: revisar sequencialmente todas as seções de `imagem_roupa.md` (Visão Geral, Fases 1–7, Dependências, Riscos, Apêndices) anotando trechos que mencionem referências visuais, prompts e comportamento opcional.
2. **Inventário de lacunas**: classificar cada ausência em três categorias – `Opcionalidade`, `Uso obrigatório pós-aprovação` e `Adaptação de expressão/prompt`. Para cada ocorrência, registrar a página/seção afetada e o risco associado.
3. **Consolidação das evidências**: transformar as anotações em uma tabela "Lacunas de Detalhamento" posicionada após a Visão Geral, contendo colunas: `Seção`, `Descrição da lacuna`, `Impacto esperado`, `Prioridade de correção (Alta/Média/Baixa)`.
4. **Validação cruzada**: confrontar as lacunas identificadas com os requisitos descritos pelo usuário nesta conversa para assegurar que nenhuma necessidade declarada fique de fora do mapeamento.

### Entregáveis
- Tabela "Lacunas de Detalhamento" acrescentada ao documento com, no mínimo, uma entrada por categoria de ausência identificada.
- Registro textual breve anterior à tabela explicando a metodologia de diagnóstico empregada.

### Dependências existentes
- Conteúdo atual de `imagem_roupa.md` (versão em vigor neste repositório).
- Observações do usuário (requisitos de opcionalidade e diferenciação de prompts para personagem/produto).
- `guia_redacao_planos_implementacao.md` para alinhamento de linguagem e estrutura de seções.

### Critérios de aceitação
- [ ] Tabela de lacunas adicionada próximo ao topo do documento (logo após Visão Geral) para contextualizar ajustes que serão feitos nas fases seguintes.
- [ ] Cada lacuna está classificada em uma das três categorias e possui indicação de impacto.

---
## Fase 2 — Atualizações na Visão Geral e Metas

### Objetivo específico
Reposicionar a introdução do plano para que os stakeholders compreendam, logo no início, os compromissos sobre referências visuais opcionais, usos mandatórios após aprovação e implicações para o pipeline de prompts.

### Atividades detalhadas
1. **Redação de contexto ampliado**: incluir parágrafo introdutório explicando por que referências opcionais exigem lógica condicional nos agentes e como isso impacta a experiência do anunciante.
2. **Definição explícita de cenários**: adicionar bullets enumerando os quatro cenários suportados (sem referências, apenas personagem, apenas produto, ambos) descrevendo comportamento esperado em cada um.
3. **Política de uso obrigatório**: inserir sub-bullet especificando que qualquer referência aprovada pelo SafeSearch deve ser utilizada em todas as etapas pertinentes (prompts, geração visual, montagem final) e que rejeições devem ser registradas/logadas.
4. **Compromissos de prompt**: destacar, em linguagem prescritiva, a obrigação de diferenciação dos prompts quando `reference_image_character_summary` existir, incluindo menção à preservação de traços físicos e à adaptação de expressão facial conforme instruções do ADK.
5. **Indicadores de sucesso**: apontar métricas textuais (ex.: "QA deve comprovar que prompts finais mencionam explicitamente a presença do personagem quando disponível") para orientar validações futuras.

### Entregáveis
- Seção "Visão Geral & Metas" reescrita com os novos parágrafos e bullets descritos nas atividades.
- Nota lateral ou box de destaque resumindo o fluxo de aprovação via SafeSearch e a obrigatoriedade subsequente de uso.

### Critérios de aceitação
- [ ] Seção atualizada apresenta requisitos textuais sobre opcionalidade, obrigatoriedade de uso após aprovação e diferenciação de prompts.
- [ ] Os quatro cenários (0, 1 ou 2 referências) estão descritos com comportamento esperado.

---
## Fase 3 — Ajustes na Fase 4 (Pipeline & Prompts)

### Objetivo específico
Determinizar, na própria descrição do pipeline, como os agentes devem consumir dados de referências visuais e como os prompts se adaptam a cada cenário, garantindo que implementadores não precisem interpretar lacunas.

### Atividades detalhadas
1. **Reorganização estrutural**: dividir a seção "Fase 4 – Pipeline de Agentes" em subtítulos numerados (ex.: "4.1 Placeholders e estrutura de dados", "4.2 Diretrizes de Prompting para Personagem", "4.3 Diretrizes quando apenas Produto estiver presente", "4.4 Compatibilidade com instruções fixas dos agentes").
2. **Definição de placeholders condicionais**: para cada subtítulo, documentar quais campos devem ser introduzidos nos prompts (`{reference_image_character_summary}`, `{reference_image_product_summary}`, flags booleanas, notas do SafeSearch) e a lógica que ativa cada um (ex.: "incluir somente quando `reference_images.character.status == 'approved'`").
3. **Guia aprofundado de prompting**: elaborar lista de verificação para `VISUAL_DRAFT`, `COPY_DRAFT` e `final_assembler` contendo:
   - Frases-modelo que mencionem o personagem pelo nome/descrição quando existir.
   - Instruções explícitas de preservação de características físicas (tom de pele, cabelo, formato de rosto).
   - Exigência de comandos que permitam mudar a expressão facial (ex.: "If the ADK prompt requests a different emotion, articulate it as 'render the same character now showing <emoção>'").
4. **Cenários sem personagem**: definir estrutura condicional para remover instruções sobre personagem, reforçando descrição de produto e storytelling correspondente.
5. **Não regressão das instruções fixas**: inserir parágrafo garantindo que os campos já estabelecidos para três imagens sequenciais (prompts `prompt_estado_atual`, `prompt_estado_intermediario`, `prompt_estado_aspiracional`) continuam obrigatórios; sugerir nota sobre como novos placeholders convivem com eles sem alterar formato esperado pelos agentes `code_generator`, `code_reviewer`, `code_refiner`.
6. **Quadro comparativo**: adicionar tabela resumindo diferenças de prompts entre os quatro cenários (nenhum, apenas personagem, apenas produto, ambos) destacando exemplos de frases-chave e objetivos.

### Entregáveis
- Seção Fase 4 reescrita com subtítulos, tabela comparativa e listas de verificação descritas.
- Anexo (ou bloco em destaque) com exemplos de prompts antes/depois demonstrando adaptação de expressão facial.

### Critérios de aceitação
- [ ] Subtópicos adicionados explicam mudanças de expressão facial e preservação de aparência.
- [ ] Diferenças textuais deixam explícito que ajustes convivem com instruções fixas dos agentes (`code_generator`, `code_reviewer`, `code_refiner`).
- [ ] Tabela comparativa cobre os quatro cenários possíveis.

---
## Fase 4 — Critérios de Aceitação e QA

### Objetivo específico
Assegurar que o plano descreva verificações robustas, tanto automatizadas quanto manuais, capazes de comprovar que prompts e saídas honram os requisitos de referências visuais e adaptação de expressão.

### Atividades detalhadas
1. **Revisão dos critérios existentes**: localizar na Fase 4 e na Fase 6 de `imagem_roupa.md` todos os bullets de QA atuais e identificar onde adicionar reforços relacionados a referências.
2. **Ampliação dos testes automatizados**: instruir a criação/atualização de testes unitários e de integração que simulem combinações de referências, incluindo mocks de SafeSearch aprovando/reprovando imagens e asserts sobre a presença de comandos de expressão facial nos prompts.
3. **Checklist de QA manual**: definir passos concretos (capturar screenshots dos prompts gerados, validar que personagem é citado quando disponível, comprovar mudança de expressão solicitada) e anexar à fase pertinente.
4. **Evidências esperadas**: solicitar que as equipes documentem exemplos "antes/depois" em artefatos de QA (ex.: pasta `artifacts/qa/reference-images`) para compor baseline visual.
5. **Cobertura de regressão**: inserir instrução garantindo que os testes mantenham critérios já existentes sobre três imagens sequenciais, assegurando que novos casos não removam asserts prévios.

### Entregáveis
- Atualização das seções de critérios de aceitação com bullets específicos sobre transformação de expressão, uso condicional de referências e coleta de evidências.
- Seção QA enriquecida com links ou referências a fixtures/mocks necessários para testes de personagem com expressão divergente.

### Critérios de aceitação
- [ ] Critérios atualizados descrevem explicitamente cenários de mudança de expressão.
- [ ] QA manual/documentação passa a exigir captura de exemplos antes/depois quando houver personagem.
- [ ] Novos testes/mocks descritos não conflitam com os requisitos existentes do pipeline de agentes.

---
## Fase 5 — Consolidação e Revisão Final

### Objetivo específico
Finalizar a atualização do plano assegurando consistência editorial, rastreabilidade das mudanças e alinhamento com as instruções permanentes dos agentes.

### Atividades detalhadas
1. **Seção de síntese**: criar a subseção "Resumo das Atualizações de Prompt" contendo bullets agrupados por tema (`Opcionalidade`, `Uso obrigatório`, `Adaptação de expressão`, `Compatibilidade com agentes`).
2. **Revisão terminológica**: executar busca por termos divergentes ("imagem de personagem", "foto do personagem", etc.) e unificar nomenclatura em todo o documento; registrar no changelog do plano se houver.
3. **Cross-check com Fase 1**: verificar se todas as lacunas listadas na tabela inicial receberam solução nas fases 2–4; caso alguma permaneça, descrevê-la como "pendência" ou justificar sua postergação.
4. **Controle de regressão**: reler as seções que tratam dos agentes `code_generator`, `code_reviewer` e `code_refiner`, confirmando que os reforços determinísticos introduzidos anteriormente foram preservados; incluir nota explícita reiterando que essas instruções permanecem válidas e que os novos ajustes são incrementais.
5. **Preparação para aprovação**: adicionar checklist final com itens que o revisor deve validar antes de aprovar a atualização (ex.: "confirmar presença da tabela de lacunas", "validar exemplos de prompts com mudança de expressão").

### Entregáveis
- Seção final adicionada com bullets claros e agrupados por tema.
- Checklist de aprovação final anexado ao término do documento.

### Critérios de aceitação
- [ ] Seção-resumo adicionada com bullets claros.
- [ ] Terminologia harmonizada em todas as fases.
- [ ] Nota sobre preservação das instruções dos agentes presente quando apropriado.
- [ ] Todas as lacunas da Fase 1 possuem resolução registrada ou justificativa formal.

---
## Checklist de Finalização
- [ ] Todas as novas subseções utilizam linguagem declarativa, alinhada ao `guia_redacao_planos_implementacao.md`.
- [ ] Diferenças planejadas citam explicitamente que tratam-se de edições no documento `imagem_roupa.md` (sem tocar código).
- [ ] Plano pronto para validação via `plan-code-validator`, sem introduzir dependências inexistentes.
- [ ] Documento final responde aos questionamentos do usuário sobre opcionalidade, uso obrigatório após aprovação e adaptação de expressão facial.

