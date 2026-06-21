# Phase-Wise Implementation Plan: Spotify App Review Analyzer AI Agent

This document defines how we build the AI agent system in **seven phases**. Each phase has a clear objective, deliverables, dependencies, and a corresponding evaluation file with testing and exit criteria.

**Related docs**
- [problemstatement.md](./problemstatement.md)
- [architecture.md](./architecture.md)
- [decision.md](./decision.md)
- Phase evals: [phases/](./phases/)

---

## Implementation Principles

1. **Ship incrementally** — Each phase produces a demoable, testable artifact
2. **Ground before generate** — Store structured data first; agent synthesizes on top
3. **Analyze before LLM** — Build deterministic RQ1–RQ6 briefings from Phase 3 data before any Groq call
4. **Eval-driven** — No phase is complete until its `eval.md` exit criteria pass
5. **Log decisions** — Material tech/business choices go in [decision.md](./decision.md)
6. **Defer complexity** — Social sources and advanced segmentation after core pipeline works

---

## Phase Summary

| Phase | Name | Duration (est.) | Outcome |
|-------|------|-----------------|---------|
| [1](./phases/phase-01-foundation/eval.md) | Foundation & Taxonomy | 1–2 weeks | Schema, taxonomy, project skeleton, CI |
| [2](./phases/phase-02-ingestion/eval.md) | Core Ingestion | 2–3 weeks | App Store, Play Store, Reddit data in DB |
| [3](./phases/phase-03-analysis-pipeline/eval.md) | Analysis Pipeline | 2–3 weeks | Sentiment, themes, segment tags on all records |
| [4](./phases/phase-04-ai-agent/eval.md) | AI Agent (Groq) | 2–3 weeks | RQ prep analytics + Groq agent answers RQ1–RQ6 with citations |
| [5](./phases/phase-05-social-sources/eval.md) | Social Media Expansion | 2 weeks | X, TikTok, YouTube, etc. integrated |
| [6](./phases/phase-06-dashboard/eval.md) | Dashboard & API | 2–3 weeks | Stakeholder-facing insights UI + exports |
| [7](./phases/phase-07-production/eval.md) | Production & Continuous Improvement | 2 weeks | Scheduled jobs, monitoring, eval automation |

**Total estimated timeline:** 14–18 weeks (adjust based on team size and API access)

---

## Phase 1: Foundation & Taxonomy

**Objective:** Establish the project foundation, data model, and discovery-theme taxonomy aligned to the six research questions.

### Deliverables
- Repository structure (`src/`, `tests/`, `docs/`, `scripts/`)
- PostgreSQL schema migrations for core entities
- Theme taxonomy YAML/JSON (hierarchy mapped to RQ1–RQ6)
- Environment config template (`.env.example`)
- Basic logging and health-check endpoint
- CI pipeline (lint, unit tests)

### Tasks
1. Scaffold Python project with dependency management
2. Define `sources`, `reviews`, `analysis_results`, `theme_taxonomy` tables
3. Draft taxonomy v1 with PM review (≥20 leaf themes across 6 RQs)
4. Set up local dev (Docker Compose: Postgres)
5. Document setup in README

### Dependencies
- None (starting phase)

### Eval
→ [phases/phase-01-foundation/eval.md](./phases/phase-01-foundation/eval.md)

---

## Phase 2: Core Ingestion

**Objective:** Ingest and normalize reviews from App Store, Play Store, and Reddit into a unified schema.

### Deliverables
- `IngestionProvider` interface + per-source adapters
- App Store ingestion (API or approved scraper)
- Play Store ingestion
- Reddit ingestion (subreddits: r/spotify, r/truespotify, etc.)
- Deduplication and `content_hash` logic
- Scheduled or manual ingest CLI (`python -m ingest --source all`)
- Ingestion metrics (records fetched, skipped, failed)

### Tasks
1. Implement source adapters behind common interface
2. Normalize fields to canonical `reviews` schema
3. Handle pagination, rate limits, retries
4. Backfill historical data (target: ≥1,000 records per source for pilot)
5. Unit tests with mocked API responses

### Dependencies
- Phase 1 schema and config

### Eval
→ [phases/phase-02-ingestion/eval.md](./phases/phase-02-ingestion/eval.md)

---

## Phase 3: Analysis Pipeline

**Objective:** Enrich ingested reviews with sentiment, theme tags, research-question mapping, and embeddings.

### Deliverables
- Text cleaning and quality-scoring module
- Sentiment classifier (model or LLM-based)
- Theme classifier mapped to taxonomy
- Research-question tagger (RQ1–RQ6)
- Segment inference (platform, tier, tenure where detectable)
- Embedding generation + vector storage
- Batch processing worker (`python -m process --batch-size 100`)
- Human validation sample export for PM review

### Tasks
1. Build processing pipeline stages (see architecture.md)
2. Implement classification prompts or fine-tuned models
3. Store `analysis_results` with confidence scores
4. Generate embeddings for semantic search
5. Run pilot on Phase 2 backfill data
6. Measure classification accuracy on labeled sample (≥100 reviews)

### Dependencies
- Phase 2 ingested data
- Taxonomy from Phase 1
- LLM API key (decision logged)

### Eval
→ [phases/phase-03-analysis-pipeline/eval.md](./phases/phase-03-analysis-pipeline/eval.md)

---

## Phase 4: AI Agent (Groq)

**Objective:** Build a tool-using AI agent that answers discovery research questions with grounded, cited responses—using **pre-analyzed RQ briefings** and **Groq** for synthesis only.

### Strategy: Analyze Data Before Groq

Phase 3 already tags reviews with sentiment, themes, RQ mappings, segments, and embeddings. Phase 4 does **not** re-classify raw text with Groq. Instead:

1. **RQ Prep (no LLM)** — Aggregate Phase 3 outputs into per-RQ evidence packs
2. **PM review** — Export `data/exports/rq_briefing.md` for stakeholder clarity on RQ1–RQ6
3. **Groq synthesis** — Agent sends only briefing + top exemplars to Groq for narrative answers

This gives a clear, data-backed view of each research question before spending tokens and reduces hallucination risk.

### Deliverables

**RQ Prep / Analytics (pre-LLM)**
- `build_rq_briefing` tool: per-RQ theme counts, sentiment mix, top themes, segment contrasts
- Evidence selector: top-N cited review snippets per theme (diverse sources)
- Cross-source theme validation flags
- RQ gap/readiness scores (thin evidence, low confidence)
- CLI: `python -m analyze --rq all` → exports `data/exports/rq_briefing.md`
- JSON artifact: `data/exports/rq_briefing.json` for agent consumption

**AI Agent (Groq)**
- Groq client integration (`GROQ_API_KEY`, model config in `.env`)
- Agent orchestrator (LangGraph or equivalent)
- Tools: `search_reviews`, `aggregate_themes`, `compare_segments`, `build_rq_briefing`, `summarize_research_question`
- Grounding layer (citations to `review_id` + source URL)
- CLI chat interface for internal testing
- `agent_queries` audit log
- Prompt templates versioned in repo (Groq synthesis prompts)

### Tasks

**4A — RQ Prep (analyze before LLM)**
1. Implement SQL aggregations: themes and sentiment grouped by RQ1–RQ6
2. Implement evidence selection (TF-IDF + theme filters + source diversity)
3. Implement segment comparison rollups (iOS vs Android, free vs premium)
4. Implement cross-source theme detection from `analysis_results`
5. Export human-readable RQ briefing for PM review
6. Validate briefing against Phase 3 data (counts match SQL)

**4B — Groq Agent**
1. Integrate Groq API client and settings (`GROQ_API_KEY`, `GROQ_MODEL`)
2. Implement tool interfaces against DB + TF-IDF index
3. Wire agent flow: tools → `build_rq_briefing` → Groq synthesis
4. Add guardrails: no uncited claims, confidence flags, token caps
5. Test all six research questions with golden queries
6. Cost and latency benchmarking per query type

### Dependencies
- Phase 3 enriched data (`analysis_results`, `review_embeddings`)
- Groq API key
- RQ briefing complete (4A) before agent eval (4B)

### Eval
→ [phases/phase-04-ai-agent/eval.md](./phases/phase-04-ai-agent/eval.md)

**Phase 4 gate:** RQ briefing exported and reviewed; then Groq agent eval runs.

### RQ Briefing Output Shape (per research question)

Each RQ section in the briefing should include:

| Field | Example |
|-------|---------|
| `rq_id` | `rq2` |
| `review_count` | 412 |
| `top_themes` | `rq2.repetition.stale` (89), `rq2.relevance.mismatch` (54) |
| `sentiment_mix` | 62% negative, 21% neutral, 17% positive |
| `source_breakdown` | app_store 31%, play_store 48%, reddit 21% |
| `segment_signals` | iOS pain > Android on repetition (directional) |
| `cross_source_themes` | `rq2.repetition.stale` in all 3 sources |
| `exemplar_citations` | 3–5 `review_id` snippets per top theme |
| `readiness` | `high` / `medium` / `low` based on volume + confidence |

---

## Phase 5: Social Media Expansion

**Objective:** Extend ingestion and analysis to social platforms for real-time sentiment and trend detection.

### Deliverables
- Adapters for X/Twitter, TikTok, YouTube, Instagram, Facebook (prioritized by API access)
- Spotify-keyword / hashtag filtering
- Engagement metadata capture (likes, shares, views)
- Burst / trend detection module
- Separate "viral" vs "steady-state" reporting flags

### Tasks
1. Evaluate API access and ToS per platform (log in decision.md)
2. Implement highest-value source first (likely X or YouTube)
3. Apply existing normalization and processing pipeline
4. Add noise filtering for off-topic viral content
5. Validate cross-source theme detection (theme appears in ≥2 channel types)

### Dependencies
- Phase 2 ingestion patterns
- Phase 3 processing pipeline (reused)

### Eval
→ [phases/phase-05-social-sources/eval.md](./phases/phase-05-social-sources/eval.md)

---

## Phase 6: Dashboard & API

**Objective:** Deliver a stakeholder-facing dashboard and API for exploration, filtering, and export.

### Deliverables
- FastAPI REST endpoints (reviews, themes, aggregates, agent query)
- Dashboard views:
  - Sentiment & theme breakdown by source
  - Time-series trends
  - Research question summaries (RQ1–RQ6)
  - Segment comparison charts
  - Top unmet needs ranked by frequency × severity
- Filters: date range, platform, rating, theme, segment
- Export: CSV, Markdown report
- Agent chat panel in dashboard

### Tasks
1. Design dashboard wireframes with Growth PM
2. Implement API layer with pagination and caching
3. Build Streamlit MVP (or React if team prefers)
4. Connect agent chat to dashboard
5. UAT with 2–3 stakeholders

### Dependencies
- Phases 3–4 (data + agent)
- Phase 5 optional for social charts (can ship with placeholder if delayed)

### Eval
→ [phases/phase-06-dashboard/eval.md](./phases/phase-06-dashboard/eval.md)

---

## Phase 7: Production & Continuous Improvement

**Objective:** Harden the system for ongoing operation, automated evals, and iterative model/taxonomy improvement.

### Deliverables
- Scheduled ingestion and processing jobs
- Monitoring: job success, latency, LLM cost, error rates
- Automated eval suite (regression on classification + agent Q&A)
- Runbook for failures and API key rotation
- Taxonomy/prompt update workflow
- Deployment config (Docker, env docs)

### Tasks
1. Configure scheduler for daily ingest + process
2. Set up alerting on pipeline failures
3. Automate phase eval checks in CI/CD where applicable
4. Document operational procedures
5. Establish monthly taxonomy review cadence with PM

### Dependencies
- All prior phases complete

### Eval
→ [phases/phase-07-production/eval.md](./phases/phase-07-production/eval.md)

---

## Cross-Phase Milestones

| Milestone | Target Phase | Stakeholder Value |
|-----------|--------------|-------------------|
| First 1,000 reviews ingested | Phase 2 | Proof of multi-source data |
| First themed insight report | Phase 3 | Qualitative patterns visible |
| RQ1–RQ6 briefing from analytics (pre-LLM) | Phase 4A | Clear evidence before Groq |
| PM asks agent a question, gets cited Groq answer | Phase 4B | Core AI value demonstrated |
| Social trend alert | Phase 5 | Real-time signal |
| Dashboard demo to Growth Team | Phase 6 | Roadmap input ready |
| Daily automated pipeline | Phase 7 | Sustainable operations |

---

## Risk Register (Implementation)

| Risk | Phase | Mitigation |
|------|-------|------------|
| App Store / Play Store API limits | 2 | Caching, backoff, approved data vendors |
| Reddit API policy changes | 2 | Archive backfill early; abstract adapter |
| Social API cost or access | 5 | Prioritize one platform; defer others |
| Low classification accuracy | 3 | Human-labeled eval set; prompt iteration |
| Agent hallucination | 4 | Mandatory citations; RQ briefing before Groq; eval golden questions |
| Groq rate limits / model changes | 4 | Retry backoff; model pinned in config; briefings cached |
| Dashboard scope creep | 6 | MVP views only; iterate post-UAT |

---

## Team Roles (Suggested)

| Role | Phases | Focus |
|------|--------|-------|
| Backend / ML Engineer | 1–5, 7 | Ingestion, pipeline, agent |
| Frontend / Full-stack | 6 | Dashboard, API |
| Growth PM | 1, 3, 6 | Taxonomy, validation, UAT |
| Data Science | 3, 4, 7 | Eval design, accuracy metrics |

---

## How to Use This Plan

1. **Start Phase 1** — Complete tasks, run eval, log decisions
2. **Gate each phase** — Do not begin next phase until `eval.md` exit criteria pass
3. **Update decision.md** — Record stack choices, API vendors, taxonomy changes
4. **Revisit estimates** — Adjust timeline after Phase 2 (API reality check)
