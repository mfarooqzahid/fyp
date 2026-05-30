# Docker and ECR Deployment

This project builds as one production image:

- Nginx serves the Vite React build on port `8080`.
- Nginx proxies `/api/*` to FastAPI running internally on port `8000`.
- The image includes `yolov8n.pt`, so keep that file in the project root before building.

## Run Locally

Create `backend/.env` first:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
```

Build and run:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

Health check:

```text
http://localhost:8080/api/health
```

## Build for ECR

Set these values for your AWS account:

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
ECR_REPOSITORY=fyp-analytics
IMAGE_TAG=latest
IMAGE_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
```

Create the ECR repository once:

```bash
aws ecr create-repository --repository-name "$ECR_REPOSITORY" --region "$AWS_REGION"
```

Authenticate Docker to ECR:

```bash
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

Build and push:

```bash
docker build -t "$IMAGE_URI" .
docker push "$IMAGE_URI"
```

## Runtime Configuration

Do not bake Supabase credentials into the image. Configure these as runtime environment variables in ECS, App Runner, or whichever AWS service runs the ECR image:

```env
SUPABASE_URL=...
SUPABASE_KEY=...
```

Expose container port `8080` from the AWS service. The frontend and API are served from the same origin, so no public API URL is needed for the React build.
