output "s3_bucket_name" {
  value = aws_s3_bucket.files.bucket
}

output "s3_bucket_arn" {
  value = aws_s3_bucket.files.arn
}

output "workspaces_bucket_name" {
  value = aws_s3_bucket.workspaces.bucket
}

output "sqs_queue_url" {
  value = aws_sqs_queue.tasks.url
}

output "sqs_queue_arn" {
  value = aws_sqs_queue.tasks.arn
}

output "s3_access_role_arn" {
  value = aws_iam_role.s3_access.arn
}
