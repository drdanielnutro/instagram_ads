Cotas

bookmark_border
Notas da versão
Neste documento, listamos as cotas e os limites do sistema que se aplicam à Document AI.

As cotas têm valores padrão, mas geralmente é possível solicitar ajustes.
Os limites do sistema são valores fixos que não podem ser alterados.
OGoogle Cloud usa cotas para garantir a imparcialidade e reduzir picos no uso e na disponibilidade de recursos. Uma cota restringe a alocação de um recurso doGoogle Cloud para uso do seu projeto do Google Cloud . As cotas se aplicam a vários tipos de recursos, incluindo hardware, software e componentes de rede. Por exemplo, elas podem restringir o número de chamadas de API para um serviço, o número de balanceadores de carga usados simultaneamente pelo projeto ou o número de projetos que podem ser criados. As cotas protegem a comunidade de usuários doGoogle Cloud , impedindo a sobrecarga de serviços. Elas também ajudam você a gerenciar seus próprios recursos do Google Cloud .

O sistema de cotas do Cloud faz o seguinte:

Monitora o consumo de produtos e serviços do Google Cloud .
Restringe o consumo desses recursos.
Possibilita a solicitação de mudanças no valor das cotas e a automatização de ajustes de cotas.
Na maioria dos casos, quando você tenta consumir mais de um recurso do que a cota permite, o sistema bloqueia o acesso ao recurso, e a tarefa que você está tentando executar falha.

As cotas geralmente se aplicam ao nível do projeto do Google Cloud . O uso de um recurso em um projeto não afeta a cota disponível em outro. Em um projeto do Google Cloud , as cotas são compartilhadas entre todos os aplicativos e endereços IP.

Neste documento, listamos as cotas que se aplicam à Document AI.

Níveis de serviço
A Document AI oferece suporte a dois níveis de serviço e cotas associadas para solicitações de processo on-line para versões de processador com tecnologia de IA generativa: níveis provisionado e da melhor maneira possível.

A cota do nível provisionado oferece 120 páginas por minuto para versões básicas do processador, como extrator personalizado v1.4 e v1.5, e 30 páginas por minuto para versões básicas do processador, como extrator personalizado v1.5 Pro.

A cota do nível de melhor esforço fornece 120 para versões de processador básicas, como extrator personalizado v1.4 e v1.5, e 60 para versões de processador Pro, como extrator personalizado v1.5 Pro. Ela só é usada depois que a cota provisionada é esgotada. Isso se aplica a cotas BestEffortOnlineProcessDocumentPagesPerMinutePerProjectUS (métrica best_effort_online_process_document_pages_us) e BestEffortOnlineProcessDocumentPagesPerMinutePerProjectEU (métrica best_effort_online_process_document_pages_eu) no console.

Observações	Extrator personalizado v1.4 (com base no Gemini 2.0 Flash)	Extrator personalizado v1.5 (com base no Gemini 2.5 Flash)	Extrator personalizado v1.5 Pro (com base no Gemini 2.5 Pro)
Provisionado	120	120	30
Melhor esforço	120	120	60
Provisionado no nível da organização	240	240	60
Observação: as cotas provisionadas no nível da organização para extrator personalizado v1.4 e v1.5 se aplicam a ProcessorOnlineRequestsPerMinutePerProjectUS e ProcessorOnlineRequestsPerMinutePerProjectEU.
Se você precisar de mais do que as cotas de melhor esforço listadas, entre em contato com seu representante da equipe de vendas para fazer uma solicitação de aumento de cota (QIR, na sigla em inglês).

Para garantir mais capacidade disponível durante períodos de alto volume de tráfego, leia a seção sobre como fazer uma solicitação de reserva de capacidade.

Não há um contrato de nível de serviço para o nível de melhor esforço.

Lista de cotas
As cotas a seguir se aplicam à Document AI. Essas cotas são aplicadas a cada projeto do console do Google Cloud e compartilhadas com todos os aplicativos e endereços IP que usam esse projeto.

Se quiser processar mais solicitações, envie uma solicitação de cota da Document AI para seu projeto no consoleGoogle Cloud .

Forneça informações sobre suas necessidades específicas e caso de uso na solicitação.

Solicitação de cotas	Valor padrão	Observações
Solicitações por minuto	1.800 por usuário	Ver cota no console Google Cloud
Solicitações de processo on-line por minuto (somente v1beta2)	600 por projeto	Ver cota no console Google Cloud
Solicitações de processo on-line por minuto (EUA)	120 por projeto por tipo de processador	Ver cota no console Google Cloud
Solicitações de processo on-line por minuto (UE)	120 por projeto por tipo de processador	Ver cota no console Google Cloud
Número de páginas de documentos de processo on-line (EUA) por minuto, tipo de processador e versão do modelo (Custom Extractor v1.4 com Gemini 2.0 Flash apenas)	120 páginas por minuto*	Ver cota no console Google Cloud
Número de páginas de documentos de processo on-line (UE) por minuto, tipo de processador e versão do modelo (Custom Extractor v1.4 com Gemini 2.0 Flash apenas)	120 páginas por minuto*	Ver cota no console Google Cloud
Número de páginas de documentos de processo on-line (EUA) por minuto, tipo de processador e versão do modelo (somente Extrator personalizado v1.5 com Gemini 2.5 Flash)	120 páginas por minuto*	Ver cota no console Google Cloud
Número de páginas de documentos de processo on-line (UE) por minuto, tipo de processador e versão do modelo (somente Extrator personalizado v1.5 com Gemini 2.5 Flash)	120 páginas por minuto*	Ver cota no console Google Cloud
Solicitações de processo on-line por minuto (região única)	6 por projeto e por tipo de processador	Ver cota no console Google Cloud
Solicitações simultâneas de processos em lote por projeto e região (EUA)	5 por projeto	Ver cota no console Google Cloud
Solicitações simultâneas de processos em lote por projeto e região (UE)	5 por projeto	Ver cota no console Google Cloud
Solicitações simultâneas de processo em lote por processador (região única)	5 por projeto	Ver cota no console Google Cloud
Número de páginas em processamento ativo (somente v1beta2)	10.000 por projeto	Ver cota no console Google Cloud
Solicitações simultâneas de treinamento de versão do processador (EUA)	1 por projeto	Ver cota no console Google Cloud
Solicitações simultâneas de treinamento de versão do processador (UE)	1 por projeto	Ver cota no console Google Cloud
Solicitações simultâneas de treinamento de versão do processador (região única)	1 por projeto†	Ver cota no console Google Cloud
Versões implantadas de processadores personalizados (EUA)	5 por projeto	Ver cota no console Google Cloud
Versões implantadas de processadores personalizados (UE)	5 por projeto	Ver cota no console Google Cloud
Versões implantadas de processadores personalizados (região única)	5 por projeto	Ver cota no console Google Cloud
Versões implantadas do processador generativo (EUA)	100 por projeto por processador de extração personalizada	Ver cota no console Google Cloud
Versões implantadas do processador generativo (UE)	100 por projeto por processador de extração personalizada	Ver cota no console Google Cloud
Versões implantadas do processador generativo (região única)	100 por projeto por processador de extração personalizada	Ver cota no console Google Cloud
Solicitações simultâneas de importação de documentos (EUA)	3 por projeto	Ver cota no console Google Cloud
Solicitações simultâneas de documentos de importação (UE)	3 por projeto	Ver cota no console Google Cloud
Solicitações simultâneas de importação de documentos (região única)	3 por projeto	Ver cota no console Google Cloud
Solicitações simultâneas de exportação de documentos (EUA)	1 por projeto	Ver cota no console Google Cloud
Solicitações simultâneas de exportação de documentos (UE)	1 por projeto	Ver cota no console Google Cloud
Solicitações simultâneas de exportação de documentos (região única)	1 por projeto	Ver cota no console Google Cloud
* Os pedidos de ajuste de cota ainda não são compatíveis com esta versão.

† Compatível com australia-southeast1 mediante uma solicitação de ajuste de cota.

Fazer uma solicitação de reserva de capacidade
A reserva de capacidade da Document AI oferece capacidade reservada para veicular tráfego de previsão em tempo real e de alto volume durante o período da assinatura, ajudando a atender aos requisitos do contrato de nível de serviço (SLA). Cada unidade corresponde a uma página por minuto adicional além da cota padrão.

A reserva de capacidade é compatível e necessária para aumentar as cotas provisionadas de nível dos modelos de extrator personalizado v1.4 e v1.5, incluindo versões de processador refinadas criadas com base neles.

O preço da reserva de capacidade é de US $300 por página por minuto extra por mês.

Para fazer uma solicitação de reserva de capacidade:

Console
No console do Google Cloud , acesse a página IAM e administrador > Reserva de capacidade:

Reserva de capacidade

Clique no botão 
square
add Criar reserva de capacidade perto do cabeçalho da página. Isso vai abrir um formulário de solicitação de duas páginas.

Preencha a página Configurar com o seguinte:

Preencha um nome para o pedido.
Selecione uma região.
Selecione a versão do processador no menu suspenso.
Escreva o número de páginas extras por minuto necessárias por mês.
Selecione o prazo de assinatura mensal.
Selecione a data e hora de início.
Selecione uma opção de renovação automática no menu suspenso.
Clique em Continuar.

Na segunda página, você vai encontrar um custo estimado por mês. Você precisa digitar CONFIRMAR para validar a compra.

Clique em Confirmar e enviar para confirmar o pedido.

Você poderá conferir o status da solicitação na guia Reserva de capacidade.

Os três status possíveis são:

Inativa: a assinatura ainda não começou.
Ativa: a assinatura está em andamento.
Concluída: a assinatura foi encerrada.
O que considerar antes de comprar uma reserva de capacidade
Para ajudar você a decidir se quer comprar uma reserva de capacidade, considere o seguinte:

Não é possível cancelar o pedido no meio do período.

Sua compra de reserva de capacidade é um compromisso, o que significa que não é possível cancelar o pedido no meio do prazo. No entanto, é possível aumentar o número de GSUs compradas. Se você comprou um compromisso acidentalmente ou se houver um problema com a configuração, entre em contato com o representante da sua conta do Google Cloud para receber ajuda.

É possível renovar sua assinatura automaticamente.

Ao enviar seu pedido, é possível optar, ao final da vigência, pela renovação automática da assinatura ou deixar que ela expire. É possível cancelar o processo de renovação automática. Para cancelar sua assinatura antes da renovação automática, cancele a renovação automática 30 dias antes do início do próximo período.

Você pode configurar as assinaturas mensais para serem renovadas automaticamente a cada mês. Os termos semanais não são compatíveis com a renovação automática.

Observação: todos os pedidos são processados da melhor maneira possível. Para garantir o processamento a tempo, recomendamos que você faça os pedidos o quanto antes.