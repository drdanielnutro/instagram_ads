# Agente Gerador de Código Flutter

## 📋 Visão Geral

Este diretório contém um agente de IA avançado, construído com o Google Agent Development Kit (ADK), projetado para automatizar o desenvolvimento de features completas em um aplicativo Flutter.

O agente segue um pipeline robusto de múltiplos passos para garantir a qualidade e a consistência do código gerado:
1.  **Análise de Contexto**: Sintetiza documentos de referência (especificação técnica, contexto de API, UX) para entender os requisitos da feature.
2.  **Planejamento Detalhado**: Cria um plano de implementação sequencial, quebrando a feature em tarefas atômicas e gerenciáveis.
3.  **Geração de Código**: Escreve código Dart/Flutter para cada tarefa, seguindo as melhores práticas e os padrões do projeto (Freezed, Riverpod, etc.).
4.  **Revisão e Refinamento**: Submete o código gerado a um agente crítico de revisão, que pode solicitar refinamentos para garantir a qualidade.
5.  **Montagem Final**: Agrupa todo o código aprovado e gera uma documentação completa da feature.

## ✨ Features

- **Geração de Código Automatizada**: Cria models, providers, widgets e services a partir de uma simples descrição da feature.
- **Orquestração por Pipeline**: Utiliza agentes sequenciais e de loop para um fluxo de trabalho determinístico e confiável.
- **Validação de Qualidade**: Inclui etapas de revisão de plano e de código para garantir que o resultado final seja de alta qualidade.
- **Reporting de Status em Tempo Real**: Fornece feedback visual no chat sobre o progresso da geração de código, com barras de progresso e estimativas de tempo, graças ao `EnhancedStatusReporter`.

## 🚀 Como Usar o Agente

O agente é projetado para ser interativo. O fluxo de trabalho principal é iniciado ao fornecer uma descrição da feature a ser implementada.

### Fluxo de Interação

1.  **Forneça o Contexto (Documentos + Feature)**: Para obter os melhores resultados, forneça os documentos de referência do seu projeto junto com a descrição da feature. O agente pode funcionar sem os documentos, mas o resultado será muito mais preciso se eles forem fornecidos.

2.  **Aprove o Plano**: O agente irá analisar sua solicitação e apresentar um plano de implementação detalhado. Você deve aprovar este plano para que a geração de código comece.

3.  **Acompanhe o Progresso**: Graças ao novo sistema de status, você verá atualizações em tempo real à medida que o agente trabalha em cada tarefa.

4.  **Receba o Código Final**: Ao final do processo, o agente entregará todo o código gerado e a documentação associada.

### Exemplo de Prompt de Entrada

Use o formato a seguir para iniciar o agente. As tags `[nome_do_documento]` e `[feature_snippet]` ajudam o agente a parsear a sua entrada corretamente.

```
Aqui estão os documentos de referência para o meu projeto e a feature que eu gostaria de implementar.

[especificacao_tecnica_da_ui]
O aplicativo usa a arquitetura MVVM com Riverpod. Todos os novos widgets devem ser `ConsumerWidget` e o estado deve ser gerenciado por `StateNotifierProvider`. As dependências principais são `flutter_riverpod`, `freezed`, e `json_serializable`.
[/especificacao_tecnica_da_ui]

[contexto_api]
O endpoint para autenticação é `POST /api/v1/auth/login`. Ele espera um JSON com `email` e `password` e retorna um `access_token`. O token deve ser enviado no header `Authorization: Bearer <token>` para todas as outras chamadas.
[/contexto_api]

[fonte_da_verdade_ux]
A tela de login deve ter dois campos de texto para email e senha, e um botão "Entrar". Deve haver um indicador de carregamento enquanto a chamada de API está em andamento. Em caso de erro, uma mensagem deve ser exibida abaixo do botão.
[/fonte_da_verdade_ux]

[feature_snippet]
Implemente a tela de login completa, incluindo o modelo de estado, o provider de autenticação que chama a API e o widget da UI com tratamento de estados de loading, success e error.
[/feature_snippet]
```

Com base nesta entrada, o agente terá todo o contexto necessário para gerar uma feature completa e de alta qualidade.
