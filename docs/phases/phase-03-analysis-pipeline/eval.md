# Phase 3 Eval: Analysis Pipeline

**Phase:** 3 — Analysis Pipeline  
**Plan reference:** [implementationplan.md](../../implementationplan.md#phase-3-analysis-pipeline)  
**Depends on:** Phase 2 eval passed

---

## Objectives Under Test

- All ingested reviews processed with sentiment, themes, and RQ tags
- Classification accuracy meets minimum threshold on gold set
- Embeddings stored for retrieval
- Pipeline is batch-rerunnable without corrupting data

---

## Test Checklist

### Pipeline Execution

| # | Test | Pass Criteria |
|---|------|---------------|
| 3.1 | Process all `pending` reviews | `processing_status` → `processed` |
| 3.2 | Re-run process on `processed` reviews | Idempotent; `model_version` updated only if forced |
| 3.3 | Malformed/empty text | Marked `skipped` with reason |
| 3.4 | Batch size 100 completes | No OOM; completes in acceptable time |

### Classification Outputs

| # | Test | Pass Criteria |
|---|------|---------------|
| 3.5 | Sentiment assigned | 100% of processed records have sentiment |
| 3.6 | ≥1 theme per review | ≥90% of on-topic reviews have ≥1 theme |
| 3.7 | RQ mapping | ≥70% of on-topic reviews map to ≥1 RQ tag |
| 3.8 | Confidence score stored | All `analysis_results` have `confidence` |
| 3.9 | `model_version` recorded | Reproducibility field present |

### Accuracy (Gold Set)

Prepare a **human-labeled set of ≥100 reviews** before eval (PM + engineer).

| # | Test | Pass Criteria |
|---|------|---------------|
| 3.10 | Sentiment accuracy | ≥75% match gold labels |
| 3.11 | Theme accuracy (top-1) | ≥65% match gold primary theme |
| 3.12 | RQ tag accuracy | ≥60% match gold RQ assignment |
| 3.13 | False positive spot check | ≤15% clearly wrong themes on 50-sample audit |

### Embeddings & Retrieval

| # | Test | Pass Criteria |
|---|------|---------------|
| 3.14 | Embeddings generated | 100% of processed reviews embedded |
| 3.15 | Semantic search: "recommendations feel repetitive" | Top-5 results are plausibly relevant (manual check) |
| 3.16 | Semantic search: "can't find new music" | Top-5 results plausibly relevant |

### Quality Filtering

| # | Test | Pass Criteria |
|---|------|---------------|
| 3.17 | Spam/off-topic filter | Known spam samples marked `skipped` |
| 3.18 | Quality score | Low-quality records flagged in metadata |

### Human Validation Export

| # | Test | Pass Criteria |
|---|------|---------------|
| 3.19 | Export 100 random classified reviews | CSV with text, themes, sentiment, RQ tags |
| 3.20 | PM reviews export | Feedback documented for taxonomy v1.1 tweaks |

---

## Exit Criteria

- [ ] **EC-3.1** ≥95% of ingested on-topic reviews have `processing_status = processed`
- [ ] **EC-3.2** Gold-set accuracy meets thresholds (3.10–3.12)
- [ ] **EC-3.3** LLM/model choice documented in [decision.md](../../decision.md) (DEC-004 resolved)
- [ ] **EC-3.4** Semantic search returns relevant results for ≥4/5 test queries
- [ ] **EC-3.5** PM validation sample reviewed; taxonomy v1.1 backlog captured if needed
- [ ] **EC-3.6** Processing cost per 1,000 reviews documented

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Engineering | | | ☐ |
| Data Science | | | ☐ |
| Growth PM | | | ☐ |

**Phase 3 status:** ☐ Not started · ☐ In progress · ☐ Eval passed · ☐ Blocked

**Blockers / notes:**

---
