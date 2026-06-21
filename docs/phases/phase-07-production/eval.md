# Phase 7 Eval: Production & Continuous Improvement

**Phase:** 7 — Production & Continuous Improvement  
**Plan reference:** [implementationplan.md](../../implementationplan.md#phase-7-production--continuous-improvement)  
**Depends on:** Phase 6 eval passed

---

## Objectives Under Test

- System runs on a defined schedule without manual intervention
- Failures are detected and recoverable
- Eval suites run automatically to catch regressions
- Operational documentation is complete

---

## Test Checklist

### Scheduled Jobs

| # | Test | Pass Criteria |
|---|------|---------------|
| 7.1 | Daily ingest job | Runs successfully for 3 consecutive days |
| 7.2 | Daily process job | New records enriched within 24h of ingest |
| 7.3 | Weekly aggregate rollup | Theme/sentiment rollups updated |
| 7.4 | Job failure notification | Alert fires on simulated failure |
| 7.5 | Job retry on transient error | Recovers without manual fix |

### Monitoring & Observability

| # | Test | Pass Criteria |
|---|------|---------------|
| 7.6 | Ingest metrics dashboard or logs | `fetched`, `inserted`, `failed` visible |
| 7.7 | Processing metrics | Throughput and error rate tracked |
| 7.8 | LLM cost tracking | Daily cost estimate logged |
| 7.9 | Agent query latency (p95) | Monitored; alert if &gt;30s |
| 7.10 | Database health | Connection pool and disk monitored |

### Automated Eval Regression

| # | Test | Pass Criteria |
|---|------|---------------|
| 7.11 | Phase 3 gold-set eval in CI/schedule | Runs weekly; results archived |
| 7.12 | Phase 4 golden questions in CI/schedule | Citation coverage tracked over time |
| 7.13 | Regression alert | Notifies if accuracy drops &gt;5% vs baseline |
| 7.14 | Eval run history stored | Last 10 runs queryable or logged |

### Security & Operations

| # | Test | Pass Criteria |
|---|------|---------------|
| 7.15 | Secrets not in repo | Scan passes; env vars only |
| 7.16 | API auth on production endpoints | Unauthorized requests rejected |
| 7.17 | Backup strategy documented | Postgres backup procedure tested once |
| 7.18 | Runbook: ingest failure | Engineer can follow and recover |
| 7.19 | Runbook: LLM outage | Graceful degradation documented |

### Continuous Improvement Workflow

| # | Test | Pass Criteria |
|---|------|---------------|
| 7.20 | Misclassification feedback loop | PM flags → export → taxonomy/prompt update process |
| 7.21 | `model_version` bump procedure | Documented; reprocess command tested |
| 7.22 | Monthly review cadence | Calendar invite or doc for PM + eng |

### Deployment

| # | Test | Pass Criteria |
|---|------|---------------|
| 7.23 | Deploy from clean environment | Docker/build docs work |
| 7.24 | Rollback procedure tested | Previous version restorable |
| 7.25 | Staging ≈ production config | Parity documented |

---

## Exit Criteria

- [ ] **EC-7.1** 3 consecutive days of successful automated ingest + process
- [ ] **EC-7.2** Alerting verified for at least ingest failure and pipeline error
- [ ] **EC-7.3** Automated eval regression suite operational (7.11, 7.12)
- [ ] **EC-7.4** Runbooks complete for top 3 failure modes
- [ ] **EC-7.5** Production deployment successful with auth enabled
- [ ] **EC-7.6** LLM cost and latency baselines documented
- [ ] **EC-7.7** Handoff complete: Growth Team can use dashboard without engineering present

---

## Production Readiness Checklist

| Area | Ready |
|------|-------|
| Ingestion (all sources) | ☐ |
| Processing pipeline | ☐ |
| AI agent | ☐ |
| Dashboard + API | ☐ |
| Monitoring | ☐ |
| Runbooks | ☐ |
| Eval automation | ☐ |
| Security review | ☐ |

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Engineering | | | ☐ |
| Growth PM | | | ☐ |
| Data Science | | | ☐ |

**Phase 7 status:** ☐ Not started · ☐ In progress · ☐ Eval passed · ☐ Blocked

**Project complete:** ☐

**Blockers / notes:**

---
