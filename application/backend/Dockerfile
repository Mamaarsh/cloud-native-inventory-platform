# ---------- Builder Stage ----------
FROM python:3.14-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip wheel \
        --wheel-dir /wheels \
        -r requirements.txt

# ---------- Runtime Stage ----------
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system appgroup \
    && useradd --system \
        --gid appgroup \
        --create-home \
        --home-dir /home/appuser \
        appuser

COPY --from=builder /wheels /wheels

COPY requirements.txt .

RUN python -m pip install \
        --no-index \
        --find-links=/wheels \
        -r requirements.txt \
    && rm -rf /wheels

COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health/live/', timeout=3)"

CMD ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"]