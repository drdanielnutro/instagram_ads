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
