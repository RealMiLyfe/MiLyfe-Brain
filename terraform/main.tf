terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  backend "s3" {
    bucket         = "milyfe-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "milyfe-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "MiLyfe-Brain"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Team        = "Infrastructure"
    }
  }
}

provider "kubernetes" {
  host                   = module.compute.cluster_endpoint
  cluster_ca_certificate = base64decode(module.compute.cluster_ca_certificate)
  token                  = module.compute.cluster_token
}

provider "helm" {
  kubernetes {
    host                   = module.compute.cluster_endpoint
    cluster_ca_certificate = base64decode(module.compute.cluster_ca_certificate)
    token                  = module.compute.cluster_token
  }
}
