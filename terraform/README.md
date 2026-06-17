# MiLyfe Brain - Terraform Infrastructure

Infrastructure as Code for deploying MiLyfe Brain to AWS.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    VPC (10.x.0.0/16)                 │   │
│  │                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ Public Sub  │  │ Public Sub  │  │ Public Sub │ │   │
│  │  │  (ALB/NAT)  │  │  (ALB/NAT)  │  │ (ALB/NAT) │ │   │
│  │  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  │                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ Private Sub │  │ Private Sub │  │Private Sub │ │   │
│  │  │ (EKS/RDS)  │  │ (EKS/RDS)  │  │(EKS/RDS)  │ │   │
│  │  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Services:                                                  │
│  • EKS Cluster (K8s 1.28) — Backend + Frontend pods        │
│  • RDS PostgreSQL 16 — Primary database                     │
│  • ElastiCache Redis 7 — Cache + PubSub                    │
│  • S3 — File storage + Workspaces                          │
│  • SQS — Background job queue                              │
│  • ECR — Container registry                                │
│  • Amazon Managed Prometheus — Metrics                     │
│  • Amazon Managed Grafana — Dashboards                     │
│  • CloudWatch — Logs + Alarms                              │
│  • WAF — Web Application Firewall                          │
│  • KMS — Encryption at rest                                │
└─────────────────────────────────────────────────────────────┘
```

## Modules

| Module | Description |
|--------|-------------|
| `networking` | VPC, subnets, NAT, ALB, WAF, security groups |
| `compute` | EKS cluster, node groups (general + GPU), ECR |
| `database` | RDS PostgreSQL, ElastiCache Redis, secrets |
| `ai-services` | S3 buckets, SQS queues, IAM roles |
| `observability` | Prometheus, Grafana, CloudWatch, SNS alerts |

## Usage

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.5.0
- S3 bucket for state: `milyfe-terraform-state`
- DynamoDB table for locks: `milyfe-terraform-locks`

### Deploy Staging

```bash
cd terraform
terraform init
terraform workspace select staging || terraform workspace new staging
terraform plan -var-file=environments/staging/terraform.tfvars
terraform apply -var-file=environments/staging/terraform.tfvars
```

### Deploy Production

```bash
cd terraform
terraform workspace select production || terraform workspace new production
terraform plan -var-file=environments/production/terraform.tfvars
terraform apply -var-file=environments/production/terraform.tfvars
```

### Get Kubeconfig

```bash
aws eks update-kubeconfig --name milyfe-brain-production --region us-east-1
```

## Cost Estimates

| Environment | Monthly Estimate |
|-------------|-----------------|
| Staging | ~$300-500 |
| Production | ~$1,500-3,000 |
| Production + GPU | ~$2,500-5,000 |

## Security

- All data encrypted at rest (KMS)
- All traffic encrypted in transit (TLS)
- Private subnets for compute and data
- WAF with rate limiting and managed rules
- Secrets in AWS Secrets Manager
- IRSA (IAM Roles for Service Accounts) for pod-level access
- Security group least-privilege
