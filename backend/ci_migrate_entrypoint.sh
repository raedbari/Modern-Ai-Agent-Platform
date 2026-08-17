#!/bin/sh
set -eu

echo "[migrate] user: $(id -u):$(id -g)"
echo "[migrate] working directory: $(pwd)"
echo "[migrate] backend contents:"
ls -la /app/backend

cd /app/backend
exec alembic -c alembic.ini upgrade head
