FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./

# Read runtime dependencies from project metadata before copying source so an
# ordinary source edit can reuse this layer.
RUN python -c "import subprocess, sys, tomllib; deps = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', '--prefix=/install', *deps])"

COPY src ./src
RUN python -m pip wheel --no-deps --wheel-dir /wheels . \
    && python -m pip install --no-deps --prefix=/install /wheels/fraud_service-*.whl

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRAUD_ENVIRONMENT=production \
    FRAUD_HOST=0.0.0.0 \
    FRAUD_PORT=8000 \
    FRAUD_MODEL_PATH=/app/models/fraud_xgb_v3.joblib

RUN groupadd --system fraud \
    && useradd --system --create-home --gid fraud --home-dir /app fraud
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=fraud:fraud models ./models

USER fraud
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/ready', timeout=2)"]

CMD ["python", "-m", "fraud_service.api.app"]
