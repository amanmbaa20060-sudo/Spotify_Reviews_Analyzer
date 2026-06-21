## Phase 3: Analysis Pipeline

Run processing on pending reviews:

```bash
python -m process --loop --export-validation
```

Semantic search:

```bash
python -m process --search "recommendations feel repetitive"
```

Eval: `docs/phases/phase-03-analysis-pipeline/eval.md`
