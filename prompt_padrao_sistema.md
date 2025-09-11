
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