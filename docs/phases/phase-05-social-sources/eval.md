# Phase 5 Eval: Social Media Expansion

**Phase:** 5 — Social Media Expansion  
**Plan reference:** [implementationplan.md](../../implementationplan.md#phase-5-social-media-expansion)  
**Depends on:** Phase 3 eval passed (Phase 4 may run in parallel)

---

## Objectives Under Test

- Social platform data ingests through existing pipeline
- Spotify-relevant filtering reduces noise
- Engagement metadata captured for trend analysis
- Cross-source themes detectable across app stores + social

---

## Test Checklist

### Source Integration

| # | Test | Pass Criteria |
|---|------|---------------|
| 5.1 | Priority source #1 ingests (per DEC-006) | ≥300 records stored |
| 5.2 | Priority source #2 ingests | ≥300 records stored |
| 5.3 | Social records normalized to `reviews` schema | Field mapping tests pass |
| 5.4 | `metadata` includes engagement fields | likes, shares, views, or equivalent |

### Relevance Filtering

| # | Test | Pass Criteria |
|---|------|---------------|
| 5.5 | Keyword/hashtag filter applied | Off-topic rate ≤30% on 50-sample audit |
| 5.6 | Non-Spotify viral posts excluded | Manual check on known noise examples |
| 5.7 | Filter rules documented | Config file or decision log entry |

### Processing Reuse

| # | Test | Pass Criteria |
|---|------|---------------|
| 5.8 | Social records processed by Phase 3 pipeline | Sentiment + themes assigned |
| 5.9 | No social-specific pipeline fork | Same worker handles all sources |

### Trend & Burst Detection

| # | Test | Pass Criteria |
|---|------|---------------|
| 5.10 | Burst detection on theme spike | Flags when theme volume &gt;2× 7-day avg |
| 5.11 | Viral vs steady-state flag | High-engagement outliers tagged |
| 5.12 | Trend report for last 7 days | Lists top 5 rising themes on social |

### Cross-Source Analysis

| # | Test | Pass Criteria |
|---|------|---------------|
| 5.13 | Theme appears in app store + social | `detect_cross_source_themes` finds it |
| 5.14 | Agent query: "What's trending on social about recommendations?" | Grounded answer with social citations |

### Compliance

| # | Test | Pass Criteria |
|---|------|---------------|
| 5.15 | ToS and API usage documented | Per platform in decision log |
| 5.16 | Rate limits respected | No sustained 429 failures in ingest logs |

---

## Exit Criteria

- [ ] **EC-5.1** ≥2 social platforms ingesting successfully (or ≥1 with documented blockers for others in decision log)
- [ ] **EC-5.2** ≥600 total social records ingested and processed
- [ ] **EC-5.3** On-topic rate ≥70% on audited sample
- [ ] **EC-5.4** Burst/trend module operational with at least one verified spike detection
- [ ] **EC-5.5** Cross-source theme detection validated on ≥3 known themes
- [ ] **EC-5.6** DEC-006 finalized in [decision.md](../../decision.md)

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Engineering | | | ☐ |
| Growth PM | | | ☐ |

**Phase 5 status:** ☐ Not started · ☐ In progress · ☐ Eval passed · ☐ Blocked

**Blockers / notes:**

---
