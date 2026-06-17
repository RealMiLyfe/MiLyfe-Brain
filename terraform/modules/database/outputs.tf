output "rds_endpoint" {
  value = aws_db_instance.main.endpoint
}

output "rds_address" {
  value = aws_db_instance.main.address
}

output "rds_port" {
  value = aws_db_instance.main.port
}

output "rds_secret_arn" {
  value = aws_secretsmanager_secret.rds.arn
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "redis_secret_arn" {
  value = aws_secretsmanager_secret.redis.arn
}
