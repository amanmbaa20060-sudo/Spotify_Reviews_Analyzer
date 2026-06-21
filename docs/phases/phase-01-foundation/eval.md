# Phase 1 Eval: Foundation & Taxonomy

**Phase:** 1 — Foundation & Taxonomy  
**Plan reference:** [implementationplan.md](../../implementationplan.md#phase-1-foundation--taxonomy)

---

## Objectives Under Test

- Project skeleton is runnable locally
- Database schema supports ingestion and analysis workflows
- Theme taxonomy maps to all six research questions
- CI runs on every push

---

## Test Checklist

### Environment & Repo

| # | Test | Pass Criteria |
|---|------|---------------|
| 1.1 | Clone repo and follow README setup | Dev environment runs without undocumented steps |
| 1.2 | `docker compose up` starts Postgres | Health check passes |
| 1.3 | Run database migrations | All tables created without error |
| 1.4 | `.env.example` documents required vars | No secret values committed |

### Schema Validation

| # | Test | Pass Criteria |
|---|------|---------------|
| 1.5 | Insert mock `sources` row | FK constraints work |
| 1.6 | Insert mock `reviews` row | All required fields enforced |
| 1.7 | Insert mock `analysis_results` row | FK to `reviews` enforced |
| 1.8 | Query reviews by `source_id` + date range | Index performs acceptably on seed data |

### Taxonomy

| # | Test | Pass Criteria |
|---|------|---------------|
| 1.9 | Taxonomy file loads programmatically | Valid YAML/JSON; no duplicate IDs |
| 1.10 | Every RQ1–RQ6 has ≥3 leaf themes | PM sign-off documented |
| 1.11 | Theme hierarchy depth ≤ 3 levels | Navigable for classifiers |

### CI & Quality

| # | Test | Pass Criteria |
|---|------|---------------|
| 1.12 | CI pipeline runs lint | Zero blocking errors |
| 1.13 | CI pipeline runs unit tests | All pass |
| 1.14 | Health endpoint returns 200 | `GET /health` → `{"status": "ok"}` |

---

## Exit Criteria

All of the following must be true to exit Phase 1:

- [ ] **EC-1.1** Repository structure matches architecture conventions (`src/`, `tests/`, `docs/`, `scripts/`)
- [ ] **EC-1.2** PostgreSQL schema migrated and documented (ER diagram or table list in docs)
- [ ] **EC-1.3** Theme taxonomy v1 approved by Growth PM with coverage across RQ1–RQ6
- [ ] **EC-1.4** Local dev reproducible in &lt;30 minutes for a new engineer
- [ ] **EC-1.5** CI green on default branch
- [ ] **EC-1.6** At least one decision logged in [decision.md](../../decision.md) if stack choices finalized

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Engineering | | | ☐ |
| Growth PM | | | ☐ |

**Phase 1 status:** ☐ Not started · ☐ In progress · ☐ Eval passed · ☐ Blocked

**Blockers / notes:**

---
