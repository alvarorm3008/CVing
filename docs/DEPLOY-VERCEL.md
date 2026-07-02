# Frontend on Vercel + backend on Render (recommended)

**Why:** Vercel serves the React app from a global CDN (fast). Render runs the API + Playwright PDF. Render is slow for static sites on the free tier (cold starts, no CDN) — not ideal as your main UI host.

| Layer | Host | URL users open |
|-------|------|----------------|
| Frontend | **Vercel** | `https://cving.vercel.app` |
| Backend | **Render** (`Dockerfile.api`) | only API calls |

## 1. Backend on Render

The repo `render.yaml` uses **`Dockerfile.api`** (no frontend build → faster deploys, smaller image).

1. Render → Blueprint → connect GitHub repo
2. Set `GEMINI_API_KEY`
3. Note the URL: `https://cving.onrender.com` (yours may differ)

Free tier **sleeps after 15 min** — the first API request can take **30–60 s**. The Vercel UI stays fast; only AI/PDF actions wait.

## 2. Frontend on Vercel

1. Import repo on Vercel (root `vercel.json` builds `frontend/`)
2. **Settings → Environment Variables:**

   `VITE_API_URL` = `https://YOUR-SERVICE.onrender.com` (no trailing slash)

3. **Redeploy** after adding the variable (required for Vite)

## 3. Verify

- `https://YOUR-SERVICE.onrender.com/health` → OK
- Vercel site → no «Backend no disponible» banner
- First action after idle → may show «Despertando backend…» then works

## CORS

`*.vercel.app` is already allowed. Custom domain:

```
ALLOWED_ORIGINS=https://cving.tudominio.com
```

(on Render → Environment)

## All-in-one on Render only

If you want a single URL without Vercel, change `render.yaml` to `dockerfilePath: ./Dockerfile` and `SERVE_FRONTEND: "1"`. Simpler, but the UI will feel slower than Vercel on free tier.
