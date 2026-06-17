environment         = "staging"
aws_region          = "us-east-1"
project_name        = "milyfe-brain"
vpc_cidr            = "10.0.0.0/16"
availability_zones  = ["us-east-1a", "us-east-1b"]

# Smaller instances for staging
eks_cluster_version     = "1.28"
eks_node_instance_types = ["t3.medium"]
eks_min_nodes           = 1
eks_max_nodes           = 4
eks_desired_nodes       = 2

db_instance_class    = "db.t3.small"
db_allocated_storage = 20
redis_node_type      = "cache.t3.small"

enable_gpu_nodes   = false
enable_waf         = false
enable_monitoring  = true
domain_name        = "staging.milyfe.ai"
