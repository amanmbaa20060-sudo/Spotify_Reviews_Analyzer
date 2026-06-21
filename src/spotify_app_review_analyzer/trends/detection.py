from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from spotify_app_review_analyzer.db.models import AnalysisResult, Review, Source

SOCIAL_SOURCE_KEYS = frozenset({"mastodon", "bluesky", "reddit", "twitter", "tiktok"})


@dataclass(frozen=True)
class DailyThemeCount:
    theme_id: str
    source_key: str
    day: date
    count: int


@dataclass
class BurstSignal:
    theme_id: str
    source_key: str
    current_count: int
    baseline_avg: float
    multiplier: float
    day: date


@dataclass
class RisingTheme:
    theme_id: str
    source_key: str
    current_count: int
    baseline_avg: float
    growth_ratio: float


def _review_day(review: Review) -> date:
    ts = review.published_at or review.created_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC).date()


def fetch_social_reviews(session: Session, *, days: int = 7) -> list[Review]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = session.scalars(
        select(Review)
        .join(Source, Review.source_id == Source.id)
        .options(joinedload(Review.source), joinedload(Review.analysis))
        .where(
            Source.key.in_(tuple(SOCIAL_SOURCE_KEYS)),
            Review.processing_status == "processed",
        )
        .order_by(Review.published_at.desc())
    ).all()
    filtered: list[Review] = []
    for review in rows:
        ts = review.published_at or review.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if ts >= cutoff:
            filtered.append(review)
    return filtered


def compute_daily_theme_volumes(
    reviews: list[Review],
    *,
    days: int = 7,
) -> list[DailyThemeCount]:
    end_day = datetime.now(UTC).date()
    start_day = end_day - timedelta(days=days - 1)
    counts: dict[tuple[str, str, date], int] = defaultdict(int)

    for review in reviews:
        if review.source is None or review.analysis is None:
            continue
        day = _review_day(review)
        if day < start_day or day > end_day:
            continue
        for theme in review.analysis.themes or []:
            key = (theme, review.source.key, day)
            counts[key] += 1

    return [
        DailyThemeCount(theme_id=theme, source_key=source, day=day, count=count)
        for (theme, source, day), count in sorted(counts.items())
    ]


def detect_bursts(
    volumes: list[DailyThemeCount],
    *,
    threshold: float = 2.0,
) -> list[BurstSignal]:
    grouped: dict[tuple[str, str], dict[date, int]] = defaultdict(dict)
    for row in volumes:
        grouped[(row.theme_id, row.source_key)][row.day] = row.count

    signals: list[BurstSignal] = []
    for (theme_id, source_key), by_day in grouped.items():
        if len(by_day) < 2:
            continue
        sorted_days = sorted(by_day.keys())
        latest_day = sorted_days[-1]
        latest_count = by_day[latest_day]
        prior_days = sorted_days[:-1]
        if not prior_days:
            continue
        baseline = sum(by_day[d] for d in prior_days) / len(prior_days)
        if baseline <= 0:
            continue
        multiplier = latest_count / baseline
        if multiplier >= threshold:
            signals.append(
                BurstSignal(
                    theme_id=theme_id,
                    source_key=source_key,
                    current_count=latest_count,
                    baseline_avg=round(baseline, 2),
                    multiplier=round(multiplier, 2),
                    day=latest_day,
                )
            )
    return sorted(signals, key=lambda signal: (-signal.multiplier, -signal.current_count))


def top_rising_themes(
    volumes: list[DailyThemeCount],
    *,
    top_n: int = 5,
) -> list[RisingTheme]:
    grouped: dict[tuple[str, str], dict[date, int]] = defaultdict(dict)
    for row in volumes:
        grouped[(row.theme_id, row.source_key)][row.day] = row.count

    rising: list[RisingTheme] = []
    for (theme_id, source_key), by_day in grouped.items():
        sorted_days = sorted(by_day.keys())
        if len(sorted_days) < 2:
            continue
        latest_day = sorted_days[-1]
        latest_count = by_day[latest_day]
        prior_days = sorted_days[:-1]
        baseline = sum(by_day[d] for d in prior_days) / len(prior_days)
        if baseline <= 0:
            continue
        rising.append(
            RisingTheme(
                theme_id=theme_id,
                source_key=source_key,
                current_count=latest_count,
                baseline_avg=round(baseline, 2),
                growth_ratio=round(latest_count / baseline, 2),
            )
        )
    rising.sort(key=lambda item: (-item.growth_ratio, -item.current_count))
    return rising[:top_n]


def viral_summary(reviews: list[Review]) -> dict[str, int]:
    summary = {"viral": 0, "steady_state": 0}
    for review in reviews:
        state = (review.extra_metadata or {}).get("traffic_state", "steady_state")
        if state == "viral":
            summary["viral"] += 1
        else:
            summary["steady_state"] += 1
    return summary
