# Observability Plan (light)

Goal: see what the app is doing and debug issues without heavy infra (no Prometheus/Grafana, no separate trace backend). Safe for Railway and local dev.

---

## What we care about

| Concern | Why |
|--------|-----|
| **Request correlation** | When something fails, find all logs for that request (e.g. one game create or one WS connection). |
| **Access / latency** | Know which endpoints are hit and how long they take (sanity check, no fine-grained SLAs). |
| **Service health** | Already have `/health`. Add a bit more: uptime, simple counters so a dashboard or uptime checker can confirm the app is alive and busy. |
| **Errors in one place** | Exceptions already logged; optional later: Sentry so errors show up in one UI. |

---

## In scope (light implementation)

1. **Request ID + access logging**
   - Middleware: assign `X-Request-ID` (or use incoming), put it on `request.state`, and log one line per HTTP request: `method path status duration_ms request_id`.
   - Response header `X-Request-ID` so clients can send it back (e.g. support tickets).
   - No request_id on WebSocket messages (optional later); WebSocket connect can get one and log it once.

2. **Structured logs (optional)**
   - Env `LOG_JSON=1` (e.g. on Railway): log lines as JSON (timestamp, level, message, optional extra fields). Easier for log aggregators; no new dependencies (stdlib only).

3. **Simple /metrics**
   - JSON endpoint with: `active_sessions`, `uptime_seconds`, `total_requests` (counter since boot). No Prometheus format, no client libs; enough for a simple dashboard or “is it up and busy?”.

4. **Keep existing logs**
   - Already logging errors and key events (game loop, hand history, LLM fallbacks). Keep them; ensure they use the same formatter when `LOG_JSON=1`.

---

## Out of scope (for now)

- **Distributed tracing** (OpenTelemetry, etc.): heavier; add only if you need cross-service traces.
- **Prometheus + Grafana**: more setup and infra; not “light.”
- **Sentry**: optional later; add `SENTRY_DSN` and a small middleware when you want error alerting in one place.
- **Frontend observability**: no RUM or frontend error reporting in this pass.

---

## Env vars

| Variable | Default | Effect |
|----------|---------|--------|
| `LOG_JSON` | `0` | Set to `1` to log JSON lines (for production / aggregators). |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR). |

---

## Summary

- **Request ID** on every HTTP request + one access log line and optional response header.
- **Optional JSON logging** when `LOG_JSON=1`.
- **/metrics** returning `active_sessions`, `uptime_seconds`, `total_requests`.
- No new runtime dependencies; safe for Railway and local dev.
