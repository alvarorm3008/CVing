# CVing — Coolify deploy checklist

## 1. Hetzner VPS

1. Go to https://www.hetzner.com/cloud
2. Create account → **New Project** → **Add Server**
3. Settings:
   - Location: Falkenstein or Nuremberg (EU)
   - Image: **Ubuntu 24.04**
   - Type: **CX22** (2 vCPU, 4 GB RAM — enough for CVing + Playwright)
   - Networking: IPv4 + IPv6
   - SSH key: add yours (`cat ~/.ssh/id_ed25519.pub` or generate with `ssh-keygen`)
4. Create server → copy the **IP address**

## 2. Install Coolify (on the VPS)

```bash
ssh root@YOUR_SERVER_IP
```

Then either:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

Or upload and run `scripts/setup-hetzner-coolify.sh`.

Open Coolify in browser: `http://YOUR_SERVER_IP:8000` (or the URL shown after install).

## 3. Coolify first-time setup

1. Create admin account (email + password)
2. **Settings** → connect **GitHub** (OAuth)
3. **+ New Project** → name it `portfolio`

## 4. Deploy CVing

1. **+ New** → **Application** → **Public Repository**
2. URL: `https://github.com/alvarorm3008/CVing`
3. Branch: `main`
4. Build pack: **Dockerfile** (root)
5. Port: **8000**
6. Environment variables:

   | Key | Value |
   |-----|-------|
   | `GEMINI_API_KEY` | your key from Google AI Studio |
   | `SERVE_FRONTEND` | `1` |
   | `DEFAULT_GITHUB_USERNAME` | `alvarorm3008` (optional) |

7. **Deploy**

## 5. After deploy

- Coolify gives a URL like `http://YOUR_SERVER_IP:PORT` or a `*.sslip.io` domain
- Test: open URL → upload a CV → check PDF generation
- **Auto deploy**: enabled by default on push to `main`

## 6. Firewall (Hetzner)

In Hetzner Cloud → server → **Firewalls** (or Networking):
- Allow TCP **22** (SSH)
- Allow TCP **80**, **443** (Coolify proxy)
- Allow TCP **8000** if needed during setup

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails on Playwright | Dockerfile uses official Playwright image — should work |
| App unhealthy | Check logs in Coolify; `/health` must return 200 |
| PDF fails | `GEMINI_API_KEY` missing or invalid |
| Slow first load | Normal — Chromium cold start |
