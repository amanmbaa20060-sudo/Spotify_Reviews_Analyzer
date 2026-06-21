## Phase 2: Core Ingestion

Implemented ingestion module: `src/spotify_app_review_analyzer/ingestion/`

### Run

```bash
python -m ingest --source all
python -m ingest --source app_store --limit 500 --dry-run
```

### Eval

- `docs/phases/phase-02-ingestion/eval.md`
