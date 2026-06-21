# Problem Statement: Spotify App Review Analyzer for Music Discovery Insights

## Executive Summary

Spotify has successfully acquired millions of users and built one of the world's most sophisticated music recommendation systems. Despite this technical achievement, a significant percentage of listening still comes from repeat playlists, familiar artists, and previously discovered tracks. Users are not discovering new music at the rate the product team expects, and repetitive listening behavior persists at scale.

As a Product Manager on the **Growth Team**, we need a systematic way to understand *why* users struggle with music discovery—not from internal metrics alone, but from the voices of users themselves across public channels. This document defines the problem, strategic context, and requirements for building an **App Review Analyzer** with an accompanying **insights dashboard** to surface patterns in user feedback related to discovery, recommendations, and listening behavior.

---

## Background & Context

### Company Position

Spotify operates at global scale with a mature recommendation engine powering Discover Weekly, Release Radar, Daily Mixes, Blend, AI DJ, and countless personalized surfaces. The platform's competitive advantage has long been framed around helping users find the right music at the right time.

### The Discovery Gap

Internal data suggests a meaningful share of listening sessions are **repetitive** rather than **exploratory**:

- Users return to the same playlists week after week
- Familiar artists dominate listening history
- Previously saved or liked tracks account for a large portion of play time

This behavior is not inherently negative—comfort listening is a valid use case—but it signals a gap between Spotify's discovery ambition and actual user behavior. When users *want* to discover new music but fail to do so within the product, that represents both a product experience problem and a growth opportunity.

### Why External Reviews Matter

App Store reviews, Play Store reviews, and Reddit discussions capture **unfiltered, qualitative feedback** that internal analytics cannot fully explain. Users describe frustrations in their own words: confusing UI, irrelevant recommendations, algorithm fatigue, paywall friction, and unmet listening goals. Aggregating and analyzing this feedback at scale can reveal consistent themes that inform roadmap prioritization on the Growth Team.

---

## Problem Definition

### Core Problem

**We lack a unified, scalable system to analyze public user feedback about the Spotify app and extract actionable insights related to music discovery and repetitive listening behavior.**

Today, insights from reviews and community discussions are fragmented:

| Source | Limitation Without a Dedicated System |
|--------|----------------------------------------|
| App Store reviews | Manual reading; hard to spot trends across thousands of reviews |
| Play Store reviews | Separate platform; duplicate effort; inconsistent tagging |
| Reddit discussions | Unstructured threads; noisy signal; difficult to quantify themes |

Product decisions about discovery features are often driven by internal A/B tests and quantitative metrics. Qualitative user voice is underutilized as a complementary input—especially for understanding *motivation*, *frustration*, and *unmet needs* that do not surface cleanly in event logs.

### Who Is Affected

- **End users** who want to discover new music but feel stuck in repetitive listening loops
- **Growth Team PMs** who need evidence to prioritize discovery-related experiments and features
- **Recommendation and personalization teams** who benefit from direct user language about algorithm quality
- **Design and UX teams** who need to understand friction in discovery flows (search, browse, radio, playlists, home feed)

---

## Strategic Alignment

### Company Strategic Goal

> **Increase meaningful music discovery and reduce repetitive listening behavior.**

This goal does not mean eliminating comfort listening. It means ensuring that when users *intend* to explore, Spotify makes that easy, rewarding, and habitual—and that recommendation surfaces feel fresh, relevant, and trustworthy over time.

### How This Project Supports the Goal

The App Review Analyzer bridges the gap between **what users say** and **what we build**:

1. **Identify root causes** of discovery failure from real user narratives
2. **Prioritize problems** that appear consistently across platforms and segments
3. **Validate hypotheses** from internal research with large-scale public feedback
4. **Track sentiment shifts** over time as discovery features ship

---

## Proposed Solution

### App Review Analyzer

A system that ingests, processes, and analyzes user-generated content from multiple public sources to extract structured insights about music discovery and listening behavior.

### Insights Dashboard

A dashboard that visualizes findings and enables stakeholders to explore data by theme, sentiment, platform, time period, and user segment—supporting answers to the research questions defined below.

---

## Data Sources

The analysis system must integrate feedback from:

| Source | Content Type | Value |
|--------|--------------|-------|
| **Apple App Store** | Star ratings, review text, version-specific feedback | iOS user sentiment; release-related regressions |
| **Google Play Store** | Star ratings, review text, device/OS context | Android user sentiment; platform-specific issues |
| **Reddit** | Posts and comments in Spotify-related communities | Deeper discussions; feature requests; long-form frustration |
| **Social media platforms** (e.g., X/Twitter, TikTok, Instagram, YouTube, Facebook) | Posts, comments, replies, and threads referencing Spotify discovery/recommendations | Real-time reactions to launches and experiments; broader audience sentiment; trend detection beyond review walls |

Cross-source analysis is critical: themes that appear across app stores, communities, and social platforms carry higher confidence than isolated complaints on a single channel.

---

## Research Questions

The review analysis system and dashboard must help answer the following questions. These form the primary analytical lens for tagging, clustering, and reporting.

### 1. Why do users struggle to discover new music?

Understand structural and experiential barriers: overwhelming catalog, unclear entry points, poor onboarding to discovery features, cognitive load, or habit formation toward known content.

### 2. What are the most common frustrations with recommendations?

Surface complaints about relevance, repetition, genre stagnation, mood mismatch, over-personalization, under-personalization, and perceived algorithm bias or randomness.

### 3. What listening behaviors are users trying to achieve?

Distinguish intent behind usage: background listening, focused discovery, mood regulation, social sharing, workout/focus contexts, nostalgia, artist deep-dives, and passive vs. active exploration.

### 4. What causes users to repeatedly listen to the same content?

Separate **intentional** comfort listening from **default** repetitive behavior driven by friction, habit loops, poor alternatives surfaced by the app, or anxiety about wasting time on bad recommendations.

### 5. Which user segments experience different discovery challenges?

Identify whether pain points differ by platform (iOS vs. Android), subscription tier (free vs. premium), geography, tenure (new vs. long-time users), or stated use case (e.g., podcast-heavy vs. music-primary listeners).

### 6. What unmet needs emerge consistently across reviews?

Extract recurring feature gaps, workflow failures, and emotional needs (e.g., "I want to feel surprised," "I want control," "I want less effort") that appear across App Store, Play Store, and Reddit.

---

## Goals & Objectives

### Primary Goals

1. **Centralize** public user feedback about the Spotify app into a single analyzable dataset
2. **Classify** reviews and discussions by discovery-related themes, sentiment, and behavior patterns
3. **Visualize** trends and segment differences in an accessible dashboard for Growth Team stakeholders
4. **Enable evidence-based prioritization** of discovery and anti-repetition initiatives

### Secondary Goals

- Establish a repeatable pipeline for ongoing review ingestion and analysis
- Create a shared vocabulary of discovery-related themes for cross-functional alignment
- Support before/after analysis when major discovery features or UI changes ship

---

## Success Criteria

The project will be considered successful when stakeholders can:

- [ ] View aggregated sentiment and theme breakdowns across App Store, Play Store, Reddit, and supported social media platforms
- [ ] Filter insights by time range, platform, rating, and segment
- [ ] Answer each of the six research questions with data-backed summaries
- [ ] Identify top recurring unmet needs ranked by frequency and severity
- [ ] Export or share findings for roadmap discussions and experiment design

Quantitative targets (e.g., % of reviews tagged, theme coverage, analysis refresh cadence) should be defined during technical scoping.

---

## Scope

### In Scope

- Ingestion and normalization of App Store reviews, Play Store reviews, Reddit discussions, and supported social media posts/comments that reference the Spotify app experience
- Text analysis: sentiment, topic modeling, theme classification, keyword and phrase extraction
- Dashboard for exploration, filtering, and visualization of insights
- Mapping findings to the six research questions above

### Out of Scope (Initial Phase)

- Analysis of in-app support tickets or internal customer service data
- Private or closed communities where content is not accessible via approved methods (e.g., private Facebook groups, private Discord servers)
- Direct integration with Spotify's internal recommendation or listening telemetry systems
- Automated responses or replies to user reviews

---

## Assumptions

- Public reviews and Reddit posts contain sufficient signal about discovery and recommendation pain points
- Users who leave reviews are not fully representative of the entire user base, but their verbatim feedback is uniquely valuable for qualitative depth
- Cross-platform theme consistency is a reliable indicator of product-wide issues
- Growth Team stakeholders will use dashboard insights to inform experiment design and feature prioritization

---

## Risks & Considerations

| Risk | Mitigation |
|------|------------|
| Review spam, bots, or off-topic content | Filtering, deduplication, and quality scoring |
| Platform API rate limits or ToS constraints | Robust ingestion design; compliance review |
| Social media noise and virality effects | Weighting by engagement and author quality; burst detection; separate “trend” vs “steady-state” reporting |
| Sentiment analysis misclassifying sarcasm or context | Human validation samples; confidence scores |
| Segment inference from public text is imperfect | Treat segment tags as directional, not definitive |
| Duplicate users across channels | Deduplication strategy where identifiers exist |

---

## Stakeholders

| Role | Interest |
|------|----------|
| Growth Team PM | Roadmap prioritization, discovery strategy |
| Recommendation / Personalization | Algorithm quality, relevance feedback |
| Product Design / UX | Discovery flow friction, clarity of surfaces |
| Data Science / Analytics | Methodology, validation, metric alignment |
| Engineering | Pipeline reliability, dashboard performance |

---

## Next Steps

1. **Technical discovery** — Evaluate data APIs, storage, and NLP/classification approaches for each source
2. **Taxonomy design** — Define a theme hierarchy aligned to the six research questions
3. **MVP definition** — Scope minimum viable ingestion, analysis, and dashboard views
4. **Pilot analysis** — Run initial pass on historical data to validate signal quality
5. **Stakeholder review** — Present early findings and refine dashboard requirements

---

## Summary

Spotify's recommendation technology is world-class, yet repetitive listening persists and users publicly express discovery frustrations across app stores and Reddit. The **Spotify App Review Analyzer** addresses this gap by turning scattered qualitative feedback into structured, queryable insights. The accompanying **dashboard** empowers the Growth Team to answer critical questions about why discovery fails, what users want, and which segments need the most attention—directly supporting the strategic goal of increasing meaningful music discovery across the platform.
