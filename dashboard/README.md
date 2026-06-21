# Spotify App Review Analyzer — Dashboard (Phase 6)

Stakeholder dashboard UI based on the Google Stitch mockup (`assets/design-reference.png`).

## Run

From project root:

```bash
python -m spotify_app_review_analyzer.api.cli --port 8000
```

Open http://127.0.0.1:8000

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
