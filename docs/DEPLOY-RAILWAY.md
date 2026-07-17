# Frontend on Vercel + backend on Railway (Docker, Root Directory = /backend)

| Layer | Host | Domain |
|-------|------|--------|
| Frontend | **Vercel** | `https://cvingapi.alvarorodriguez.dev` |
| Backend | **Railway** | `https://api.alvarorodriguez.dev` |

## 1. Railway

1. Service → **Root Directory** = `backend`
2. Builder: Docker (uses `backend/railway.toml` → `backend/Dockerfile`)
3. **Settings → Deploy → Start Command: leave EMPTY**  
   (if you set `uvicorn ... --port $PORT`, Railway runs it without a shell and `$PORT` stays literal → crash → healthcheck fails)
4. Variables:

```
AI_PROVIDER=gemini
GEMINI_API_KEY=…          # only in Railway dashboard, never in git
GEMINI_MODEL=gemini-2.5-flash-lite
SERVE_FRONTEND=0
ALLOWED_ORIGINS=https://cvingapi.alvarorodriguez.dev
```

4. Custom domain: `api.alvarorodriguez.dev` (Porkbun CNAME → Railway)
5. Healthcheck: `/health`
6. Verify: `https://api.alvarorodriguez.dev/health`

## 2. Vercel

```
VITE_API_URL=https://api.alvarorodriguez.dev
```

Custom domain: `cvingapi.alvarorodriguez.dev`. **Redeploy** after setting `VITE_API_URL`.

## 3. Porkbun DNS

| Host | Type | Value |
|------|------|--------|
| `api` | CNAME | lo que te dé Railway |
| `cvingapi` | CNAME | `cname.vercel-dns.com` (o el que indique Vercel) |

## Secrets

`GEMINI_API_KEY` lives in:
- local: `backend/.env` (gitignored)
- production: Railway Variables only

Never commit real keys. Template only: `backend/.env.example`.
