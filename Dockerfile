# Multi-stage: build frontend, then backend + static assets.
# Single image serves API, WebSockets, and SPA at /.

# ---- Frontend ----
FROM node:20-slim AS frontend
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
# Same-origin deploy: API and WS on same host
ENV VITE_API_URL=
RUN npm run build

# ---- Backend ----
FROM python:3.12-slim
WORKDIR /app

COPY backend/pyproject.toml .
RUN pip install --no-cache-dir .

COPY backend/ .
COPY --from=frontend /app/dist /app/static

# No reload in production; point app at SPA assets
ENV PYTHONDONTWRITEBYTECODE=1
ENV STATIC_DIR=/app/static
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
