pipeline {
  agent any

  environment {
    AWS_REGION = 'ap-southeast-2'
    ECR_REPOSITORY = 'fyp-analytics'
    DEPLOY_HOST = 'ec2-54-253-146-9.ap-southeast-2.compute.amazonaws.com'
    DEPLOY_USER = 'ubuntu'
    DEPLOY_DIR = '/opt/fyp'
  }

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build Image') {
      steps {
        sh '''
          set -eu
          AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
          IMAGE_TAG="$(printf '%s' "${GIT_COMMIT:-manual}" | cut -c1-12)"
          IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"

          docker build -t "$IMAGE_URI" .
          printf '%s' "$IMAGE_URI" > image-uri.txt
        '''
      }
    }

    stage('Push To ECR') {
      steps {
        sh '''
          set -eu
          AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
          ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
          IMAGE_URI="$(cat image-uri.txt)"

          aws ecr get-login-password --region "$AWS_REGION" \
            | docker login --username AWS --password-stdin "$ECR_REGISTRY"

          docker push "$IMAGE_URI"
        '''
      }
    }

    stage('Deploy To EC2') {
      steps {
        sshagent(credentials: ['ec2-deploy-ssh-key']) {
          sh '''
            set -eu
            IMAGE_URI="$(cat image-uri.txt)"
            AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
            ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

            ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" "mkdir -p '$DEPLOY_DIR'"
            scp deploy/docker-compose.prod.yml deploy/prometheus.yml deploy/filebeat.yml deploy/grafana-datasources.yml "$DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_DIR/"

            ssh "$DEPLOY_USER@$DEPLOY_HOST" "
              set -eu
              cd '$DEPLOY_DIR'
              aws ecr get-login-password --region '$AWS_REGION' | docker login --username AWS --password-stdin '$ECR_REGISTRY'
              printf 'IMAGE_URI=%s\\n' '$IMAGE_URI' > .env
              test -f backend.env || { echo 'Missing $DEPLOY_DIR/backend.env with SUPABASE_URL and SUPABASE_KEY'; exit 1; }
              docker compose -f docker-compose.prod.yml pull app
              docker compose -f docker-compose.prod.yml up -d
              docker image prune -f
            "
          '''
        }
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'image-uri.txt', allowEmptyArchive: true
    }
  }
}
