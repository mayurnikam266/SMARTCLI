# 📦 Base image with only build tools
FROM python:3.10-slim AS builder

WORKDIR /app
COPY . /app

# Install system deps + build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev curl git \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential gcc \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 🏗️ Final runtime image
FROM python:3.10-slim

WORKDIR /app

COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=builder /usr/local/bin /usr/local/bin

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8


RUN echo '#!/bin/sh\npython3 /app/smartcli/scli.py "$@"' > /usr/local/bin/scli && chmod +x /usr/local/bin/scli

ENTRYPOINT ["scli"]
