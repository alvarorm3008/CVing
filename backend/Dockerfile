# Backend-only for Railway (service Root Directory = /backend).
# Frontend lives on Vercel. Chromium included in base image.
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
ENV SERVE_FRONTEND=0
EXPOSE 8000

# Railway injects PORT
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
