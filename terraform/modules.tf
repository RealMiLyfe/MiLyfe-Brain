module "networking" {
  source = "./modules/networking"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  enable_waf         = var.enable_waf
  domain_name        = var.domain_name
}

module "compute" {
  source = "./modules/compute"

  project_name        = var.project_name
  environment         = var.environment
  vpc_id              = module.networking.vpc_id
  private_subnet_ids  = module.networking.private_subnet_ids
  cluster_version     = var.eks_cluster_version
  node_instance_types = var.eks_node_instance_types
  min_nodes           = var.eks_min_nodes
  max_nodes           = var.eks_max_nodes
  desired_nodes       = var.eks_desired_nodes
  enable_gpu_nodes    = var.enable_gpu_nodes
  gpu_instance_types  = var.gpu_instance_types
}

module "database" {
  source = "./modules/database"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  db_instance_class  = var.db_instance_class
  allocated_storage  = var.db_allocated_storage
  redis_node_type    = var.redis_node_type
  allowed_security_groups = [module.compute.node_security_group_id]
}

module "ai_services" {
  source = "./modules/ai-services"

  project_name    = var.project_name
  environment     = var.environment
  vpc_id          = module.networking.vpc_id
  eks_cluster_arn = module.compute.cluster_arn
  eks_oidc_issuer = module.compute.oidc_issuer
}

module "observability" {
  source = "./modules/observability"
  count  = var.enable_monitoring ? 1 : 0

  project_name       = var.project_name
  environment        = var.environment
  eks_cluster_name   = module.compute.cluster_name
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
}
