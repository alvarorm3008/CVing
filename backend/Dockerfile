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

# Must use a shell so ${PORT} expands. Do NOT set a Start Command in Railway
# dashboard — it overrides this and passes "$PORT" as a literal string.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
