# Terraform Infrastructure

This Terraform setup creates the ECR repository used by Jenkins and an IAM
policy that allows Jenkins to push and pull the application image.

## Apply

```bash
cd terraform
terraform init
terraform apply \
  -var="aws_region=us-east-1" \
  -var="ecr_repository_name=fyp-analytics" \
  -var="jenkins_iam_role_name=your-jenkins-ec2-role"
```

If your Jenkins EC2 instance does not use an IAM role, leave
`jenkins_iam_role_name` empty and attach the printed policy ARN manually to the
user or role Jenkins uses for AWS CLI access.

## Existing EC2 Instance

Because Jenkins and Docker already exist on your EC2 instance, this config does
not recreate the server. If you want Terraform to manage the existing EC2
instance too, import it first instead of creating a duplicate instance.
