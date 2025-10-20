# Validação Técnica do Erro RESOURCE_EXHAUSTED em Vertex AI (Gemini)

## Introdução

### Propósito do Relatório
Este documento fornece uma validação técnica definitiva das hipóteses relacionadas ao erro `429 RESOURCE_EXHAUSTED`, ocorrido em 14 de outubro de 2025, durante a utilização do modelo `gemini-2.5-flash` na região `us-central1`. O objetivo é analisar cada afirmação técnica, confirmar ou refutar sua validade com base em documentação oficial e, por fim, apresentar um diagnóstico conclusivo da causa raiz do incidente, acompanhado de recomendações estratégicas para mitigação, remediação e monitoramento proativo.

### Metodologia
A análise apresentada é fundamentada exclusivamente em uma revisão abrangente da documentação oficial da Google Cloud, referências de API, notas de lançamento e artigos de suporte técnico. Cada uma das oito asserções propostas será sistematicamente avaliada, com conclusões suportadas por citações diretas às fontes documentais. A análise dos logs fornecidos é um componente central para o diagnóstico final.

### Resumo Executivo das Conclusões
A análise aprofundada indica que a causa primária do erro não foi uma violação de quotas específicas do projeto (como RPM ou TPM) nem a ultrapassagem do limite da janela de contexto do modelo. A evidência aponta de forma conclusiva para uma saturação temporária do pool regional de recursos gerenciado pelo sistema de **Dynamic Shared Quota (DSQ)**. Este mecanismo, utilizado pelos modelos Gemini mais recentes, aloca capacidade de forma dinâmica entre todos os usuários pay-as-you-go, e um erro `429` sinaliza um pico de demanda agregada na região que excede a capacidade disponível momentaneamente. Consequentemente, as medidas corretivas devem focar na implementação de padrões de resiliência robustos no lado do cliente, como *retry* com *backoff* exponencial, em vez de tentativas de aumento de quota no servidor.

## Parte I: Validação Técnica das Asserções

Esta seção avalia sistematicamente cada uma das afirmações técnicas (A–H), fornecendo um veredito, uma análise detalhada baseada em documentação oficial e as respectivas citações.

### A. Múltiplas dimensões de quota podem causar o erro RESOURCE_EXHAUSTED

**✅ Confirmado.**

O erro `RESOURCE_EXHAUSTED` (código HTTP 429) é um código de status genérico que pode ser acionado por violações em múltiplas e distintas dimensões de quotas e limites. A documentação oficial confirma que a gestão de recursos na Vertex AI é multifacetada e não se restringe a uma única métrica.¹

As principais dimensões que podem levar a este erro incluem:

*   **Quotas Baseadas em Taxa (Rate-Based Quotas):** Esta é a categoria mais comum de limitação e abrange métricas como Requisições por Minuto (RPM) e Tokens por Minuto (TPM). A documentação da API Gemini e serviços associados, como o Firebase AI Logic, lista explicitamente RPM, Requisições por Dia (RPD), TPM e Tokens por Dia (TPD) como as quatro dimensões primárias de medição de quotas.² Exceder qualquer um desses limites resultará em um erro `429`.
*   **Limites por Requisição (Per-Request Limits):** Uma requisição pode falhar não pela taxa de envio, mas pelo seu tamanho individual. Existem limites rígidos para o número de tokens de entrada (janela de contexto) e para o tamanho total do payload. Para o modelo `gemini-2.5-flash`, esses limites são de 1.048.576 tokens de entrada e 500 MB de payload total.⁴ Embora a violação do limite de tokens possa, em alguns casos, retornar um erro `400 INVALID_ARGUMENT`, um `429` também é uma resposta possível dependendo do contexto da sobrecarga gerada.⁵
*   **Limites de Concorrência e Jobs:** Para serviços específicos dentro da Vertex AI, como AutoML ou jobs de treinamento e inferência em lote, existem limites explícitos sobre o número de operações concorrentes (por exemplo, 5 jobs de treinamento simultâneos para AutoML).¹ Embora menos aplicável à chamada síncrona `generateContent` do caso em questão, este princípio demonstra que a exaustão de recursos pode ser baseada em concorrência.
*   **Saturação do Pool de Dynamic Shared Quota (DSQ):** Esta é uma dimensão crítica e distinta das demais. A documentação sobre DSQ esclarece que um erro `429` neste contexto não significa que o projeto do usuário excedeu uma quota própria. Em vez disso, indica que o pool compartilhado de recursos computacionais para um determinado modelo em uma região específica está temporariamente saturado devido à alta demanda agregada de todos os clientes.⁶

A existência dessas múltiplas dimensões implica que o monitoramento de uma única métrica, como RPM, é inadequado para um diagnóstico completo. Um sistema pode estar operando bem abaixo de sua quota de RPM, mas ser estrangulado por exceder o limite de TPM com poucas requisições de grande porte, ou por encontrar um pool de DSQ congestionado. Uma estratégia de observabilidade robusta deve, portanto, rastrear a taxa de requisições, o tamanho (em tokens) de cada requisição e a frequência dos próprios erros `429` para inferir a causa mais provável.

### B. Dynamic Shared Quota (DSQ) nos modelos Gemini 2.x

**✅ Confirmado.**

A afirmação de que os modelos da família Gemini 2.x utilizam Dynamic Shared Quota (DSQ) e que um erro `429` nesses modelos indica saturação do pool global, e não do projeto, está correta e é fundamental para a análise deste incidente.

A documentação oficial sobre DSQ descreve o sistema como um mecanismo que fornece acesso a um "grande pool compartilhado de recursos, alocado dinamicamente com base na disponibilidade em tempo real... e na demanda em tempo real de todos os clientes".⁶ O propósito explícito deste sistema é eliminar a necessidade de os usuários pay-as-you-go gerenciarem quotas e submeterem Pedidos de Aumento de Quota (QIRs).

A aplicabilidade aos modelos Gemini 2.x é confirmada diretamente. A página de documentação do modelo `gemini-2.5-flash` lista "Dynamic shared quota" como um dos tipos de uso suportados.⁴ A documentação geral do DSQ também enumera vários modelos Gemini 2.5 e 2.0 como compatíveis.⁷

A interpretação do erro `429` sob o DSQ é inequívoca. A documentação afirma: "encontrar um erro 'resource exhausted' 429... com DSQ, não é o caso [de que você está atingindo um limite de quota]. Esses erros indicam que o pool geral de recursos compartilhados... está passando por uma demanda extremamente alta de muitos usuários simultaneamente".⁶ A analogia usada é a de um trem lotado em horário de pico: o problema é uma contenção temporária por um recurso compartilhado, não um limite fixo imposto ao seu projeto.

Essa mudança para o DSQ representa uma alteração de paradigma na gestão de recursos para serviços de IA generativa em nuvem pública. Ela prioriza a maximização da utilização agregada do hardware e a capacidade de oferecer picos de performance (burst) em detrimento da garantia de uma vazão fixa e previsível para clientes individuais no modelo pay-as-you-go. A consequência direta para a arquitetura de aplicações é a necessidade de projetá-las para resiliência e degradação graciosa. O nível de serviço torna-se probabilístico, não determinístico. A alternativa para capacidade garantida é o serviço "Provisioned Throughput", que possui um custo significativamente maior.⁵

### C. Quotas para modelos não-DSQ (ex: Text-Bison, AutoML)

**✅ Confirmado.**

A distinção entre o modelo DSQ e o modelo de quotas fixas por projeto é correta e relevante. Modelos mais antigos e outros serviços dentro da plataforma Vertex AI, como AutoML, operam sob o paradigma tradicional de quotas.

A página principal de quotas da Vertex AI detalha inúmeras quotas por projeto para serviços como AutoML (por exemplo, "Concurrent training jobs: 5") e para modelos treinados de forma customizada ("Online inference requests: 30,000 per minute").¹ Estes são limites clássicos, com escopo definido por projeto, que podem ser monitorados em painéis de controle.

Para essas quotas fixas, o procedimento padrão para lidar com a exaustão de recursos é submeter um Pedido de Aumento de Quota (QIR) através do Console do Google Cloud (IAM & Admin -> Quotas).¹ Este processo é válido e necessário quando a carga de trabalho previsível de um projeto excede os limites padrão.

A documentação do DSQ contrasta explicitamente seu funcionamento com o modelo tradicional, onde "você geralmente precisa submeter um pedido de aumento de quota e esperar pela aprovação".¹⁰ Para modelos baseados em DSQ, como o `gemini-2.5-flash`, submeter um QIR é um procedimento ineficaz, pois não existe um limite por projeto a ser aumentado.⁶

A coexistência de ambos os modelos de quota dentro da mesma plataforma (Vertex AI) pode ser uma fonte significativa de confusão. A resposta correta a um erro `429` depende inteiramente do serviço e da versão do modelo em uso. Um engenheiro acostumado a resolver erros `429` com um QIR para o serviço de AutoML falhará se aplicar a mesma lógica a um modelo Gemini 2.5. Portanto, é crucial que as equipes de desenvolvimento documentem e compreendam o modelo de quota específico para cada serviço da Vertex AI que utilizam. O nome do modelo é a informação chave para determinar o caminho correto de diagnóstico e remediação.

### D. Ferramentas de diagnóstico para erros 429 ambíguos

**✅ Confirmado.**

A afirmação de que o erro `429` é ambíguo por design e requer o uso de ferramentas específicas para um diagnóstico correto é precisa.

*   **Cloud Monitoring:** Esta é a principal ferramenta de observabilidade. A métrica chave para diagnóstico não é a contagem de tokens (`aiplatform.googleapis.com/publisher/online_serving/token_count`), mas sim o monitoramento dos códigos de resposta da API. É possível criar métricas baseadas em logs ou utilizar as métricas padrão da API para visualizar a contagem de respostas `429` para o serviço `aiplatform.googleapis.com`. Correlacionar picos de erros `429` com os padrões de tráfego da própria aplicação pode ajudar a distinguir entre atingir um limite de taxa e sofrer com a contenção do DSQ.¹¹
*   **Comando `gcloud alpha quotas list`:** Este comando é útil para inspecionar quotas fixas e alocadas por projeto. No entanto, para serviços baseados em DSQ, ele não exibirá limites relevantes, o que pode ser enganoso. Sua utilidade é, principalmente, para descartar uma violação de quota fixa em serviços aplicáveis.
*   **API `countTokens`:** Esta API é essencial para diagnosticar problemas relacionados ao limite da janela de contexto, não a limites de taxa ou DSQ. Ela permite verificar o tamanho de um prompt antes de enviá-lo, confirmando se um erro (mais provavelmente um `400`, mas potencialmente um `429`) é devido a um payload excessivamente grande.¹²

A ambiguidade do erro `429` no mundo DSQ transfere o ônus da observabilidade do painel de quotas do provedor de nuvem para o monitoramento no nível da aplicação do usuário. Não é mais possível confiar em um simples gráfico de "percentual da quota utilizada". No modelo DSQ, não existe "sua quota". O Google Cloud não pode fornecer um painel que diga "O pool regional está com 98% de capacidade", pois isso exporia dados sensíveis de uso de múltiplos clientes e seria extremamente volátil. O único sinal que o usuário recebe é o próprio erro `429`. A inferência da causa deve ser feita pelo usuário: se os erros `429` aparecem durante um pico massivo de tráfego auto-iniciado, a causa pode ser um limite nocional de RPM/TPM. Se eles aparecem aleatoriamente durante um tráfego baixo e estável, a causa é quase certamente a contenção do DSQ provocada por outros inquilinos. A telemetria interna da aplicação, que registra taxas de requisição, tamanhos de prompt e a frequência dos erros `429`, torna-se mais valiosa do que os painéis de quota da plataforma.

### E. Validade do uso da API CountTokens para gerenciamento da janela de contexto

**✅ Confirmado.**

A recomendação de usar a API `CountTokens` (ou seu equivalente no SDK) para medir o tamanho do prompt é uma prática recomendada e documentada oficialmente pela Google Cloud.

A documentação afirma explicitamente: "Use a API `CountTokens` para evitar que as requisições excedam a janela de contexto do modelo e para estimar custos potenciais".¹² A API permite que um cliente envie o payload exato (`contents`) que seria usado em uma chamada `generateContent` e receba em troca o `total_tokens` e `total_billable_characters`.¹³ Isso fornece uma verificação prévia precisa e de baixo custo, já que as chamadas para a API `countTokens` não são cobradas e possuem uma quota alta de 3000 RPM.¹⁴

Recentemente, a documentação passou a recomendar o uso do tokenizador integrado do SDK da Vertex AI para Python, pois ele realiza a contagem localmente, evitando uma chamada de rede e sendo, portanto, mais eficiente. No entanto, o princípio fundamental de verificar o tamanho do prompt antes do envio permanece o mesmo.¹³

A API `countTokens` é mais do que uma ferramenta de validação; é um componente crítico para construir aplicações de LLM robustas, eficientes e com custo controlado, especialmente aquelas que lidam com conteúdo de prompt dinâmico ou gerado pelo usuário. Seu uso permite não apenas evitar falhas por exceder o limite de contexto, mas também implementar lógicas de gerenciamento de custos e estratégias de gerenciamento de contexto, como truncamento ou sumarização de históricos de conversas para garantir que caibam na janela do modelo. A implementação de uma verificação prévia com `countTokens` deve ser considerada uma etapa obrigatória no ciclo de vida da requisição para qualquer aplicação em produção onde o tamanho do prompt não seja fixo e previsível.

### F. Limites documentados para os modelos Gemini 2.x

**✅ Confirmado.**

Os limites citados no prompt para os modelos Gemini 2.x estão corretos e em conformidade com a documentação oficial mais recente.

*   **Modelo:** `gemini-2.5-flash`
*   **Limite de Tokens de Entrada:** 1.048.576 tokens.⁴
*   **Limite de Tokens de Saída:** 65.536 tokens (documentado como 65.535 ou 65.536, uma diferença insignificante).⁴
*   **Tamanho do Payload:** 500 MB no total por requisição.⁴

Esses valores são consistentemente reportados nas páginas do Model Garden da Vertex AI para o `gemini-2.5-flash` e na documentação técnica detalhada do modelo.⁴

O tamanho massivo desses limites (mais de 1 milhão de tokens) torna plausível que uma aplicação que concatena dados progressivamente possa, eventualmente, atingi-los. No entanto, também significa que, para uma única transação de rotina, exceder o limite é altamente improvável. O erro é mais provável de ocorrer em casos extremos envolvendo inputs muito grandes ou processos de longa duração com estado acumulado. Uma análise simples do prompt que falhou (aproximadamente 86.531 caracteres, que se traduz em cerca de 22.000 tokens) mostra que ele estava muito longe do limite de ~1M de tokens. Isso permite rebaixar significativamente a hipótese de "janela de contexto excedida" como a causa deste incidente específico. Contudo, o mecanismo de crescimento linear do prompt continua sendo uma preocupação válida para a estabilidade a longo prazo da aplicação.

### G. Coerência da hipótese de crescimento progressivo do prompt

**✅ Confirmado.**

A hipótese de que a concatenação de seções JSON aprovadas em um prompt pode levar à ultrapassagem da janela de contexto é tecnicamente sólida. Este é um padrão de arquitetura comum e um modo de falha conhecido em aplicações de LLM com estado.

O mecanismo descrito, onde cada seção completa é serializada para JSON e adicionada ao contexto da próxima chamada, cria uma "memória" ou "estado" crescente dentro do prompt. Esse crescimento é linear em relação ao número de seções concluídas. Como observado nos logs, após 11 seções, o contexto já havia crescido para aproximadamente 8.000 tokens, um tamanho não trivial. Sem uma estratégia de sumarização ou truncamento, esse crescimento linear colidirá inevitavelmente com o limite fixo da janela de contexto do modelo, não importa quão grande seja esse limite.

Essa arquitetura revela uma tensão clássica no design de agentes e aplicações com estado: a necessidade de um contexto completo versus as restrições físicas e de custo da janela de contexto. A estratégia de "apenas anexar" (*append-only*) é simples de implementar, mas não é escalável. Uma aplicação madura deve implementar uma estratégia de gerenciamento de contexto mais sofisticada, como uma janela deslizante (incluindo apenas as N seções mais recentes), sumarização periódica do contexto ou o uso de uma memória vetorial (RAG) para recuperar apenas os trechos mais relevantes do histórico. A abordagem atual da aplicação é uma bomba-relógio, mesmo que não tenha sido a causa deste incidente específico.

### H. retry/backoff exponencial como resposta recomendada para saturação de DSQ

**✅ Confirmado.**

A documentação oficial da Google Cloud recomenda repetida e explicitamente a implementação de uma estratégia de *retry* com *backoff* exponencial para lidar com erros `429`, especialmente aqueles que surgem de condições transitórias como a saturação do DSQ.

A página de documentação sobre como lidar com erros `429` para o framework pay-as-you-go lista "Implementar uma estratégia de retry usando backoff exponencial truncado" como uma das soluções primárias.⁷ Outra página sobre erros de API também recomenda tentar novamente com um backoff exponencial.⁵

Essa estratégia é ideal para erros de DSQ porque eles são, por natureza, transitórios, refletindo um pico temporário de demanda no pool compartilhado. Um *backoff* exponencial aguarda por períodos progressivamente mais longos, dando tempo para que o pool se descongestione. A adição de "*jitter*" (um elemento de aleatoriedade no tempo de espera), que é uma prática recomendada, evita que uma manada de clientes tente novamente em sincronia, o que poderia perpetuar a sobrecarga.¹⁸

Como estabelecido anteriormente, um Pedido de Aumento de Quota (QIR) é a ferramenta errada para um erro `429` relacionado ao DSQ. A documentação confirma isso ao apresentar o *backoff* e os QIRs como soluções para modelos de quota fundamentalmente diferentes.⁷ O Google fornece exemplos de código e tutoriais que demonstram como implementar essa lógica, por exemplo, usando a biblioteca `tenacity` em Python.¹⁰

Um forte indício que corrobora a ocorrência de um erro de DSQ é a ausência do cabeçalho `Retry-After` nas respostas de erro recebidas. Um sistema determinístico, como um limitador de taxa fixo, pode informar com precisão quando tentar novamente. Um sistema probabilístico e competitivo como o DSQ não pode fazer tal garantia, pois o servidor não tem como prever quando a contenção regional diminuirá. Portanto, a API retorna um `429` simples, sinalizando "Estou ocupado, descubra você mesmo quando tentar novamente". Isso coloca o ônus no cliente para implementar uma estratégia de *retry* sofisticada, paciente e aleatória. O *wrapper* de *retry* atual, que falhou após 5 tentativas, pode não ser paciente o suficiente para um evento significativo de contenção de DSQ.

## Parte II: Síntese Executiva e Recomendações Estratégicas

### Diagnóstico Primário do Incidente de 14 de Outubro

A análise das evidências indica, com alto grau de confiança, que o erro `429 RESOURCE_EXHAUSTED` foi causado por uma saturação temporária de recursos no pool regional de **Dynamic Shared Quota (DSQ)** do `us-central1` para o modelo `gemini-2.5-flash`.

As evidências que suportam este diagnóstico são:

*   **Tipo de Modelo:** O `gemini-2.5-flash` é confirmado como um modelo que utiliza o mecanismo DSQ.⁴
*   **Análise da Janela de Contexto:** Uma estimativa conservadora do tamanho do prompt que falhou (~22.000 tokens) representa menos de 3% do limite de entrada do modelo (~1.000.000 tokens). Portanto, a ultrapassagem da janela de contexto é descartada como a causa imediata.
*   **Ambiguidade da Mensagem de Erro:** A mensagem genérica `RESOURCE_EXHAUSTED`, juntamente com a ausência do cabeçalho `Retry-After`, é característica de um evento de contenção de DSQ, em oposição a uma violação de um limite de taxa simples e determinístico.
*   **Interpretação das Mensagens de Log:**
    *   A mensagem `Span storybrand_fallback_section_writer exceeds limit;` é interpretada como um sintoma, não a causa. Provavelmente, é um erro no nível da aplicação, gerado por uma biblioteca de tracing ou de gerenciamento de concorrência, que foi acionado depois que a API do Google retornou o `429`.
    *   A mensagem `AFC is enabled with max remote calls: 10 20` confirma o uso de um framework de agente (Automatic Function Calling). Isso implica que uma única operação lógica na aplicação pode gerar uma rajada de múltiplas chamadas de API em rápida sucessão, tornando a aplicação altamente suscetível ao estrangulamento por DSQ durante períodos de contenção regional.

A tabela a seguir resume as validações técnicas e suas implicações estratégicas.

| Asserção | Status da Validação | Conclusão Chave | Implicação Estratégica |
| :--- | :--- | :--- | :--- |
| **A. Múltiplas dimensões de quota** | ✅ Confirmado | O erro 429 é multifacetado, cobrindo taxas, tamanhos e concorrência. | O diagnóstico requer uma visão holística; monitorar apenas RPM é insuficiente. |
| **B. Dynamic Shared Quota (DSQ)** | ✅ Confirmado | `gemini-2.5-flash` usa DSQ; 429 indica saturação do pool regional. | Focar na resiliência do cliente (retry), não em aumentos de quota no servidor. |
| **C. Cotas fixas (não-DSQ)** | ✅ Confirmado | Modelos mais antigos/outros usam quotas por projeto onde QIRs são válidos. | O modelo em uso dita a estratégia de resposta correta para um erro 429. |
| **D. Ambiguidade do erro 429** | ✅ Confirmado | O mesmo código de erro é usado para diferentes causas raiz (DSQ vs. fixa). | O diagnóstico eficaz depende da telemetria no nível da aplicação, não apenas dos consoles da nuvem. |
| **E. Uso da API CountTokens** | ✅ Confirmado | É a ferramenta oficial para pré-validar a contagem de tokens do prompt. | Implementar como uma verificação prévia obrigatória para prompts dinâmicos ou grandes. |
| **F. Limites do Gemini 2.x** | ✅ Confirmado | Os limites são muito altos (~1M tokens de entrada, 500 MB de payload). | Exceder a janela de contexto é um risco real, mas latente, não a causa deste incidente. |
| **G. Hipótese de crescimento do prompt** | ✅ Confirmado | O mecanismo de contexto "append-only" é um padrão tecnicamente válido, mas não escalável. | A aplicação deve ter salvaguardas (ex: sumarização) contra o crescimento ilimitado do contexto. |
| **H. retry/backoff para DSQ** | ✅ Confirmado | Backoff exponencial com jitter é a estratégia de tratamento oficialmente recomendada. | O wrapper de retry existente deve ser revisado e aprimorado para maior paciência e aleatoriedade. |

### Estratégias de Mitigação e Remediação Recomendadas

#### Ação Imediata - Aprimorar a Lógica de Retry

*   **Modificar o wrapper de retry existente:** A implementação atual, que falhou após 5 tentativas, é insuficiente para lidar com eventos de contenção de DSQ.
*   **Implementar Backoff Exponencial Truncado com Jitter:** Utilizar uma biblioteca padrão da indústria, como a `tenacity` em Python.¹⁹ Configurar a estratégia com um número maior de tentativas máximas (ex: 10-15) e um tempo máximo de backoff mais longo (ex: 60-120 segundos). O "jitter" (aleatoriedade) é crucial para evitar que múltiplos clientes tentem novamente de forma sincronizada.¹⁸

#### Ação de Curto Prazo - Implementar Gerenciamento Proativo de Contexto

*   **Integrar `countTokens`:** Antes de cada chamada para `generateContent`, usar o tokenizador integrado do SDK da Vertex AI (`get_tokenizer_for_model`) para contar os tokens no prompt construído.¹³
*   **Estabelecer uma Margem de Segurança:** Registrar um aviso (warning) quando o tamanho do prompt exceder 75% do limite do modelo e falhar a requisição de forma graciosa (ou acionar uma estratégia de corte de contexto) se exceder 95%. Isso previne falhas futuras devido ao problema de "crescimento ilimitado".

#### Ação de Médio Prazo - Re-arquitetar o Manuseio de Contexto

*   **Substituir a Estratégia "Append-Only":** Para o contexto das `approved_sections`, implementar uma abordagem mais escalável.
    *   **Opção 1 (Simples):** Uma janela deslizante que inclui apenas as N seções mais recentes.
    *   **Opção 2 (Melhor):** Um agente de sumarização que condensa periodicamente as seções aprovadas em um resumo conciso, que é então usado como contexto.
    *   **Opção 3 (Avançada):** Uma abordagem baseada em RAG (Retrieval-Augmented Generation) usando um banco de dados vetorial para as seções aprovadas, recuperando apenas os trechos mais relevantes para a tarefa atual.

### Plano de Instrumentação e Monitoramento Proativo

#### Aprimorar o Logging no Nível da Aplicação

*   Registrar a contagem de tokens para cada requisição enviada à Vertex AI.
*   Quando um erro `429` ocorrer, registrar o tempo atual, o atraso de backoff que está sendo aplicado e o número da tentativa de retry.
*   Para chamadas de agente, atribuir um ID de rastreamento (trace ID) único à operação pai e registrá-lo em cada chamada de LLM filha para entender o fan-out de requisições.

#### Desenvolver um Painel de Controle no Cloud Monitoring

*   **Gráfico 1: Taxa de Erros da API:** Criar um gráfico de métricas para `aiplatform.googleapis.com/request_count`, agrupado por `response_code`. Visualizar especificamente a contagem de erros `429`.
*   **Gráfico 2: Vazão de Tokens:** Criar um gráfico para a métrica `aiplatform.googleapis.com/publisher/online_serving/token_count`, visualizando tanto `input_tokens` quanto `output_tokens`.
*   **Sobrepor e Correlacionar:** Posicionar esses gráficos lado a lado. Isso permitirá correlacionar visualmente os picos de erros `429` com os padrões de tráfego e uso de tokens da própria aplicação.

#### Configurar Alertas Proativos

*   Criar uma política de alertas no Cloud Monitoring que seja acionada se a taxa de erros `429` exceder um limiar definido (ex: >1% do total de requisições em uma janela de 5 minutos).
*   A notificação de alerta deve ser enviada para o canal de resposta a incidentes da equipe de engenharia (ex: Slack, PagerDuty) e deve incluir um link para o painel de diagnóstico. Isso permitirá uma resposta rápida a futuros eventos de contenção de DSQ.