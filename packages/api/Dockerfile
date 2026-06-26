FROM python:3.14-slim

WORKDIR /app

# tesseract-ocr: local OCR for the library-import path (Epic 14).
RUN apt-get update \
    && apt-get install --no-install-recommends -y tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --without dev --no-root --no-interaction

COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY src/ ./src/

RUN poetry install --without dev --no-interaction

# Run as an unprivileged system user. The capture upload dir
# (settings.capture_upload_dir, default "uploads/captures", relative to /app)
# must be writable by this user, so create it and chown the app tree.
RUN adduser --system --no-create-home --group appuser \
    && mkdir -p /app/uploads/captures \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8100

# --proxy-headers + --forwarded-allow-ips lets uvicorn trust X-Forwarded-For /
# X-Forwarded-Proto from the Caddy reverse proxy, so the real client IP reaches
# the app (auth rate limiter keys on client IP — without this every request
# collapses to the proxy's address). FORWARDED_ALLOW_IPS must list ONLY the
# trusted proxy: default is the docker bridge gateway (172.17.0.1) where Caddy
# typically lives; override to Caddy's container/host IP for your topology.
# Never set it to "*" in production — that lets any client spoof its IP.
ENV FORWARDED_ALLOW_IPS=172.17.0.1
CMD ["sh", "-c", "uvicorn src.dailyloadout.main:app --host 0.0.0.0 --port 8100 --proxy-headers --forwarded-allow-ips \"$FORWARDED_ALLOW_IPS\""]
