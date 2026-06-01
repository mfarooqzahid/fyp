terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_ecr_repository" "app" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep the latest 20 pushed images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 20
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

data "aws_iam_policy_document" "jenkins_ecr" {
  statement {
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    resources = ["*"]
  }

  statement {
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:DescribeRepositories",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:ListImages",
      "ecr:PutImage",
      "ecr:UploadLayerPart"
    ]
    resources = [aws_ecr_repository.app.arn]
  }
}

resource "aws_iam_policy" "jenkins_ecr" {
  name        = "${var.project_name}-jenkins-ecr"
  description = "Allow Jenkins to push and pull the ${var.project_name} ECR image."
  policy      = data.aws_iam_policy_document.jenkins_ecr.json
}

resource "aws_iam_role_policy_attachment" "jenkins_ecr" {
  count      = var.jenkins_iam_role_name == "" ? 0 : 1
  role       = var.jenkins_iam_role_name
  policy_arn = aws_iam_policy.jenkins_ecr.arn
}

data "aws_vpc" "selected" {
  id      = var.vpc_id == "" ? null : var.vpc_id
  default = var.vpc_id == "" ? true : null
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_iam_policy_document" "app_ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app_ec2" {
  name               = "${var.project_name}-app-ec2"
  assume_role_policy = data.aws_iam_policy_document.app_ec2_assume_role.json
}

data "aws_iam_policy_document" "app_ec2_ecr_pull" {
  statement {
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    resources = ["*"]
  }

  statement {
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:DescribeImages",
      "ecr:DescribeRepositories",
      "ecr:GetDownloadUrlForLayer"
    ]
    resources = [aws_ecr_repository.app.arn]
  }
}

resource "aws_iam_policy" "app_ec2_ecr_pull" {
  name        = "${var.project_name}-app-ec2-ecr-pull"
  description = "Allow the ${var.project_name} app EC2 instance to pull images from ECR."
  policy      = data.aws_iam_policy_document.app_ec2_ecr_pull.json
}

resource "aws_iam_role_policy_attachment" "app_ec2_ecr_pull" {
  role       = aws_iam_role.app_ec2.name
  policy_arn = aws_iam_policy.app_ec2_ecr_pull.arn
}

resource "aws_iam_instance_profile" "app_ec2" {
  name = "${var.project_name}-app-ec2"
  role = aws_iam_role.app_ec2.name
}

resource "aws_security_group" "app" {
  name        = "${var.project_name}-app"
  description = "Access to the ${var.project_name} app server."
  vpc_id      = data.aws_vpc.selected.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_allowed_cidrs
  }

  ingress {
    description = "Application"
    from_port   = 8081
    to_port     = 8081
    protocol    = "tcp"
    cidr_blocks = var.app_allowed_cidrs
  }

  ingress {
    description = "Grafana"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = var.monitoring_allowed_cidrs
  }

  ingress {
    description = "Kibana"
    from_port   = 5601
    to_port     = 5601
    protocol    = "tcp"
    cidr_blocks = var.monitoring_allowed_cidrs
  }

  egress {
    description = "Outbound internet"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-app"
  }
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.app_instance_type
  key_name                    = var.app_key_name
  vpc_security_group_ids      = [aws_security_group.app.id]
  iam_instance_profile        = aws_iam_instance_profile.app_ec2.name
  associate_public_ip_address = true

  root_block_device {
    volume_size = var.app_root_volume_size
    volume_type = "gp3"
  }

  user_data = <<-USERDATA
    #!/bin/bash
    set -eux

    apt-get update
    apt-get install -y ca-certificates curl gnupg unzip awscli

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" > /etc/apt/sources.list.d/docker.list

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    systemctl enable docker
    systemctl start docker
    usermod -aG docker ubuntu

    mkdir -p /opt/fyp
    chown ubuntu:ubuntu /opt/fyp
  USERDATA

  tags = {
    Name = "${var.project_name}-app"
  }
}
