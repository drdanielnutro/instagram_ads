# Anexo – Revisão de Planos `.md`

Estas instruções complementam `AGENTS.md` e **devem ser seguidas sempre que o usuário solicitar que o Codex "revise um plano .md"** ou qualquer variação equivalente ("revisar plano", "validar plano markdown", etc.).

## Contexto
- Trabalhe em PT-BR e use America/Sao_Paulo quando precisar citar horários.
- Trate o código-fonte como fonte da verdade. Nunca presuma que o plano está correto.
- Utilize as instruções detalhadas do agente `plan-code-validator` (`.claude/agents/plan-code-validator.md`) como referência técnica obrigatória.

## Procedimento Obrigatório
1. **Localizar e ler o plano** indicado pelo usuário. Resuma rapidamente o objetivo e anote caminhos de arquivos relevantes.
2. **Construir o Creation Registry (First Pass – OBRIGATÓRIO)**:
   - Escaneie TODO o plano antes de classificar qualquer alegação, cobrindo títulos, subtítulos, listas numeradas e bullet points.
   - Registre todo elemento que o plano diz “criar/implementar/adicionar/desenvolver/estender/construir”, incluindo caminhos de arquivos, classes, funções, flags de config, rotas e prompts.
   - Armazene o resultado em um dicionário (`creation_registry`) e anote o tamanho (ex.: `Creation Registry: 23 itens`). Esse registro prevalece sobre qualquer contexto local durante a classificação.
3. **Extrair e classificar alegações (Second Pass)** conforme o sistema do `plan-code-validator`, obedecendo a ordem de precedência:
   - Verifique primeiro se o elemento está no `creation_registry`. Se estiver, classifique como `ENTREGA` mesmo que o texto local use verbos como “usar/chamar/importar”.
   - Se não estiver no registry, avalie os verbos e qualificadores locais:
     - `DEPENDÊNCIA`: verbos de uso/invocação/leitura, menções a algo "existente", "atual", "já implementado".
     - `MODIFICAÇÃO`: verbos como “refatorar”, “modificar”, “ajustar”, “atualizar”.
     - `ENTREGA`: verbos de criação e novos artefatos.
   - Registre a fase/seção de origem de cada alegação para facilitar o mapeamento posterior.
4. **Validar no código** apenas alegações `DEPENDÊNCIA` e `MODIFICAÇÃO`:
   - Localize os arquivos correspondentes no repositório.
   - Verifique assinaturas, tipos, contratos, rotas, constantes, configs e integrações mencionadas.
   - Registre sempre o caminho e a linha (`arquivo.py:42`) usados como evidência.
5. **Avaliar severidade e registrar métricas** usando a escala P0–P3 do `plan-code-validator`, destacando número total de claims, quantas passaram/falharam e quantas foram tratadas como entregas planejadas.
6. **Executar checagens de contradição antes de finalizar**:
   - Garanta que nenhum item classificado como `ENTREGA` (presente no registry) apareça em findings P0/P1.
   - Se houver sobreposição, reclassifique imediatamente e explique o ajuste no relatório.
   - Documente incertezas (ex.: metaprogramação) separadamente, sem classificá-las como blockers.
7. **Montar relatório estruturado** com:
   - Resumo executivo (quantidade de achados por severidade e impacto).
   - Métricas: totais por classificação, tamanho do `creation_registry`, número de blockers verdadeiros.
   - Lista de inconsistências contendo severidade, alegação original, evidência no código e ação recomendada.
   - Seção dedicada “✅ Planned Creations (não validar no código)” listando todos os itens do `creation_registry`.
   - Tabela mapa Plano ↔ Código (quando aplicável) e itens de incerteza ou verificações pendentes.
8. **Responder ao usuário** somente após revisar todo o plano. Informe claramente se o plano está alinhado ou detalhe as inconsistências encontradas, citando o `creation_registry` quando justificar ausência de blockers.

## Exemplo Prático
- Plano diz: "Fase 1 – Criar `app/validators/final_delivery_validator.py`" e "Fase 3 – Usar `final_delivery_validator` no pipeline".
- Durante o First Pass, registre `final_delivery_validator` no `creation_registry`.
- No Second Pass, ao ler "Usar final_delivery_validator", priorize o registro e classifique como `ENTREGA` (não validar no código).
- Resultado: nenhum falso positivo; o relatório lista o artefato em “Planned Creations”.

## Boas Práticas
- Priorize achados críticos (P0/P1) que não constam no `creation_registry` antes dos demais.
- Registre e compartilhe o tamanho do `creation_registry` para dar transparência ao usuário.
- Se algo parecer dinâmico/metaprogramado, marque como incerteza em vez de assumir ausência.
- Não rode testes ou comandos destrutivos sem autorização explícita.
- Não modifique arquivos do repositório durante a revisão.
- Em caso de dúvida, reescaneie o plano antes de classificar uma alegação como blocker.

## Resultado Esperado
Uma resposta final que permita ao usuário corrigir o plano antes da implementação, evitando retrabalho. O relatório deve ser autoexplicativo, com links de código e ações concretas para cada divergência.
