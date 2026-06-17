# S3 Bucket for file storage (MinIO-compatible interface)
resource "aws_s3_bucket" "files" {
  bucket = "${var.project_name}-${var.environment}-files"

  tags = {
    Name = "${var.project_name}-${var.environment}-files"
  }
}

resource "aws_s3_bucket_versioning" "files" {
  bucket = aws_s3_bucket.files.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "files" {
  bucket = aws_s3_bucket.files.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "files" {
  bucket = aws_s3_bucket.files.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "files" {
  bucket = aws_s3_bucket.files.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }

  rule {
    id     = "cleanup-multipart"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# S3 Bucket for workspace outputs
resource "aws_s3_bucket" "workspaces" {
  bucket = "${var.project_name}-${var.environment}-workspaces"

  tags = {
    Name = "${var.project_name}-${var.environment}-workspaces"
  }
}

resource "aws_s3_bucket_versioning" "workspaces" {
  bucket = aws_s3_bucket.workspaces.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "workspaces" {
  bucket = aws_s3_bucket.workspaces.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "workspaces" {
  bucket = aws_s3_bucket.workspaces.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM Role for EKS pods to access S3
resource "aws_iam_role" "s3_access" {
  name = "${var.project_name}-${var.environment}-s3-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${replace(var.eks_oidc_issuer, "https://", "")}"
      }
      Condition = {
        StringEquals = {
          "${replace(var.eks_oidc_issuer, "https://", "")}:sub" = "system:serviceaccount:milyfe:milyfe-backend"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "s3_access" {
  name = "${var.project_name}-${var.environment}-s3-policy"
  role = aws_iam_role.s3_access.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.files.arn,
          "${aws_s3_bucket.files.arn}/*",
          aws_s3_bucket.workspaces.arn,
          "${aws_s3_bucket.workspaces.arn}/*"
        ]
      }
    ]
  })
}

# SQS Queue for background job processing
resource "aws_sqs_queue" "tasks" {
  name = "${var.project_name}-${var.environment}-tasks"

  visibility_timeout_seconds = 300
  message_retention_seconds  = 1209600  # 14 days
  receive_wait_time_seconds  = 20       # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.tasks_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-tasks"
  }
}

resource "aws_sqs_queue" "tasks_dlq" {
  name = "${var.project_name}-${var.environment}-tasks-dlq"

  message_retention_seconds = 1209600

  tags = {
    Name = "${var.project_name}-${var.environment}-tasks-dlq"
  }
}

data "aws_caller_identity" "current" {}
