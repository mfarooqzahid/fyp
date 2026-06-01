variable "project_name" {
  description = "Project name used for IAM policy naming."
  type        = string
  default     = "fyp-analytics"
}

variable "aws_region" {
  description = "AWS region for ECR and IAM resources."
  type        = string
  default     = "ap-southeast-2"
}

variable "ecr_repository_name" {
  description = "ECR repository name used by Jenkins."
  type        = string
  default     = "fyp-analytics"
}

variable "jenkins_iam_role_name" {
  description = "Optional IAM role name attached to the Jenkins EC2 instance. Leave empty if you attach permissions another way."
  type        = string
  default     = ""
}

variable "vpc_id" {
  description = "VPC ID for the app EC2 security group. Leave empty to use the default VPC."
  type        = string
  default     = ""
}

variable "app_instance_type" {
  description = "EC2 instance type for the app server."
  type        = string
  default     = "t3.medium"
}

variable "app_key_name" {
  description = "Existing AWS EC2 key pair name used for SSH to the app server."
  type        = string
  default     = "farooq"
}

variable "app_root_volume_size" {
  description = "Root EBS volume size in GiB for the app server."
  type        = number
  default     = 30
}

variable "ssh_allowed_cidrs" {
  description = "CIDR blocks allowed to SSH into the app EC2. Prefer your IP or Jenkins EC2 public IP /32."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "app_allowed_cidrs" {
  description = "CIDR blocks allowed to access the app on port 8081."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "monitoring_allowed_cidrs" {
  description = "CIDR blocks allowed to access Grafana and Kibana. Prefer your IP /32."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
