# syntax=docker/dockerfile:1
# Shadow Lab Deployer
# Base image ships the docker CLI + compose plugin (same major line as the
# lab hosts); Python/FastAPI are added on top.
FROM docker:29-cli

RUN apk add --no-cache python3 py3-pip && \
    pip install --no-cache-dir --break-system-packages \
        "fastapi>=0.115" "uvicorn[standard]>=0.30" "pyyaml>=6"

COPY app/ /opt/app/
COPY static/ /opt/static/

WORKDIR /opt/app
EXPOSE 8080

# Single worker: the job registry lives in process memory.
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
