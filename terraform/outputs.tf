output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.compute.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.compute.cluster_endpoint
  sensitive   = true
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.database.rds_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.database.redis_endpoint
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 bucket for file storage"
  value       = module.ai_services.s3_bucket_name
}

output "ecr_backend_url" {
  description = "ECR repository URL for backend"
  value       = module.compute.ecr_backend_url
}

output "ecr_frontend_url" {
  description = "ECR repository URL for frontend"
  value       = module.compute.ecr_frontend_url
}

output "load_balancer_dns" {
  description = "Application Load Balancer DNS name"
  value       = module.networking.alb_dns_name
}

output "grafana_url" {
  description = "Grafana dashboard URL"
  value       = var.enable_monitoring ? module.observability[0].grafana_url : ""
}

output "kubeconfig_command" {
  description = "Command to update kubeconfig"
  value       = "aws eks update-kubeconfig --name ${module.compute.cluster_name} --region ${var.aws_region}"
}
