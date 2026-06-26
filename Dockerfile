# Stage 1 — build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2 — FastAPI + Playwright (serves API + static frontend)
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-build /app/frontend/dist ./static/app

ENV PORT=8000
ENV SERVE_FRONTEND=1
EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
