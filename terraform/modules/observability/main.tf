# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {
  name              = "/milyfe/${var.environment}/application"
  retention_in_days = var.environment == "production" ? 90 : 30

  tags = {
    Name = "${var.project_name}-${var.environment}-logs"
  }
}

# Prometheus workspace (Amazon Managed Prometheus)
resource "aws_prometheus_workspace" "main" {
  alias = "${var.project_name}-${var.environment}"

  tags = {
    Name = "${var.project_name}-${var.environment}-prometheus"
  }
}

# Grafana workspace (Amazon Managed Grafana)
resource "aws_grafana_workspace" "main" {
  name                     = "${var.project_name}-${var.environment}"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "SERVICE_MANAGED"
  role_arn                 = aws_iam_role.grafana.arn

  data_sources = ["PROMETHEUS", "CLOUDWATCH"]

  tags = {
    Name = "${var.project_name}-${var.environment}-grafana"
  }
}

resource "aws_iam_role" "grafana" {
  name = "${var.project_name}-${var.environment}-grafana-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "grafana.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "grafana" {
  name = "${var.project_name}-${var.environment}-grafana-policy"
  role = aws_iam_role.grafana.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aps:QueryMetrics",
          "aps:GetSeries",
          "aps:GetLabels",
          "aps:GetMetricMetadata"
        ]
        Resource = aws_prometheus_workspace.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:DescribeAlarmsForMetric",
          "cloudwatch:DescribeAlarmHistory",
          "cloudwatch:DescribeAlarms",
          "cloudwatch:ListMetrics",
          "cloudwatch:GetMetricData",
          "cloudwatch:GetInsightRuleReport",
          "logs:DescribeLogGroups",
          "logs:GetLogGroupFields",
          "logs:StartQuery",
          "logs:StopQuery",
          "logs:GetQueryResults",
          "logs:GetLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EKS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "CPU utilization exceeds 80%"

  dimensions = {
    ClusterName = var.eks_cluster_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_memory" {
  alarm_name          = "${var.project_name}-${var.environment}-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/EKS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Memory utilization exceeds 85%"

  dimensions = {
    ClusterName = var.eks_cluster_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"
}

resource "aws_sns_topic_policy" "alerts" {
  arn = aws_sns_topic.alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "cloudwatch.amazonaws.com"
      }
      Action   = "SNS:Publish"
      Resource = aws_sns_topic.alerts.arn
    }]
  })
}
