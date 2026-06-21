# Decision Log

This file records **important technical and business decisions** for the Spotify App Review Analyzer AI Agent. Each entry follows an ADR-style format so future contributors understand *what* was decided, *why*, and *what alternatives were considered*.

**How to add a decision**
1. Copy the template at the bottom
2. Assign the next `DEC-XXX` ID
3. Set status: `Proposed` → `Accepted` → `Superseded` (link to replacement)

---

## Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| DEC-001 | Phase-gated delivery with per-phase eval files | Accepted | 2026-06-17 |
| DEC-002 | Python as primary implementation language | Proposed | 2026-06-17 |
| DEC-003 | PostgreSQL as primary datastore | Proposed | 2026-06-17 |
| DEC-004 | LLM provider selection | Superseded by DEC-010 | — |
| DEC-005 | Dashboard: Static HTML + FastAPI | Accepted | 2026-06-19 |
| DEC-006 | Social platform ingestion priority order | Accepted | 2026-06-19 |
| DEC-007 | Phase 2 ingestion sources and adapters | Accepted | 2026-06-17 |
| DEC-008 | SQLite default for local raw-data bootstrap | Accepted | 2026-06-18 |
| DEC-009 | Phase 3 rule-based classifier + TF-IDF embeddings | Accepted | 2026-06-18 |
| DEC-010 | Phase 4 Groq LLM + pre-LLM RQ analysis | Accepted | 2026-06-18 |
| DEC-011 | Groq model `llama-3.3-70b-versatile` and rate limits | Accepted | 2026-06-19 |

---

## DEC-001: Phase-gated delivery with per-phase eval files

**Status:** Accepted  
**Date:** 2026-06-17  
**Deciders:** Growth PM, Engineering  

### Context
The project spans ingestion, NLP, an AI agent, social sources, and a dashboard. Building everything at once risks late discovery of integration issues and unclear "done" criteria.

### Decision
Deliver in **7 phases**, each with a dedicated `eval.md` containing testing procedures and exit criteria. No phase advance until eval passes.

### Rationale
- Aligns engineering milestones with stakeholder value
- Makes quality gates explicit and auditable
- Supports incremental demos (ingestion → analysis → agent → dashboard)

### Alternatives Considered
| Alternative | Why Not Chosen |
|-------------|----------------|
| Big-bang release | High integration risk; delayed feedback |
| Continuous deploy without gates | Hard to validate research-question coverage per milestone |

### Consequences
- Slightly more documentation overhead
- Clearer project tracking and handoffs

---

## DEC-002: Python as primary implementation language

**Status:** Proposed  
**Date:** 2026-06-17  
**Deciders:** Engineering  

### Context
The system requires data pipelines, NLP, LLM agent orchestration, and API services.

### Decision
Use **Python 3.11+** for ingestion workers, processing pipeline, agent, and API (FastAPI).

### Rationale
- Rich ecosystem: LangChain/LangGraph, Hugging Face, pandas, FastAPI
- Single language across batch and agent workloads
- Team familiarity (assumed)

### Alternatives Considered
| Alternative | Why Not Chosen |
|-------------|----------------|
| Node.js for API + Python for ML | Two runtimes; more ops complexity |
| Java/Kotlin | Slower iteration for NLP/agent prototyping |

### Consequences
- Confirm Python version and dependency lock strategy in Phase 1

---

## DEC-003: PostgreSQL as primary datastore

**Status:** Proposed  
**Date:** 2026-06-17  
**Deciders:** Engineering  

### Context
Reviews need relational queries (filters, aggregations) and optional vector search.

### Decision
Use **PostgreSQL** with **pgvector** extension for embeddings when scale permits.

### Rationale
- One database for structured data and vectors (early stage)
- Strong support for JSONB metadata, time-series aggregations
- Managed Postgres available on Render and other hosts

### Alternatives Considered
| Alternative | Why Not Chosen |
|-------------|----------------|
| MongoDB | Weaker ad-hoc analytics for dashboard aggregations |
| Pinecone / dedicated vector DB | Extra service; justified only at large scale |

### Consequences
- Re-evaluate at >1M vectors if query latency degrades

---

## DEC-004: LLM provider selection

**Status:** Proposed  
**Date:** —  
**Deciders:** Engineering, Data Science  

### Context
Classification, summarization, and agent Q&A require an LLM API.

### Decision
*TBD — evaluate during Phase 3 spike.*

### Evaluation Criteria
- Classification accuracy on 100-review gold set
- Cost per 1,000 reviews processed
- Latency for agent queries (p95 < 10s target)
- Data residency / compliance requirements

### Alternatives to Evaluate
- OpenAI (GPT-4o / GPT-4o-mini)
- Anthropic (Claude)
- Open-source via hosted inference (Llama, Mistral)

---

## DEC-005: Dashboard: Static HTML + FastAPI (not Streamlit)

**Status:** Accepted  
**Date:** 2026-06-19  
**Deciders:** Growth PM, Engineering  

### Context
Stakeholders need a dashboard in Phase 6; polish requirements are uncertain. A Stitch mockup was provided as the UI target.

### Decision
Ship a **static HTML/CSS/JS dashboard** in a separate `dashboard/` folder, served by the existing **FastAPI** API layer. Revisit a React SPA only if external stakeholders or UX requirements grow beyond the current mockup.

### Rationale
- FastAPI already required for Phase 6 API endpoints; static assets mount cleanly
- Full control over Stitch mockup fidelity without Streamlit layout limits
- Agent chat, citations drawer, and exports integrate via fetch without extra framework
- `dashboard/` isolation keeps frontend separate from Python package

### Alternatives Considered
| Alternative | Why Not Chosen |
|-------------|----------------|
| Streamlit MVP (original proposal) | Harder to match Stitch design; less flexible for citation drawer / multi-view nav |
| React from day one | Slower MVP; more scope before UAT validates views |
| Grafana/Metabase only | Poor fit for agent chat and narrative RQ summaries |

### Consequences
- Dashboard JS maintained in `dashboard/static/js/`; API contract in `src/.../api/`
- Run with `api-server` CLI or `python -m spotify_app_review_analyzer.api.cli`

---

## DEC-006: Social platform ingestion priority order

**Status:** Accepted  
**Date:** 2026-06-19  
**Deciders:** Growth PM, Engineering  

### Context
Phase 5 requires social ingestion with public API access and acceptable ToS. X/Twitter, TikTok, and Meta platforms have restrictive or paid APIs.

### Decision
**Phase 5 priority sources:**
1. **Mastodon** — Public REST search API via configurable instance (`mastodon.social` default); hashtag/keyword queries
2. **Bluesky** — Public AT Protocol search API (`public.api.bsky.app`); no auth for read-only search
3. **Reddit** — Retained from Phase 2 as a social discussion source

**Deferred (documented blockers):**
- **X/Twitter** — Paid API; not required for Phase 5 gate
- **TikTok / Instagram / Facebook** — Restricted APIs; deferred to future phase

**Filtering:** Spotify keyword/hashtag relevance rules in `ingestion/social_filter.py`  
**Engagement:** likes, reposts/shares, replies captured in `metadata`  
**Trends:** burst detection (>2× 7-day theme avg) and viral vs steady-state flags

### Rationale
- Mastodon and Bluesky offer open, text-rich public search without API keys
- Reuses Phase 2 ingestion patterns and Phase 3 processing without fork
- Meets eval gate of ≥2 social platforms and ≥600 records

### Alternatives Considered
| Alternative | Why Not Chosen |
|-------------|----------------|
| X/Twitter first | API cost and access barriers on free tier |
| Scraping TikTok/Instagram | ToS risk and brittle HTML parsers |
| Social-specific NLP pipeline | Violates Phase 5 reuse requirement |

### Consequences
- CLI: `python -m ingest --source social` ingests Mastodon + Bluesky + Reddit
- CLI: `python -m trends` exports burst/trend report
- Filter rules documented in code and `social_filter_rules.py`
- **Bluesky note:** `public.api.bsky.app` returns 403 on some networks; authenticated ingest via `BLUESKY_HANDLE` + `BLUESKY_APP_PASSWORD` (app password) is supported

---

## DEC-007: Phase 2 ingestion sources and adapters

**Status:** Accepted  
**Date:** 2026-06-17  
**Deciders:** Engineering  

### Context
Phase 2 requires ingesting App Store, Play Store, and Reddit data into a unified schema with idempotent deduplication and a CLI.

### Decision
- **App Store:** Apple iTunes RSS customer reviews JSON (`itunes.apple.com/rss/customerreviews/...`) for Spotify app ID `324684580`
- **Play Store:** `google-play-scraper` library for `com.spotify.music`
- **Reddit:** Public `.json` listings from subreddits `spotify`, `truespotify`, `spotifyplaylists` with a custom User-Agent; **PullPush API** fallback when Reddit blocks requests
- **Dedup:** SHA-256 `content_hash` over normalized `source_key + text (+ title)`
- **CLI:** `python -m ingest --source all` (wrapper over `spotify_app_review_analyzer.ingestion.cli`)

### Rationale
- No paid API keys required for Phase 2 pilot
- RSS and public Reddit endpoints are sufficient for backfill and eval
- `google-play-scraper` is widely used for Play Store review extraction
- Content-hash dedup gives idempotent re-runs per eval EC-2.2

### Alternatives Considered
| Alternative | Why Not Chosen |
|-------------|----------------|
| Commercial review aggregation APIs | Added cost; defer until scale/ToS limits hit |
| PRAW for Reddit | OAuth setup overhead for read-only public data |
| Scraping App Store HTML | RSS is stable and simpler |

### Consequences
- Apple RSS capped at ~10 pages (~500 reviews); Play Store/Reddit carry bulk backfill
- Reddit rate limits require backoff and respectful User-Agent
- May need vendor APIs in production if ToS or volume limits are hit

---

## DEC-008: SQLite default for local raw-data bootstrap

**Status:** Accepted  
**Date:** 2026-06-18  
**Deciders:** Engineering  

### Context
Local development on Windows ARM lacked Docker/Postgres and `psycopg` libpq support, blocking raw data ingestion.

### Decision
Default `DATABASE_URL` to **SQLite** (`sqlite:///data/spotify_reviews.db`) for local bootstrap. PostgreSQL remains supported via `.env` for production/Docker.

### Rationale
- Zero-infra local setup
- Cross-dialect SQLAlchemy models (`Uuid`, `JSON`)
- Bootstrap script creates DB + ingests in one command

### Consequences
- Alembic migrations target Postgres; local SQLite uses `create_all`
- JSON exports in `data/raw/` provide portable raw snapshots

---

## DEC-009: Phase 3 rule-based classifier + TF-IDF embeddings

**Status:** Accepted  
**Date:** 2026-06-18  
**Deciders:** Engineering  

### Context
Phase 3 requires sentiment, theme/RQ tagging, segment inference, and embeddings without mandating paid LLM API access for local development.

### Decision
- **Classifier:** Rule/keyword-based `RuleBasedClassifier` mapped to taxonomy v1 (default `CLASSIFIER_BACKEND=rule`)
- **Embeddings:** `TfidfVectorizer` (256 features) stored in `review_embeddings` table and `data/models/`
- **CLI:** `python -m process --loop --export-validation`
- **Model version:** `rule-v1.0+tfidf-v1`
- **LLM path:** Reserved via settings for future `openai` backend (DEC-004 superseded for MVP)

### Rationale
- Works offline on Windows ARM without API keys
- Deterministic, testable, fast on ~2k reviews
- Meets Phase 3 pipeline architecture; agent phase can upgrade classifier later

### Consequences
- Theme accuracy lower than LLM on nuanced text; gold-set eval uses keyword rules
- TF-IDF semantic search is lexical; upgrade to embedding API when agent phase requires

---

## DEC-010: Phase 4 Groq LLM + pre-LLM RQ analysis

**Status:** Accepted  
**Date:** 2026-06-18  
**Deciders:** Growth PM, Engineering  

### Context
Phase 4 introduces an AI agent for RQ1–RQ6 Q&A. Sending raw reviews to an LLM is costly, slow, and increases hallucination risk. Phase 3 already provides structured tags and embeddings.

### Decision
- **LLM provider:** Groq API for synthesis and research-question answers only
- **Pre-LLM step:** Deterministic RQ Prep layer aggregates Phase 3 data into per-RQ briefings (theme counts, sentiment, segments, cited exemplars) **before** any Groq call
- **Flow:** `analyze` (local) → PM reviews briefing → `agent` (Groq) synthesizes from briefing context
- **Classification stays rule-based** (DEC-009); Groq does not re-tag ingestion data

### Rationale
- Groq offers fast inference suitable for interactive agent Q&A
- RQ briefings give stakeholders clarity on RQ1–RQ6 without token spend
- Compact evidence packs reduce cost and improve grounding

### Alternatives Considered
| Alternative | Why Not Chosen |
|-------------|----------------|
| OpenAI / Anthropic for Phase 4 | Groq chosen for speed and cost; can add fallback later |
| Groq on raw reviews | High token use; weak grounding |
| Skip pre-analysis | PM lacks visibility; agent lacks structured context |

### Consequences
- Add `GROQ_API_KEY` and `GROQ_MODEL` to `.env`
- Phase 4 split into 4A (RQ prep) and 4B (Groq agent)
- `summarize_research_question` must call `build_rq_briefing` first

---

## DEC-011: Groq model `llama-3.3-70b-versatile` and rate limits

**Status:** Accepted  
**Date:** 2026-06-19  
**Deciders:** Growth PM, Engineering  

### Context
Phase 4B integrates Groq for synthesis. The project uses Groq free-tier quotas for `llama-3.3-70b-versatile`.

### Decision
- **Model:** `llama-3.3-70b-versatile`
- **Rate limits (enforced in-app):** 30 RPM, 1K RPD, 12K TPM, 100K TPD
- **Token caps:** 8K context to Groq, 2K max output (configurable via `.env`)
- **Prompt templates:** versioned at `agent/prompts/v1.0/`

### Rationale
- Matches Growth team choice for fast inference on research Q&A
- In-app limiter prevents hard API failures during eval runs
- Compact briefing context stays under TPM budget

### Consequences
- `GroqRateLimiter` blocks/waits when quotas would be exceeded
- Golden-question runs should batch with `--runs` carefully on free tier
- Upgrade path: raise limits via env vars when Groq plan changes

---

## Template for New Decisions

```markdown
## DEC-XXX: [Short title]

**Status:** Proposed | Accepted | Superseded by DEC-YYY
**Date:** YYYY-MM-DD
**Deciders:** [Roles or names]

### Context
[What situation or problem prompted this decision?]

### Decision
[What we decided to do.]

### Rationale
[Why this option is best.]

### Alternatives Considered
| Alternative | Why Not Chosen |
|-------------|----------------|
| ... | ... |

### Consequences
[Positive and negative outcomes; follow-up actions.]
```
