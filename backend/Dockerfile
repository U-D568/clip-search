FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

FROM python:3.13-slim
RUN apt-get update && apt-get install -y \
    libxcb1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

COPY . .
