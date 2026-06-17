variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be 'staging' or 'production'."
  }
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "milyfe-brain"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "eks_cluster_version" {
  description = "Kubernetes version for EKS"
  type        = string
  default     = "1.28"
}

variable "eks_node_instance_types" {
  description = "EC2 instance types for EKS nodes"
  type        = list(string)
  default     = ["t3.large", "t3.xlarge"]
}

variable "eks_min_nodes" {
  description = "Minimum number of EKS nodes"
  type        = number
  default     = 2
}

variable "eks_max_nodes" {
  description = "Maximum number of EKS nodes"
  type        = number
  default     = 10
}

variable "eks_desired_nodes" {
  description = "Desired number of EKS nodes"
  type        = number
  default     = 3
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS (GB)"
  type        = number
  default     = 50
}

variable "redis_node_type" {
  description = "ElastiCache node type for Redis"
  type        = string
  default     = "cache.t3.medium"
}

variable "enable_gpu_nodes" {
  description = "Enable GPU node group for Ollama"
  type        = bool
  default     = false
}

variable "gpu_instance_types" {
  description = "GPU instance types for Ollama inference"
  type        = list(string)
  default     = ["g4dn.xlarge", "g5.xlarge"]
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

variable "enable_waf" {
  description = "Enable AWS WAF"
  type        = bool
  default     = true
}

variable "enable_monitoring" {
  description = "Enable enhanced monitoring and observability"
  type        = bool
  default     = true
}
