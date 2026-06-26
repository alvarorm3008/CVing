# CVing on Render (free tier)

## 1. Create Render account

1. Go to https://render.com → **Get Started** (GitHub login works)
2. No credit card needed for free tier

## 2. Deploy with Blueprint

1. Dashboard → **New** → **Blueprint**
2. Connect GitHub → select repo `alvarorm3008/CVing`
3. Render reads `render.yaml` automatically
4. When prompted, set:
   - `GEMINI_API_KEY` — from your local `backend/.env` or [Google AI Studio](https://aistudio.google.com/apikey)
   - `DEFAULT_GITHUB_USERNAME` — `alvarorm3008` (optional)
5. Click **Apply**

First Docker build takes ~10–15 min. You get a URL like `https://cving.onrender.com`.

## 3. After deploy

- Every push to `main` → auto-redeploy
- Free tier **sleeps after 15 min** without traffic → first visit may take ~30–60 s
- Visual PDF needs Chromium (~512 MB RAM on free tier — may be tight; ATS PDF always works)

## 4. Test

1. Open your Render URL
2. Wait for cold start if it slept
3. Paste a job description + upload a CV
4. Check `/health` returns OK

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails | Check Render logs; Docker image is large (Playwright) |
| OOM / PDF visual fails | Free tier RAM limit — use **ATS PDF** button instead |
| 503 on first load | Cold start — wait and refresh |
| `GEMINI_API_KEY` missing | Add in Render → Environment |

## Local test (optional)

```bash
cp backend/.env.example .env   # add GEMINI_API_KEY
docker compose up --build
```
