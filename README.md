## Spotify App Review Analyzer

An AI agent system to ingest public user feedback (app stores, Reddit, social), analyze it (themes/sentiment/segments), and surface grounded insights via an agent interface and dashboard.

### Docs

- `docs/problemstatement.md`
- `docs/architecture.md`
- `docs/implementationplan.md`
- `docs/decision.md`
- Phase evals: `docs/phases/`

### Prerequisites

- Python 3.11+
- Docker Desktop (for PostgreSQL)

### Get raw data (one command)

Bootstrap the local SQLite database and ingest from all sources:

```bash
pip install -e ".[dev]"
python -m spotify_app_review_analyzer.scripts.bootstrap_raw_data
```

This will:
1. Create `.env` from `.env.example` (if missing)
2. Initialize `data/spotify_reviews.db`
3. Ingest App Store, Play Store, and Reddit reviews
4. Export JSON snapshots to `data/raw/`

### Local development (Phase 1)

Start Postgres (optional — only if using PostgreSQL instead of SQLite):

```bash
docker compose up -d
```

Create a virtualenv and install deps:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -e .[dev]
```

Set env vars:

```bash
copy .env.example .env
```

Run migrations (PostgreSQL only):

```bash
alembic upgrade head
```

Run the API:

```bash
uvicorn spotify_app_review_analyzer.api.app:app --reload
```

Health check:

- `GET http://localhost:8000/health`

### Ingestion (Phase 2)

```bash
python -m ingest --source all
```

Options:

- `--source app_store|play_store|reddit|all`
- `--limit 500` (max records per source)
- `--dry-run` (fetch and count without writing)

Example:

```bash
python -m ingest --source reddit --limit 200
python -m ingest --source all --dry-run
```

### Processing (Phase 3)

Classify pending reviews (sentiment, themes, RQ tags, segments) and build TF-IDF embeddings:

```bash
python -m process --loop --export-validation
```

Semantic search:

```bash
python -m process --search "can't find new music"
```

