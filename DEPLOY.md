# Deploying the Poker Training Engine

The app is a **single-service** stack: one container serves the API, WebSockets, and the frontend SPA. SQLite stores hand history on a volume. No Redis or separate DB required.

## Quick production run (Docker)

```bash
docker compose -f docker-compose.prod.yml up -d
```

Open **http://localhost:8000**. The API is at the same origin (`/game/...`, `/coach/...`, etc.), and WebSockets work over the same port.

## Build the image

```bash
docker build -t poker-training-engine .
```

Optional: run the container with a DB volume and env:

```bash
docker run -d -p 8000:8000 \
  -v poker_data:/data \
  -e POKER_DB_PATH=/data/poker_history.db \
  poker-training-engine
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POKER_DB_PATH` | `poker_history.db` | SQLite path; use a volume path in production. |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated origins; only needed if frontend is on another domain. |
| `STATIC_DIR` | (auto) | Set in Dockerfile; override only if you serve static elsewhere. |
| `ANTHROPIC_API_KEY` | — | Optional; enables LLM coach (Coach Claude). |

## Hosting options

### 1. **Railway** (simple, good free tier)

- Connect repo → Railway creates a service from the Dockerfile.
- Add a **volume** and set **Mount path** to `/data`; set `POKER_DB_PATH=/data/poker_history.db`.
- WebSockets and single-port deploy are supported. No extra config.

### 2. **Render** (Docker + free tier)

- New **Web Service**, connect repo, use **Docker**.
- Add **Disk** (persistent storage), mount at `/data`; set `POKER_DB_PATH=/data/poker_history.db`.
- WebSockets work on paid plans; free tier may sleep after inactivity.

### 3. **Fly.io** (global, always-on)

- Install `flyctl`, then from repo root:
  ```bash
  fly launch
  ```
  Choose no Postgres/Redis, use the Dockerfile.
- Add a **volume** and set `POKER_DB_PATH=/data/poker_history.db` with mount at `/data`.
- Scale to one VM; WebSockets and single port are supported.

### 4. **VPS (DigitalOcean, Linode, etc.)**

- SSH in, install Docker and Docker Compose.
- Clone repo and run:
  ```bash
  docker compose -f docker-compose.prod.yml up -d
  ```
- Put **Nginx** (or Caddy) in front with TLS if you want HTTPS; proxy `http://localhost:8000`.

### 5. **Vercel / Netlify (frontend only)**

- Not suitable for the **full** app: they don’t run long-lived WebSockets or your FastAPI server.
- You can deploy **only the frontend** (e.g. Vite build) and point `VITE_API_URL` at your backend URL. Then deploy the backend (API + WS) on Railway, Render, or Fly as above and set `CORS_ORIGINS` to your frontend URL.

## Checklist

- [ ] Use a **volume** (or host path) for `POKER_DB_PATH` so hand history persists across restarts.
- [ ] If frontend is on another domain, set `CORS_ORIGINS` to that origin (e.g. `https://your-app.vercel.app`).
- [ ] For the LLM coach, set `ANTHROPIC_API_KEY` in the host’s environment (never commit it).
- [ ] For HTTPS, put the app behind a reverse proxy (Nginx/Caddy) or use the host’s TLS (Railway/Render/Fly provide it).

## Health check

```bash
curl http://localhost:8000/health
```

Returns `{"status":"ok","version":"0.1.0","active_sessions":0}`.
