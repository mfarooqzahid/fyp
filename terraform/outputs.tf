output "ecr_repository_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "ECR repository URL used by the Jenkins pipeline."
}

output "jenkins_ecr_policy_arn" {
  value       = aws_iam_policy.jenkins_ecr.arn
  description = "IAM policy ARN for Jenkins ECR access."
}

output "app_ec2_public_ip" {
  value       = aws_instance.app.public_ip
  description = "Public IP address of the app EC2 instance."
}

output "app_ec2_public_dns" {
  value       = aws_instance.app.public_dns
  description = "Public DNS name of the app EC2 instance."
}

output "app_ec2_security_group_id" {
  value       = aws_security_group.app.id
  description = "Security group ID attached to the app EC2 instance."
}

output "app_ec2_ecr_pull_policy_arn" {
  value       = aws_iam_policy.app_ec2_ecr_pull.arn
  description = "IAM policy ARN that allows the app EC2 instance to pull from ECR."
}
