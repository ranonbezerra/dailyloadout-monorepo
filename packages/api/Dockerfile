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
# the app (auth rate limiter keys on client IP).
# ⚠ FORWARDED_ALLOW_IPS must be EXACTLY the trusted proxy's source IP for YOUR
# topology — host+systemd Caddy → 127.0.0.1 (this safe default); all-in-compose →
# the compose network gateway (172.18+). The default is the LOOPBACK-only
# 127.0.0.1: if it's wrong for your topology, X-Forwarded-For is ignored and every
# request shares ONE per-IP bucket (over-restrictive — fails SAFE), which is far
# better than the old 172.17.0.1 bridge default that a mismatch could turn
# spoofable. Override to the exact proxy IP and VERIFY after deploy. NEVER "*" —
# that lets clients spoof their source IP and rotate the rate-limit identity.
# --timeout-keep-alive bounds idle keep-alive sockets (slow-loris mitigation;
# the reverse proxy should also enforce request read/write timeouts).
ENV FORWARDED_ALLOW_IPS=127.0.0.1
CMD ["sh", "-c", "uvicorn src.slate.main:app --host 0.0.0.0 --port 8100 --proxy-headers --forwarded-allow-ips \"$FORWARDED_ALLOW_IPS\" --timeout-keep-alive 5"]
