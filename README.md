# Memora Notifications

Lightweight push notification microservice for Memora.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your VAPID keys and API key
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /subscribe | Store a push subscription |
| POST | /notify/schedule | Schedule a notification |
| DELETE | /notify/{id} | Cancel a scheduled notification |
| PUT | /notify/{id}/snooze | Snooze a notification |
| GET | /health | Health check |

## Environment Variables

| Variable | Description |
|----------|-------------|
| VAPID_PRIVATE_KEY | VAPID private key (base64url) |
| VAPID_PUBLIC_KEY | VAPID public key (base64url) |
| VAPID_CLAIMS_EMAIL | Contact email for VAPID |
| API_KEY | Shared secret for backend auth |
| DB_PATH | SQLite database path (default: notifications.db) |
| RATE_LIMIT_PER_HOUR | Max notifications per subscription per hour (default: 100) |

## Docker

```bash
docker build -t memora-notifications .
docker run -p 8001:8001 --env-file .env memora-notifications
```
