# Phase 2 Eval: Core Ingestion

**Phase:** 2 — Core Ingestion  
**Plan reference:** [implementationplan.md](../../implementationplan.md#phase-2-core-ingestion)  
**Depends on:** Phase 1 eval passed

---

## Objectives Under Test

- App Store, Play Store, and Reddit data ingest into unified schema
- Deduplication prevents duplicate records on re-run
- Ingestion handles rate limits and failures gracefully

---

## Test Checklist

### Adapter Interface

| # | Test | Pass Criteria |
|---|------|---------------|
| 2.1 | Each adapter implements `IngestionProvider` | Interface contract tests pass |
| 2.2 | Normalized output matches `reviews` schema | Field mapping unit tests pass |
| 2.3 | Invalid/malformed API response handled | Logged; no crash; partial batch saved |

### Per-Source Ingestion

| # | Test | Pass Criteria |
|---|------|---------------|
| 2.4 | App Store ingest (manual run) | ≥500 records stored |
| 2.5 | Play Store ingest (manual run) | ≥500 records stored |
| 2.6 | Reddit ingest (manual run) | ≥500 posts/comments stored |
| 2.7 | `rating` populated for app store records | ≥90% of store reviews have rating |
| 2.8 | `published_at` populated | ≥95% of records have valid timestamp |

### Deduplication & Idempotency

| # | Test | Pass Criteria |
|---|------|---------------|
| 2.9 | Re-run ingest on same date range | Zero duplicate `content_hash` rows |
| 2.10 | Same text, different `external_id` | Fuzzy dedup catches or flags near-duplicate |
| 2.11 | Ingest CLI `--dry-run` | Reports counts without writing |

### Reliability

| # | Test | Pass Criteria |
|---|------|---------------|
| 2.12 | Simulated rate limit (429) | Exponential backoff; eventual success |
| 2.13 | Simulated network failure | Retry up to N times; failed batch logged |
| 2.14 | Ingest metrics emitted | `fetched`, `inserted`, `skipped`, `failed` logged |

### Data Quality Spot Check

| # | Test | Pass Criteria |
|---|------|---------------|
| 2.15 | Manual review of 50 random records | ≥80% clearly about Spotify app/experience |
| 2.16 | Source distribution query | All 3 sources represented in DB |

---

## Exit Criteria

- [ ] **EC-2.1** ≥1,000 total records ingested across all three sources
- [ ] **EC-2.2** Re-ingestion is idempotent (no duplicate growth)
- [ ] **EC-2.3** Ingest CLI documented and runnable: `python -m ingest --source all`
- [ ] **EC-2.4** API/rate-limit handling verified with at least one failure injection test
- [ ] **EC-2.5** Data quality spot check ≥80% on-topic (document sample methodology)
- [ ] **EC-2.6** Ingestion approach per source logged in [decision.md](../../decision.md) if non-obvious (API vendor, subreddit list)

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Engineering | | | ☐ |
| Growth PM | | | ☐ |

**Phase 2 status:** ☐ Not started · ☐ In progress · ☐ Eval passed · ☐ Blocked

**Blockers / notes:**

---
