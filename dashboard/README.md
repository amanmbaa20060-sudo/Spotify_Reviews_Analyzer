# Spotify App Review Analyzer — Dashboard (Phase 6)

Stakeholder dashboard UI based on the Google Stitch mockup (`assets/design-reference.png`).

## Run locally (with API)

From project root:

```bash
python -m spotify_app_review_analyzer.api.cli --port 8000
```

Open http://127.0.0.1:8000

The dashboard uses `/api` on the same origin when served by FastAPI.

## Deploy frontend on Vercel

The API runs separately on Render. Vercel serves only the static `dashboard/` folder.

1. Import the GitHub repo in [Vercel](https://vercel.com/new).
2. Leave **Root Directory** as the repo root (default). `vercel.json` sets `outputDirectory` to `dashboard`.
3. Add an environment variable:

| Variable | Example | Required |
|----------|---------|----------|
| `API_BASE_URL` | `https://spotify-review-analyzer-api.onrender.com` | Yes |

No trailing slash. The build writes `dashboard/static/js/config.js` so the UI calls your Render backend.

4. Deploy. Open your `*.vercel.app` URL.

**Build command** (from `vercel.json`): `python scripts/vercel_build.py`

CORS is enabled on the FastAPI backend (`allow_origins=["*"]`), so cross-origin requests from Vercel work.

## Structure

```
dashboard/
  index.html          # Main SPA shell
  assets/
    design-reference.png
  static/
    css/dashboard.css
    js/dashboard.js
```

## API (FastAPI)

| Endpoint | Description |
|----------|-------------|
| `GET /api/overview` | KPIs, ratings, sentiment |
| `GET /api/reviews` | Paginated reviews with filters |
| `GET /api/aggregates/sentiment` | Sentiment by source |
| `GET /api/aggregates/themes` | Top themes |
| `GET /api/aggregates/ratings` | Star rating distribution |
| `GET /api/research-questions` | RQ1–RQ6 with citations |
| `GET /api/word-cloud` | Theme word cloud data |
| `POST /api/agent/query` | Groq agent Q&A |
| `GET /api/export/csv` | CSV export |
| `GET /api/export/markdown` | RQ briefing markdown |

## Views

- **Overview** — KPIs, active RQ panel, citations, feedback, word cloud
- **Sentiment** — Source sentiment table + rating chart
- **Themes** — Full theme list + unmet needs
- **Research** — All six RQ cards
- **Agent Chat** — Ask grounded research questions
