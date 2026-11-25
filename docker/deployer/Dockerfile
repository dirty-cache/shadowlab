# syntax=docker/dockerfile:1
# Shadow Lab Deployer
# Published to https://github.com/dirty-cache/shadowlab/packages
# as ghcr.io/dirty-cache/shadowlab/deployer
FROM python:3.13-alpine

LABEL org.opencontainers.image.source=https://github.com/dirty-cache/shadowlab
LABEL org.opencontainers.image.description="Shadow Lab Deployer"

RUN pip install --no-cache-dir --break-system-packages \
        "fastapi>=0.115" "uvicorn[standard]>=0.30" "pyyaml>=6" "httpx>=0.27"

COPY app/ /opt/app/
COPY static/ /opt/static/

WORKDIR /opt/app
EXPOSE 8080

# Single worker: the job registry lives in process memory.
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
