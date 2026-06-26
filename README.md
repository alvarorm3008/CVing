# CVing

Local app to tailor your resume to a job posting, research the company, generate a cover letter, and export submission-ready PDFs (visual and ATS-friendly).

## What it does

```
PDF/DOCX → parser (Gemini) → ATS-perfect adaptation → modern-pro PDF
                              ↘ company research + salary + cover letter
```

| Action | Output |
|--------|--------|
| **Full application** | Adapted CV, PDF, company research (salary, reviews, culture), cover letter |
| **Adapt CV only** | Adapted CV, PDF, ATS score and improvement suggestions |

## Features

- **AI:** [Google Gemini](https://aistudio.google.com/apikey) only (free tier with `gemini-2.5-flash-lite`)
- **ATS-perfect mode** by default: tailors the CV to the job without inventing experience
- **ATS panel:** score, keywords, gaps, and concrete improvements
- **Company research:** culture, pros/cons, career path, **company salary vs local market**
- **Cover letter:** inferred from CV + research (no motivation textarea required)
- **modern-pro PDF:** clean layout, clickable links (LinkedIn, GitHub), auto 1→2 pages (Playwright)
- **ATS PDF/TXT:** plain export for ATS parsers (`ats-plain`, single column, selectable text)
- **GitHub in header:** `contact.github` via `DEFAULT_GITHUB_USERNAME`
- **History** in the browser (localStorage)
- **Languages:** Spanish, English, and more (UI + CV content)

## Requirements

- Python 3.10+
- Node.js 18+
- **GEMINI_API_KEY** — [Google AI Studio](https://aistudio.google.com/apikey)
- **Playwright Chromium** — required for the visual PDF

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Edit .env and set GEMINI_API_KEY
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

## Usage

1. Paste the **job description**
2. Upload a **text-based PDF or DOCX** (not a scan) or use a saved base CV
3. Choose **output language** and optionally **translate content**
4. Click **Full application** or **Adapt CV only**
5. Review ATS score, research, cover letter, and PDF preview
6. Download **PDF**, **ATS PDF**, or **ATS TXT**; edit the CV if needed → **Update PDF**

Enable **Fast mode** to reduce Gemini API calls (recommended on the free tier).

## Environment variables (`backend/.env`)

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_FALLBACK_MODELS=gemini-2.0-flash,gemini-2.5-flash
GEMINI_MAX_RETRIES=5
GEMINI_RATE_LIMIT_RETRIES=2

# GitHub profile link in the CV header when not in the source document
DEFAULT_GITHUB_USERNAME=your-github-username
```

Never commit `.env` to GitHub. Use `.env.example` as a template only.

## API

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Backend status + Chromium |
| GET | `/templates` | Available PDF templates |
| POST | `/parse-cv` | PDF/DOCX → structured CV (JSON) |
| POST | `/adapt-cv` | Adapt CV + PDF as base64 |
| POST | `/full-application` | Full pipeline (CV + research + letter + PDF) |
| POST | `/render-pdf` | Re-render PDF (`modern-pro` or `ats-plain`) |
| POST | `/render-txt` | ATS TXT from `StructuredCV` |
| POST | `/generate-pdf` | ATS PDF from flat JSON (ATS schema) |
| POST | `/generate-txt` | ATS TXT from flat JSON |
| POST | `/preview-html` | HTML preview of the PDF (WYSIWYG) |
| POST | `/generate-cover-letter` | Cover letter only |
| POST | `/application-package` | Research + cover letter |

## PDF templates

| ID | Description |
|----|-------------|
| `modern-pro` | Visual PDF (Playwright + HTML). Default in the app. |
| `ats-plain` | Plain ATS PDF (ReportLab). “ATS PDF” button in the UI. |

## Project structure

```
CVing/
├── backend/
│   ├── main.py                 # FastAPI
│   ├── ai_client.py            # Gemini + retries / quota handling
│   ├── cv_adapter.py           # ATS-perfect adaptation
│   ├── cv_parser.py            # PDF/DOCX → JSON
│   ├── cover_letter.py         # Cover letter generation
│   ├── offer_research.py       # Company research
│   ├── salary_research.py      # Company vs local salary
│   ├── ats_cv_generator.py     # ATS PDF/TXT (ReportLab)
│   ├── html_pdf_renderer.py    # modern-pro PDF (Playwright)
│   ├── pdf_layout_engine.py    # Auto 1–2 page layout
│   ├── templates/cv_modern_pro.html
│   └── static/fonts/           # Bundled Inter fonts
└── frontend/
    └── src/App.jsx             # Main UI
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Backend unavailable | `cd backend && uvicorn main:app --reload --port 8000` |
| Visual PDF fails | `playwright install chromium` inside the venv |
| `429 RESOURCE_EXHAUSTED` | Gemini quota exceeded. Wait, use fast mode, or check [AI Studio](https://aistudio.google.com/) |
| `503` overload | Retry in 1–2 min; the backend rotates models automatically |
| Scanned PDF (no text) | Use a selectable-text PDF or DOCX |
| Invalid cover letter JSON | Retry; the backend runs an automatic second pass |

## Gemini free tier limits

**Full application** triggers multiple API calls (adapt + research + salary + letter). On the free tier you can hit per-minute or daily limits quickly. Prefer **Adapt CV only** or **Fast mode** if that happens often.

## Deployment

Portfolio setup used for this and similar full-stack projects:

| Project type | Host |
|--------------|------|
| Next.js + Supabase (main portfolio piece) | **Vercel** |
| Full-stack with Docker (CVing, etc.) | **Coolify on a Hetzner VPS** |

One VPS (~€4–5/mo) runs every Dockerized demo. No cold starts, one panel, one bill.

### Coolify (recommended for CVing)

**One-time VPS setup**

1. Create a server at [Hetzner Cloud](https://www.hetzner.com/cloud) (CX22 or similar, Ubuntu 24.04)
2. Install Coolify on the server: [coolify.io/docs](https://coolify.io/docs/get-started/installation)
3. In Coolify → **+ Add** → **New Project** → **Production**
4. **+ New** → **Application** → **Public Repository** → `alvarorm3008/CVing`
5. Build pack: **Dockerfile** (root). Port: **8000**
6. Environment variables:
   ```env
   GEMINI_API_KEY=your_key_here
   SERVE_FRONTEND=1
   DEFAULT_GITHUB_USERNAME=your-github-username
   ```
7. Deploy → assign a domain (e.g. `cving.yourdomain.com`)

Coolify rebuilds automatically on every push to `main`.

**Local production test**

```bash
cp backend/.env.example .env   # fill GEMINI_API_KEY
docker compose up --build
# → http://localhost:8000
```

### Alternatives

- **Render:** connect repo and use `render.yaml` (free tier sleeps after inactivity)
- **Railway:** uses root `Dockerfile` + `railway.toml` (paid after free credits)

Do **not** deploy this project on Vercel — Playwright/Chromium does not run there. Use Vercel only for the Next.js + Supabase portfolio app.

## License

MIT — see [LICENSE](LICENSE).
