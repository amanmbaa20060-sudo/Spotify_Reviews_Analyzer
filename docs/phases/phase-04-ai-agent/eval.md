# Phase 4 Eval: AI Agent (Groq)

**Phase:** 4 — AI Agent (Groq)  
**Plan reference:** [implementationplan.md](../../implementationplan.md#phase-4-ai-agent-groq)  
**Depends on:** Phase 3 eval passed

**Gate:** Complete **Phase 4A (RQ Prep)** before **Phase 4B (Groq agent)** eval.

---

## Phase 4A: RQ Prep (Pre-LLM) Exit Criteria

- [ ] **EC-4A.1** `python -m analyze --rq all` exports `data/exports/rq_briefing.md` and `.json`
- [ ] **EC-4A.2** All six RQs have theme counts, sentiment mix, and ≥3 exemplar citations
- [ ] **EC-4A.3** Aggregated counts match SQL verification queries
- [ ] **EC-4A.4** PM sign-off on RQ briefing accuracy (directional)

---

## Objectives Under Test (Phase 4B)

- Agent answers all six research questions with grounded citations
- Tool calls return correct structured data
- Guardrails prevent unsupported claims
- Query latency and cost within targets

---

## Golden Questions (Agent Q&A)

Each question must be run **3 times**; pass if ≥2/3 runs meet criteria.

| RQ | Golden Question | Pass Criteria |
|----|-----------------|---------------|
| RQ1 | "Why do users struggle to discover new music?" | Cites ≥3 reviews; names ≥2 distinct barriers |
| RQ2 | "What are the most common frustrations with recommendations?" | Cites ≥3 reviews; lists top themes with counts or ranking |
| RQ3 | "What listening behaviors are users trying to achieve?" | Identifies ≥3 behavior intents with examples |
| RQ4 | "What causes users to repeat the same content?" | Distinguishes comfort vs friction-driven repetition |
| RQ5 | "Which segments have different discovery challenges?" | Compares ≥2 segments with evidence (even if directional) |
| RQ6 | "What unmet needs appear consistently?" | Lists ≥3 needs with cross-source or frequency support |

---

## Test Checklist

### Tool Functionality

| # | Test | Pass Criteria |
|---|------|---------------|
| 4.1 | `search_reviews` with filters | Returns paginated, filtered results |
| 4.2 | `aggregate_themes` for last 90 days | Counts match SQL verification query |
| 4.3 | `compare_segments` iOS vs Android | Side-by-side metrics returned |
| 4.4 | `summarize_research_question` RQ2 | Structured summary + evidence |
| 4.5 | `detect_cross_source_themes` | Reports presence across ≥2 sources |

### Grounding & Guardrails

| # | Test | Pass Criteria |
|---|------|---------------|
| 4.6 | Every factual claim has citation | `review_id` or source link in response |
| 4.7 | Prompt: "What is Spotify's revenue?" | Refuses or states out of scope |
| 4.8 | Empty result set query | Agent states insufficient data; no fabrication |
| 4.9 | Low-confidence classifications | Flagged when used as evidence |

### Agent Behavior

| # | Test | Pass Criteria |
|---|------|---------------|
| 4.10 | Multi-step query: "Compare Reddit vs App Store sentiment on recommendations" | Uses ≥2 tools; coherent synthesis |
| 4.11 | Follow-up question in session | Maintains context correctly |
| 4.12 | `agent_queries` audit log | All queries and tool calls logged |

### Performance & Cost

| # | Test | Pass Criteria |
|---|------|---------------|
| 4.13 | Simple query latency (p95) | &lt;10 seconds |
| 4.14 | Complex multi-tool query (p95) | &lt;30 seconds |
| 4.15 | Cost per golden question set (18 runs) | Documented; within agreed budget |

### Regression Suite

| # | Test | Pass Criteria |
|---|------|---------------|
| 4.16 | Automated golden-question script | Runnable in CI or scheduled job |
| 4.17 | Citation coverage metric | ≥90% of claims have citations on golden set |

---

## Exit Criteria

- [ ] **EC-4.1** All six golden questions pass (≥2/3 runs each)
- [ ] **EC-4.2** Citation coverage ≥90% on golden set
- [ ] **EC-4.3** No hallucination failures on out-of-scope or empty-data tests (4.7, 4.8)
- [ ] **EC-4.4** Agent CLI available for internal use
- [ ] **EC-4.5** Latency targets met (4.13, 4.14)
- [ ] **EC-4.6** Prompt templates versioned in repo

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Engineering | | | ☐ |
| Data Science | | | ☐ |
| Growth PM | | | ☐ |

**Phase 4 status:** ☐ Not started · ☐ In progress · ☐ Eval passed · ☐ Blocked

**Blockers / notes:**

---
