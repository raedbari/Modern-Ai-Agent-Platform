FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system --gid 10001 maap \
    && adduser --system --uid 10001 --ingroup maap --home /nonexistent maap

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements.txt

COPY --chown=maap:maap backend /app/backend

# copy CI entrypoint for migrate
COPY backend/ci_migrate_entrypoint.sh /app/backend/ci_migrate_entrypoint.sh
RUN chmod +x /app/backend/ci_migrate_entrypoint.sh

USER maap

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
