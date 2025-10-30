Resolver erros de cota

bookmark_border
Erros de cota podem ocorrer por vários motivos, como exceder valores de cota ou não definir a cota em um projeto corretamente. Se você quiser receber um alerta quando ocorrer erros no futuro, crie alertas personalizados para erros de cota específicos, conforme descrito em Configurar alertas de cota.

Cotas de taxa excedentes
As cotas de taxa são redefinidas após um intervalo de tempo predefinido específico de cada serviço. Para mais informações, consulte a documentação de cotas do serviço específico.

Valores de cota excedentes
Se o projeto exceder o valor máximo da cota ao usar um serviço, o Google Cloud retornará um erro com base em como você acessou o serviço:

Se você exceder uma cota com uma solicitação de API, o Google Cloud retornará um código de status HTTP 413 REQUEST ENTITY TOO LARGE. Ao usar a API de streaming legada do BigQuery em um ambiente de produção, você poderá receber um código de status 413 REQUEST ENTITY TOO LARGE se as solicitações HTTP forem maiores que 10 MB. Esse erro também poderá ser exibido se você exceder 300 MB por segundo. Para mais informações, consulte Inserções por streaming.
Se você tiver excedido uma cota com uma solicitação HTTP/REST, o Google Cloud retornará um código de status HTTP 429 TOO MANY REQUESTS.
Se você exceder uma cota do Compute Engine, o Google Cloud normalmente retornará um código de status HTTP 403 QUOTA_EXCEEDED, seja da API, do HTTP/REST ou do gRPC. Se a cota for uma cota de taxa, 403 RATE_LIMIT_EXCEEDED será retornado.
Se você tiver excedido uma cota usando o gRPC, o Google Cloud retornará um erro ResourceExhausted. A forma como esse erro aparece para você depende do serviço.
Se você excedeu uma cota usando um comando da CLI do Google Cloud, a CLI gcloud gera uma mensagem de erro que excede a cota e retorna com o código de saída 1.
Se você recebeu uma mensagem QUOTA_EXCEEDED durante uma distribuição de serviço, consulte a próxima seção.
Exceder valores de cota durante uma distribuição de serviço
Às vezes, o Google Cloud altera os valores de cota padrão para recursos e APIs. Essas mudanças ocorrem gradualmente, o que significa que, durante o lançamento de uma nova cota padrão, o valor da cota que aparece no console do Google Cloud pode não refletir o novo valor da cota disponível para você.

Se o lançamento de uma cota estiver em andamento, talvez você receba a mensagem de erro The future limit is the new default quota that will be available after a service rollout completes. Se essa mensagem de erro for exibida, significa que o valor da cota citado e o valor futuro estão corretos, mesmo que o console do Google Cloud mostre algo diferente.

Para mais informações, consulte os registros de auditoria e procure uma mensagem QUOTA_EXCEEDED.



    "status": {
      ...
      "message": "QUOTA_EXCEEDED",
      "details": [
        {
          ...
          "value": {
            "quotaExceeded": {
              ...
              "futureLimit": FUTUREVALUE
            }
          }
        }
      ]
    },
Para conferir gráficos que mostram o uso atual e o pico de uso, acesse a página Cotas e limites do sistema e clique em monitoringMonitoramento. Talvez seja necessário ir até o fim da tabela.

Se você precisar de mais cota, solicite um ajuste de cota.

Mensagens de erro da API
Se o projeto de cota (também chamado de projeto de faturamento) não estiver definido corretamente, as solicitações de API poderão retornar mensagens de erro semelhantes a esta:

User credentials not supported by this API
API not enabled in the project
No quota project set
Esses e outros erros geralmente podem ser corrigidos ao definir o projeto de cota. Para mais informações, consulte Visão geral do projeto de cota.

Erros da CLI do Google Cloud
Esta seção descreve problemas comuns encontrados ao começar a usar a CLI do Google Cloud (gcloud CLI).

Instalar e inicializar
Para usar a gcloud CLI para cotas do Cloud, instale e inicialize os componentes:

Instale a CLI gcloud.

Se você estiver usando o Cloud Shell, pule esta etapa porque a gcloud CLI vem pré-instalada.

Inicialize a CLI gcloud.

Instale o componente alfa executando o seguinte comando:



gcloud components install alpha
Definir o projeto de cota
Se você não tiver definido seu projeto de cota, os comandos da gcloud CLI poderão retornar um erro como este:



PERMISSION_DENIED: Your application is authenticating by using local Application Default Credentials.
The cloudquotas.googleapis.com API requires a quota project, which is not set by default.
Para resolver esse problema, adicione a flag --billing-project ao comando gcloud CLI para definir explicitamente o projeto de cota ou execute gcloud config set billing/quota_project CURRENT_PROJECT novamente para definir o projeto de cota como o projeto atual.

Para ver mais informações, consulte os seguintes tópicos:

Definir o projeto de cota de maneira programática
Definir o projeto de faturamento na gcloud CLI
Atualizar componentes da gcloud CLI
Se você receber um erro informando que o comando de cotas contém um Invalid choice, é possível que você tenha uma versão mais antiga da gcloud CLI instalada. Atualize a gcloud CLI com o comando a seguir:



gcloud components update
Para mais informações sobre comandos e flags gcloud alpha quotas, consulte a seção de cotas gcloud alpha da referência da CLI do Google Cloud.