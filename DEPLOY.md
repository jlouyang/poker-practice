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
| `LOG_JSON` | `0` | Set to `1` for JSON log lines (e.g. production / log aggregators). |
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR. |

## Hosting options

### 1. **Railway** (recommended)

The repo includes `railway.toml` and a Dockerfile that uses Railway’s `PORT`. No custom start command needed.

**Steps:**

1. **New project** → Deploy from GitHub repo (connect and select this repo).
2. **Service** → Railway will detect the root `Dockerfile` and build it. No need to set a build command.
3. **Port** → Railway injects `PORT` at runtime; the container listens on it automatically.
4. **Volume (for hand history)**  
   - In the service: **Variables** → **Volumes** → **Add Volume**.  
   - Set **Mount path** to `/data`.  
   - The app will use `RAILWAY_VOLUME_MOUNT_PATH` and store the SQLite DB at `/data/poker_history.db` by default.  
   - To use a different path, set `POKER_DB_PATH` (e.g. `POKER_DB_PATH=/data/poker_history.db`).
5. **Optional env vars**  
   - `ANTHROPIC_API_KEY` — for the LLM coach (Coach Claude).  
   - `CORS_ORIGINS` — only if you host the frontend elsewhere (e.g. `https://your-app.vercel.app`).
6. **Deploy** → Push to the linked branch or trigger a deploy from the dashboard. Health checks use `/health` (see `railway.toml`).

**If a deploy fails:** check the deploy logs. Typical causes: app not binding to `0.0.0.0`, or not listening on the injected `PORT`. This setup uses `PORT` in the Dockerfile CMD and binds to `0.0.0.0`.

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

## Health and metrics

**Health:** `GET /health` → `{"status":"ok","version":"0.1.0","active_sessions":0}`.

**Metrics (light):** `GET /metrics` → JSON with `uptime_seconds`, `active_sessions`, `total_requests` (since boot). No Prometheus dependency; useful for dashboards or uptime checks.

Every HTTP response includes an `X-Request-ID` header for log correlation; you can send the same header on retries to keep the same id.
