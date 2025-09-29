# Guia: Provisionar alertas para métricas StoryBrand com Terraform

Este documento descreve, de ponta a ponta, como criar políticas de alerta no Google Cloud Monitoring para as métricas expostas pelo agente (por exemplo `storybrand.vertex429.count` e `storybrand.delivery_failure.count`). Siga os passos na ordem indicada.

---

## 1. Pré-requisitos

1. **Ferramentas instaladas**  
   - Terraform ≥ 1.5 (`terraform -version`).  
   - Google Cloud SDK (`gcloud -v`).

2. **Autenticação**  
   - Entre com a conta que tem permissão para criar políticas de alerta:  
     ```bash
     gcloud auth application-default login
     ```
   - Verifique o projeto padrão (ou defina explicitamente o que será usado pelo Terraform):  
     ```bash
     gcloud config set project <ID_DO_PROJETO>
     export GOOGLE_CLOUD_PROJECT=<ID_DO_PROJETO>
     ```

3. **Estado do Terraform**  
   - Se o diretório `deployment/terraform/` já usa backend remoto (GCS, Terraform Cloud etc.), confirme as instruções internas antes de continuar. Caso contrário, o backend local padrão (`terraform.tfstate`) será utilizado.

---

## 2. Criar o arquivo `deployment/terraform/monitoring.tf`

1. No repositório raiz, abra o arquivo (crie se não existir) `deployment/terraform/monitoring.tf`.
2. Adicione o conteúdo abaixo, ajustando os comentários marcados como `TODO` após confirmar o nome exato das métricas no Metrics Explorer (procure por “storybrand.vertex429.count” e “storybrand.delivery_failure.count”).

```hcl
# deployment/terraform/monitoring.tf

locals {
  project_id = var.project_id != "" ? var.project_id : var.default_project_id
}

# Variável auxiliar (adicione em variables.tf se ainda não existir)
# variable "project_id" {
#   description = "Project ID onde as políticas serão criadas"
#   type        = string
#   default     = ""
# }

resource "google_monitoring_alert_policy" "vertex429_burst" {
  display_name = "StoryBrand – Erros 429 (Vertex AI)"
  combiner     = "OR"

  conditions {
    display_name = "Taxa de 429 acima do limite"
    condition_threshold {
      filter = <<-FILTER
        metric.type = "${var.vertex429_metric_type}"
      FILTER
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields = []
      }
      duration        = "600s"        # 10 minutos
      comparison      = "COMPARISON_GT"
      threshold_value = var.vertex429_rate_threshold
    }
  }

  notification_channels = var.alert_notification_channels
}

resource "google_monitoring_alert_policy" "delivery_failure" {
  display_name = "StoryBrand – Falhas de entrega"
  combiner     = "OR"

  conditions {
    display_name = "Falhas consecutivas de entrega"
    condition_threshold {
      filter = <<-FILTER
        metric.type = "${var.delivery_failure_metric_type}"
      FILTER
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields = []
      }
      duration        = "300s"        # 5 minutos
      comparison      = "COMPARISON_GT"
      threshold_value = var.delivery_failure_threshold
    }
  }

  notification_channels = var.alert_notification_channels
}
```

3. Acrescente (ou atualize) as variáveis correspondentes em `deployment/terraform/variables.tf`:

```hcl
variable "default_project_id" {
  description = "Project ID padrão (fallback quando project_id não for informado)"
  type        = string
  default     = ""
}

variable "project_id" {
  description = "Project ID onde as políticas serão criadas"
  type        = string
  default     = ""
}

variable "vertex429_metric_type" {
  description = "Metric type completo do contador de erros 429"
  type        = string
  default     = "custom.googleapis.com/storybrand/vertex429/count"  # TODO: confirme no Metrics Explorer
}

variable "vertex429_rate_threshold" {
  description = "Limite (taxa por minuto) para disparo do alerta de erros 429"
  type        = number
  default     = 5
}

variable "delivery_failure_metric_type" {
  description = "Metric type completo do contador de falhas de entrega"
  type        = string
  default     = "custom.googleapis.com/storybrand/delivery_failure/count"  # TODO: confirme no Metrics Explorer
}

variable "delivery_failure_threshold" {
  description = "Número de falhas em 5 minutos que dispara o alerta"
  type        = number
  default     = 1
}

variable "alert_notification_channels" {
  description = "Lista de IDs de canais de notificação (e-mail, Slack, Pub/Sub etc.)"
  type        = list(string)
  default     = []
}
```

> **Importante:** Identifique os `notification_channels` existentes (via console do Cloud Monitoring ou recurso Terraform `google_monitoring_notification_channel`). Adicione os IDs na variável `alert_notification_channels` (ex.: `var.alert_notification_channels = ["projects/<ID>/notificationChannels/<CHANNEL_ID>"]`).

---

## 3. Inicializar e aplicar o Terraform

1. Vá até o diretório de Terraform:
   ```bash
   cd deployment/terraform
   ```

2. Inicialize (apenas na primeira vez ou quando adicionar providers):
   ```bash
   terraform init
   ```

3. Visualize o plano antes de aplicar:
   ```bash
   terraform plan      -var="default_project_id=${GOOGLE_CLOUD_PROJECT}"      -var="alert_notification_channels=["projects/${GOOGLE_CLOUD_PROJECT}/notificationChannels/CHANNEL_ID"]"
   ```
   - Ajuste os valores das variáveis conforme necessário (`project_id`, thresholds, metric types etc.).
   - Confirme se o plano exibe apenas os recursos de alerta desejados.

4. Aplique o plano:
   ```bash
   terraform apply      -var="default_project_id=${GOOGLE_CLOUD_PROJECT}"      -var="alert_notification_channels=["projects/${GOOGLE_CLOUD_PROJECT}/notificationChannels/CHANNEL_ID"]"
   ```
   - Revise o resumo do Terraform e confirme com `yes`.

---

## 4. Verificação pós-implantação

1. Acesse **Google Cloud Console → Monitoring → Alerting** e confirme se as políticas “StoryBrand – Erros 429 (Vertex AI)” e “StoryBrand – Falhas de entrega” aparecem como *Enabled*.
2. No Metrics Explorer, confirme que as métricas configuradas (`vertex429_metric_type`, `delivery_failure_metric_type`) estão recebendo dados.
3. Opcional: force um cenário de teste (por exemplo, gerando algumas falhas controladas) para observar se um alerta é disparado e se a notificação chega pelo canal configurado.
4. Registre no histórico da equipe (ex.: CHANGELOG interno) a data e o responsável pela ativação das políticas.

---

## 5. Observações adicionais

- Se o projeto tiver múltiplos ambientes (dev/staging/prod), replique as políticas conforme necessário, ajustando `project_id`, thresholds e canais.
- Caso novos contadores sejam criados no código, siga o mesmo padrão: confirme o `metric.type` no Metrics Explorer, adicione uma nova `google_monitoring_alert_policy` em `monitoring.tf` e reaplique o Terraform.
- Em pipelines CI/CD, prefira rodar `terraform plan` e `terraform apply` (com aprovação manual) para garantir que alertas acompanhem as releases.

---

**Checklist rápido**

- [ ] Variáveis atualizadas com o `metric.type` real das métricas customizadas.  
- [ ] IDs de canais de notificação definidos.  
- [ ] `terraform plan` verificado sem diffs inesperados.  
- [ ] `terraform apply` concluído com sucesso.  
- [ ] Verificação no console confirma políticas ativas e notificações funcionando.

Com esses passos, a tarefa 4.2 do plano de correções fica efetivamente concluída e versionada como infraestrutura.  
Boa implementação!
