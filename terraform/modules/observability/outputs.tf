output "prometheus_endpoint" {
  value = aws_prometheus_workspace.main.prometheus_endpoint
}

output "grafana_url" {
  value = aws_grafana_workspace.main.endpoint
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.app.name
}

output "sns_topic_arn" {
  value = aws_sns_topic.alerts.arn
}
