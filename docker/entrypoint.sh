#!/bin/sh
set -eu

cd /app

uvicorn backend.api:app --host 127.0.0.1 --port 8000 &
api_pid="$!"

trap 'kill "$api_pid" 2>/dev/null || true; wait "$api_pid" 2>/dev/null || true' INT TERM

nginx -g 'daemon off;' &
nginx_pid="$!"

wait "$nginx_pid"
