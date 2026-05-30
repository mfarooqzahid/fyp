# Learning This Dockerfile

This project has two parts:

1. `frontend/` is a React/Vite app.
2. `backend/` is a FastAPI app.

The Docker setup builds both parts into one production image.

## Big Picture

In development, you usually run two servers:

```text
Frontend: http://localhost:5174
Backend:  http://localhost:8000
```

In Docker, this setup runs as one app:

```text
Browser
  |
  v
Nginx :8080
  |
  |-- /          -> React frontend
  |
  |-- /api/*     -> FastAPI backend on 127.0.0.1:8000
```

So the final container exposes only one port:

```text
8080
```

This is useful for AWS/ECR deployment because you only need to push and run one image.

## Why This Dockerfile Looks Different

A simple Dockerfile usually has one `FROM` line.

This project uses a multi-stage Dockerfile:

```dockerfile
FROM node:20-bookworm-slim AS frontend-build
...
FROM python:3.11-slim-bookworm AS runtime
...
```

That means:

- the first stage uses Node.js to build the frontend
- the second stage uses Python to run the backend
- only the final stage becomes the real image

Node.js is not needed at runtime because the React app becomes static files after `npm run build`.

## Stage 1: Build the Frontend

```dockerfile
FROM node:20-bookworm-slim AS frontend-build
```

This starts from a Node.js image.

The name `frontend-build` lets us refer to this stage later.

```dockerfile
WORKDIR /app/frontend
```

This sets the working directory inside the image.

Any following command runs from:

```text
/app/frontend
```

```dockerfile
COPY frontend/package*.json ./
```

This copies:

```text
frontend/package.json
frontend/package-lock.json
```

into the image.

```dockerfile
RUN npm ci
```

This installs frontend dependencies.

`npm ci` is preferred in Docker when `package-lock.json` exists because it gives repeatable installs.

```dockerfile
COPY frontend/ ./
```

This copies the rest of the frontend source code.

```dockerfile
RUN npm run build
```

This builds the React app.

Vite creates the production frontend here:

```text
/app/frontend/dist/
```

That folder contains static HTML, CSS, and JavaScript.

## Stage 2: Build the Runtime Image

```dockerfile
FROM python:3.11-slim-bookworm AS runtime
```

This starts the final image from Python.

The backend is Python, so the final image must have Python.

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
```

These are common Python Docker settings.

```text
PYTHONDONTWRITEBYTECODE=1
```

Stops Python from creating `.pyc` cache files.

```text
PYTHONUNBUFFERED=1
```

Makes Python print logs immediately.

This is useful in Docker because container logs should appear without delay.

```text
PIP_NO_CACHE_DIR=1
```

Stops pip from keeping package cache files.

This helps keep the image smaller.

```dockerfile
WORKDIR /app
```

Sets the working directory for the final app.

## Installing System Packages

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        nginx \
    && rm -rf /var/lib/apt/lists/*
```

This installs Linux packages required by the app.

```text
nginx
```

Serves the frontend and forwards API requests to FastAPI.

```text
libgl1
libglib2.0-0
```

Required by OpenCV.

Your backend uses `opencv-python`, so these libraries are needed inside the container.

```dockerfile
rm -rf /var/lib/apt/lists/*
```

Removes apt package list files after installation.

This keeps the image smaller.

## Installing Python Dependencies

```dockerfile
COPY backend/requirements.txt /app/backend/requirements.txt
```

Copies only the requirements file first.

```dockerfile
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/backend/requirements.txt
```

Installs the backend dependencies.

This includes packages like:

- FastAPI
- Uvicorn
- Supabase
- OpenCV
- Ultralytics
- Deep SORT

Copying `requirements.txt` separately is useful because Docker can cache this layer.

If your backend code changes but `requirements.txt` does not, Docker does not need to reinstall all Python packages.

## Copying Application Files

```dockerfile
COPY backend/ /app/backend/
```

Copies the backend code into the image.

```dockerfile
COPY yolov8n.pt /app/yolov8n.pt
```

Copies the YOLO model file into the image.

Your backend config uses:

```python
MODEL_PATH = "yolov8n.pt"
```

Since the container runs from `/app`, the model will be available at:

```text
/app/yolov8n.pt
```

## Copying the Built Frontend

```dockerfile
COPY --from=frontend-build /app/frontend/dist/ /usr/share/nginx/html/
```

This is the most important multi-stage line.

It means:

> Copy the React production build from the Node stage into the final Python/Nginx image.

The frontend build was created here:

```text
/app/frontend/dist/
```

Nginx serves static files from here:

```text
/usr/share/nginx/html/
```

So after this line, Nginx can serve the React app.

## Nginx Config and Entrypoint

```dockerfile
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/entrypoint.sh /entrypoint.sh
```

Copies the Nginx configuration and startup script.

```dockerfile
RUN chmod +x /entrypoint.sh \
    && mkdir -p /run/nginx /var/cache/nginx /var/log/nginx
```

Makes the startup script executable and creates directories Nginx may need.

## Exposing the Port

```dockerfile
EXPOSE 8080
```

This documents that the container listens on port `8080`.

It does not publish the port by itself.

When running locally, Docker Compose maps it like this:

```yaml
ports:
  - "8080:8080"
```

That means:

```text
host port 8080 -> container port 8080
```

## Healthcheck

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)"
```

This tells Docker how to check if the app is healthy.

It calls:

```text
http://127.0.0.1:8080/api/health
```

That request goes through Nginx and reaches FastAPI.

If the endpoint responds, the container is healthy.

## Container Startup

```dockerfile
CMD ["/entrypoint.sh"]
```

This tells Docker what to run when the container starts.

The script is:

```sh
#!/bin/sh
set -eu

cd /app

uvicorn backend.api:app --host 127.0.0.1 --port 8000 &
api_pid="$!"

trap 'kill "$api_pid" 2>/dev/null || true; wait "$api_pid" 2>/dev/null || true' INT TERM

nginx -g 'daemon off;' &
nginx_pid="$!"

wait "$nginx_pid"
```

This starts FastAPI in the background:

```sh
uvicorn backend.api:app --host 127.0.0.1 --port 8000 &
```

FastAPI listens only inside the container on:

```text
127.0.0.1:8000
```

Then it starts Nginx:

```sh
nginx -g 'daemon off;'
```

Nginx listens on:

```text
0.0.0.0:8080
```

So users only access Nginx.

Nginx decides whether to serve frontend files or forward the request to FastAPI.

## Nginx Routing

The Nginx config has this:

```nginx
location /api/ {
    proxy_pass http://backend;
}
```

That means every request starting with `/api/` goes to FastAPI.

Example:

```text
/api/health
/api/sources
/api/dashboard
```

The frontend route is:

```nginx
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}
```

That means normal browser routes serve the React app.

The `try_files` part is important for React apps.

If the browser opens a route like:

```text
/dashboard
```

Nginx falls back to:

```text
/index.html
```

Then React handles the route in the browser.

## Simple Backend-Only Dockerfile

If you only wanted to Dockerize the backend, it could look like this:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ ./backend
COPY yolov8n.pt .

EXPOSE 8000

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

This is easier, but it only runs the backend.

The frontend would still need to be hosted somewhere else.

## Simple Frontend-Only Dockerfile

For development, the frontend alone could look like this:

```dockerfile
FROM node:20

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .

EXPOSE 5174

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

This is okay for local development.

It is not ideal for production because `npm run dev` is a development server.

## Why the Combined Production Image Is Better for ECR

For your ECR plan, the combined image is better because:

- you push one image
- AWS runs one container
- only one public port is needed
- frontend and backend share the same domain
- frontend can call `/api` directly
- CORS issues are reduced

In AWS, configure these as runtime environment variables:

```env
SUPABASE_URL=...
SUPABASE_KEY=...
```

Do not put secrets directly in the Dockerfile.

## Mental Model

The Dockerfile is doing this:

```text
1. Use Node to build React.
2. Use Python as the final app image.
3. Install OpenCV and Nginx system dependencies.
4. Install Python backend dependencies.
5. Copy backend code.
6. Copy YOLO model.
7. Copy built React files into Nginx.
8. Start FastAPI and Nginx.
9. Expose one port: 8080.
```

That is the whole idea.
