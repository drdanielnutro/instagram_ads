## **Documento de Design Técnico (Revisão 2): Sistema Autônomo de Geração de StoryBrand com ADK**

#### **1. Visão Geral e Intenção do Projeto (Inalterado)**

**1.1. Contexto:**
O sistema atual para geração de StoryBrand opera como um assistente conversacional. Ele depende de um fluxo de interação sequencial, onde cada seção do StoryBrand gerada é submetida à validação manual do usuário ("sim/não"). Embora funcional, este modelo apresenta limitações significativas em termos de velocidade, escalabilidade e consistência, pois a qualidade final e o tempo de execução são diretamente dependentes da disponibilidade e do critério do usuário.

**1.2. Missão e Intenção:**
A missão deste projeto é transformar o modelo interativo em um **sistema de pipeline totalmente autônomo**. A intenção é substituir a validação humana externa por um **mecanismo de validação interna, automatizado e orientado por personas de IA**. O objetivo é criar um sistema que, após receber um conjunto mínimo de inputs iniciais, execute todo o processo de escrita, revisão e correção de forma independente, entregando um StoryBrand completo e de alta qualidade, alinhado ao perfil do cliente-alvo.

**1.3. Princípios de Design:**
*   **Autonomia:** O sistema deve operar sem intervenção humana após a configuração inicial.
*   **Qualidade Integrada (Quality Assurance):** A revisão não é uma etapa final, mas um processo contínuo e integrado que ocorre após a geração de cada componente.
*   **Modularidade e Reutilização:** Os agentes devem ser especializados em tarefas específicas (escrever, revisar, corrigir) e projetados para serem reutilizáveis em diferentes estágios do pipeline.
*   **Determinismo e Controle:** O fluxo de controle deve ser explícito e previsível, utilizando os mecanismos do ADK para garantir que a lógica de aprovação/reprovação seja robusta.
*   **Dinamismo e Contextualização:** O comportamento dos agentes, especialmente os de revisão, deve se adaptar dinamicamente com base nos inputs iniciais do usuário (sexo do cliente e contexto de negócio).

---

#### **2. Arquitetura de Alto Nível e Fluxo de Estado (Revisado)**

A arquitetura permanece como uma linha de montagem orquestrada por um `SequentialAgent`. No entanto, adicionamos um agente preparatório para lidar com a reutilização do loop de revisão, conforme a recomendação do Codex.

O fluxo macro revisado é:
1.  **Coleta de Dados:** O `root_agent` coleta os inputs e os salva no `state`.
2.  **Orquestração Sequencial:** O `storybrand_pipeline` (`SequentialAgent`) é ativado.
3.  **Ciclo de Preparação, Escrita e Validação:** O pipeline executa um ciclo repetitivo para cada seção do StoryBrand:
    a. Um **Agente Preparador de Contexto** (`BaseAgent`) configura o `state` para o próximo ciclo de revisão.
    b. Um **Agente Escritor** (`LlmAgent`) gera o conteúdo da seção.
    c. Um **Módulo de Loop de Revisão** (`LoopAgent`) valida o conteúdo gerado.
4.  **Consolidação Final:** Um agente final (`agente_compilador`) reúne todas as seções aprovadas em um único documento.
5.  **Entrega Final:** O sistema entrega o StoryBrand completo.

---

#### **3. Detalhamento dos Componentes e Arquivos (Revisado e Expandido)**

**3.1. O Agente Raiz (`root_agent`)**
*   **Tipo:** `LlmAgent` ou `BaseAgent`.
*   **Função:** Ponto de entrada do sistema. Sua responsabilidade é garantir que o `state` inicial seja populado corretamente antes de iniciar o pipeline principal. Ele coleta os três inputs (`nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`) e os escreve no `state`. Em seguida, delega a execução para o `storybrand_pipeline`. **(Endereça o Ponto de Atenção 1 do Codex)**.

**3.2. O Agente Preparador de Contexto (`preparador_de_contexto`)**
*   **Tipo:** `BaseAgent`.
*   **Função:** Este novo agente é crucial para a reutilização do loop de revisão. Ele é um agente lógico, sem LLM, que é executado antes de cada ciclo de escrita/revisão. Sua tarefa é preparar o `state` com chaves genéricas que o loop de revisão irá consumir.
*   **Lógica (Exemplo para o ciclo "Problema"):**
    1.  Lê `state['storybrand_personagem']`.
    2.  Escreve em `state['contexto_anterior']` o valor de `state['storybrand_personagem']`.
    3.  Escreve em `state['chave_secao_atual']` o valor `"storybrand_problema"`.
    4.  Escreve em `state['nome_secao_atual']` o valor `"Problema"`.
*   **Intenção:** Ao fazer isso, o `agente_revisor` e o `agente_corretor` podem ser programados para ler sempre as mesmas chaves genéricas (`contexto_anterior`, `chave_secao_atual`), tornando o loop verdadeiramente reutilizável. **(Endereça o Ponto de Atenção 3 do Codex)**.

**3.3. O Pipeline Principal (`storybrand_pipeline`)**
*   **Tipo:** `SequentialAgent`.
*   **Função:** Orquestra a sequência completa de geração do StoryBrand, agora incluindo os agentes preparadores.
*   **Estrutura (`sub_agents`) - Totalmente Expandida:**
    1.  `preparador_contexto_personagem`
    2.  `agente_personagem`
    3.  `loop_revisao_generico`
    4.  `preparador_contexto_problema`
    5.  `agente_problema`
    6.  `loop_revisao_generico`
    7.  `preparador_contexto_guia`
    8.  `agente_guia`
    9.  `loop_revisao_generico`
    10. `preparador_contexto_plano`
    11. `agente_plano`
    12. `loop_revisao_generico`
    13. `preparador_contexto_cta`
    14. `agente_cta`
    15. `loop_revisao_generico`
    16. `preparador_contexto_fracasso`
    17. `agente_fracasso`
    18. `loop_revisao_generico`
    19. `preparador_contexto_sucesso`
    20. `agente_sucesso`
    21. `loop_revisao_generico`
    22. `preparador_contexto_identidade`
    23. `agente_identidade`
    24. `loop_revisao_generico`
    25. `agente_compilador`

**3.4. O Módulo de Loop de Revisão (`loop_revisao_generico`)**
*   **Tipo:** `LoopAgent`.
*   **Função:** O mesmo `LoopAgent` é instanciado e reutilizado em cada etapa de validação.
*   **Sub-Agentes:**

    **3.4.1. O Revisor (`agente_revisor`)**
    *   **Tipo:** `LlmAgent`.
    *   **Lógica Dinâmica de Prompt:** A instrução para este agente será construída dinamicamente no código Python antes de sua execução, não apenas trocando o arquivo.
        ```python
        # Lógica de implementação
        sexo = ctx.session.state.get('sexo_cliente_alvo')
        if sexo == 'masculino':
            prompt_base = Path('{prompt_revisor_masculino.txt}').read_text()
        else:
            prompt_base = Path('{prompt_revisor_feminino.txt}').read_text()
        
        # Injeta o contexto atual no prompt base
        chave_secao = ctx.session.state.get('chave_secao_atual')
        texto_secao = ctx.session.state.get(chave_secao)
        # ... e assim por diante
        
        agente_revisor.instruction = prompt_formatado
        ```
        Esta abordagem garante que o prompt correto seja usado a cada chamada. **(Endereça o Ponto de Atenção 2 do Codex)**.
    *   **Output Estruturado:** A saída permanece um JSON com `grade` e `comment`, escrito em `state['revisao_atual']`.

    **3.4.2. O Checador de Aprovação (`checador_de_aprovacao`)**
    *   **Tipo:** `BaseAgent`.
    *   **Função:** Inalterada. Lê `state['revisao_atual']['grade']` e dispara `escalate=True` se for `"pass"`.

    **3.4.3. O Corretor (`agente_corretor`)**
    *   **Tipo:** `LlmAgent`.
    *   **Inputs:** Lê as chaves genéricas preparadas pelo `preparador_de_contexto`:
        *   Texto reprovado de `state[state['chave_secao_atual']]`.
        *   Feedback de `state['revisao_atual']['comment']`.
    *   **Output:** Sobrescreve o texto na chave dinâmica `state[state['chave_secao_atual']]`.

**3.5. O Agente Compilador (`agente_compilador`)**
*   **Tipo:** `BaseAgent` ou `LlmAgent`.
*   **Função:** Este agente é executado uma única vez, no final do pipeline. Sua tarefa é ler todas as chaves de seção individuais do `state` (`storybrand_personagem`, `storybrand_problema`, etc.) e concatená-las em um único documento de texto formatado.
*   **Output:** Escreve o resultado final em `state['storybrand_completo']`. **(Endereça o Ponto de Atenção 4 do Codex)**.

---

#### **4. Gerenciamento de Estado e Fluxo de Chaves (Detalhado)**

O `state` é o coração do sistema. O fluxo de chaves será meticulosamente gerenciado:

1.  **Inicial:** `state` contém `{ 'sexo_cliente_alvo', 'nome_empresa', 'o_que_a_empresa_faz' }`.
2.  **Ciclo "Personagem":**
    *   `preparador_contexto_personagem` adiciona: `{ 'chave_secao_atual': 'storybrand_personagem', 'nome_secao_atual': 'Personagem', 'contexto_anterior': '' }`.
    *   `agente_personagem` adiciona: `{ 'storybrand_personagem': 'Texto do personagem...' }`.
    *   `loop_revisao_generico` opera usando as chaves genéricas e, se necessário, o `agente_corretor` sobrescreve `state['storybrand_personagem']`.
3.  **Ciclo "Problema":**
    *   `preparador_contexto_problema` atualiza: `{ 'chave_secao_atual': 'storybrand_problema', 'nome_secao_atual': 'Problema', 'contexto_anterior': state['storybrand_personagem'] }`.
    *   `agente_problema` adiciona: `{ 'storybrand_problema': 'Texto do problema...' }`.
    *   `loop_revisao_generico` agora opera sobre a seção "Problema", usando o mesmo mecanismo.
4.  **... (O processo continua)**
5.  **Final:**
    *   `agente_compilador` lê todas as chaves `storybrand_*` e cria `state['storybrand_completo']`.

Este design revisado e expandido aborda diretamente as complexidades de implementação apontadas pelo Codex, resultando em um plano mais robusto, detalhado e alinhado com as melhores práticas do framework ADK.