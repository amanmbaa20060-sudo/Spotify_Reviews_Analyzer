# Phase 6 Eval: Dashboard & API

**Phase:** 6 — Dashboard & API  
**Plan reference:** [implementationplan.md](../../implementationplan.md#phase-6-dashboard--api)  
**Depends on:** Phase 4 eval passed; Phase 5 recommended

---

## Objectives Under Test

- API exposes reviews, aggregates, and agent queries
- Dashboard answers problem-statement success criteria via UI
- Stakeholders can filter, explore, and export insights
- UAT feedback incorporated or triaged

---

## Test Checklist

### API Endpoints

| # | Test | Pass Criteria |
|---|------|---------------|
| 6.1 | `GET /reviews` with pagination | Returns filtered list; OpenAPI docs accurate |
| 6.2 | `GET /aggregates/sentiment` | Matches SQL verification for test window |
| 6.3 | `GET /aggregates/themes` | Top themes with counts correct |
| 6.4 | `GET /research-questions/{rq}` | Summary + evidence payload |
| 6.5 | `POST /agent/query` | Returns grounded response + citations |
| 6.6 | API error handling | 400/404/500 return structured JSON errors |
| 6.7 | API integration tests | ≥90% endpoint coverage in automated tests |

### Dashboard Views

| # | Test | Pass Criteria |
|---|------|---------------|
| 6.8 | Overview: sentiment by source | Chart renders; totals match API |
| 6.9 | Theme breakdown view | Top 10 themes; clickable drill-down |
| 6.10 | Time-series trend chart | Filterable by date range |
| 6.11 | RQ1–RQ6 summary pages | Each page loads with narrative + data |
| 6.12 | Segment comparison view | ≥2 segment dimensions filterable |
| 6.13 | Unmet needs ranking | Sorted by frequency × severity |
| 6.14 | Agent chat panel | User can ask question; citations visible |

### Filters & Export

| # | Test | Pass Criteria |
|---|------|---------------|
| 6.15 | Filter: date range | All views respect filter |
| 6.16 | Filter: platform (incl. social) | Correct subset shown |
| 6.17 | Filter: rating, theme, segment | Combinations work |
| 6.18 | Export CSV | Downloads valid file with expected columns |
| 6.19 | Export Markdown report | Readable stakeholder summary |

### Performance & UX

| # | Test | Pass Criteria |
|---|------|---------------|
| 6.20 | Dashboard initial load | &lt;5s on staging with full dataset |
| 6.21 | Filter apply | &lt;3s for aggregate refresh |
| 6.22 | Mobile-readable layout | Usable on tablet (not required: phone) |

### UAT (User Acceptance Testing)

Run with ≥2 Growth Team stakeholders.

| # | Test | Pass Criteria |
|---|------|---------------|
| 6.23 | Stakeholder completes 5 task script | Tasks documented below |
| 6.24 | SUS or qualitative feedback | Score ≥70 or "acceptable for internal use" |
| 6.25 | Critical UAT bugs | P0/P1 resolved or waived by PM |

#### UAT Task Script

1. View sentiment breakdown across App Store, Play Store, Reddit, and social
2. Identify top 3 recommendation frustrations for the last 90 days
3. Compare iOS vs Android discovery pain points
4. Read RQ6 unmet needs summary
5. Export a CSV for a selected theme

---

## Exit Criteria (Maps to Problem Statement Success Criteria)

- [ ] **EC-6.1** Aggregated sentiment and theme breakdowns across all integrated sources (PS success #1)
- [ ] **EC-6.2** Filters by time range, platform, rating, and segment (PS success #2)
- [ ] **EC-6.3** Each RQ1–RQ6 answerable from dashboard (PS success #3)
- [ ] **EC-6.4** Top unmet needs ranked by frequency and severity (PS success #4)
- [ ] **EC-6.5** Export for roadmap discussions (PS success #5)
- [ ] **EC-6.6** UAT passed with stakeholder sign-off
- [ ] **EC-6.7** Dashboard tech choice confirmed in [decision.md](../../decision.md) (DEC-005)

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Engineering | | | ☐ |
| Growth PM | | | ☐ |
| Stakeholder (UAT) | | | ☐ |

**Phase 6 status:** ☐ Not started · ☐ In progress · ☐ Eval passed · ☐ Blocked

**Blockers / notes:**

---
