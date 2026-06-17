output "cluster_name" {
  value = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "cluster_ca_certificate" {
  value = aws_eks_cluster.main.certificate_authority[0].data
}

output "cluster_token" {
  value = data.aws_eks_cluster_auth.main.token
}

output "cluster_arn" {
  value = aws_eks_cluster.main.arn
}

output "oidc_issuer" {
  value = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

output "node_security_group_id" {
  value = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}

output "ecr_backend_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  value = aws_ecr_repository.frontend.repository_url
}

data "aws_eks_cluster_auth" "main" {
  name = aws_eks_cluster.main.name
}
