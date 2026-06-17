environment         = "production"
aws_region          = "us-east-1"
project_name        = "milyfe-brain"
vpc_cidr            = "10.1.0.0/16"
availability_zones  = ["us-east-1a", "us-east-1b", "us-east-1c"]

# Production-grade instances
eks_cluster_version     = "1.28"
eks_node_instance_types = ["t3.large", "t3.xlarge"]
eks_min_nodes           = 3
eks_max_nodes           = 10
eks_desired_nodes       = 3

db_instance_class    = "db.r6g.large"
db_allocated_storage = 100
redis_node_type      = "cache.r6g.large"

enable_gpu_nodes   = true
gpu_instance_types = ["g4dn.xlarge", "g5.xlarge"]
enable_waf         = true
enable_monitoring  = true
domain_name        = "api.milyfe.ai"
