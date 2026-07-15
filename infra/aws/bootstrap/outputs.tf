output "terraform_state_bucket" {
  value = aws_s3_bucket.state.id
}

output "terraform_state_kms_key_arn" {
  value = aws_kms_key.state.arn
}

output "image_publish_role_arn" {
  value = aws_iam_role.image_publish.arn
}

output "terraform_deploy_role_arn" {
  value = aws_iam_role.terraform_deploy.arn
}

output "alert_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "cosign_kms_key_uri" {
  value = "awskms:///${aws_kms_key.image_signing.arn}"
}

output "ecr_repository_urls" {
  value = { for name, repository in aws_ecr_repository.production : name => repository.repository_url }
}
