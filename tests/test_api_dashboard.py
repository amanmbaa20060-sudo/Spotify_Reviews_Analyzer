from __future__ import annotations

from fastapi.testclient import TestClient

from spotify_app_review_analyzer.api.app import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_dashboard_index() -> None:
    res = client.get("/")
    assert res.status_code == 200


def test_overview_includes_app_store_with_date_filter() -> None:
    """App Store KPIs must appear when since_days filter is active."""
    res = client.get("/api/overview?since_days=30")
    assert res.status_code == 200
    data = res.json()
    assert data["app_store"]["count"] > 0
    assert data["app_store"]["average"] is not None


def test_reviews_pagination() -> None:
    res = client.get("/api/reviews?limit=5&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data


def test_recent_feedback_app_store() -> None:
    res = client.get("/api/reviews/recent?source_key=app_store&limit=8")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    assert len(data["items"]) > 0
    assert all(item["source_key"] == "app_store" for item in data["items"])
    assert all(item["rating"] is not None for item in data["items"])
    assert all(item["sentiment"] in {"positive", "negative", "neutral"} for item in data["items"])


def test_research_questions() -> None:
    res = client.get("/api/research-questions")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 6


def test_rq_problem_analysis_endpoint() -> None:
    res = client.get("/api/research-questions/rq1/problem-analysis")
    assert res.status_code == 200
    data = res.json()
    pa = data["problem_analysis"]
    assert pa["root_causes"]
    assert abs(sum(c["weight"] for c in pa["root_causes"]) - 100.0) < 1.0
    assert data["problem_summary"]


def test_rq_top_evidence_endpoint() -> None:
    res = client.get("/api/research-questions/rq1/top-evidence")
    assert res.status_code == 200
    data = res.json()
    assert data["rq_id"] == "rq1"
    assert data["total"] > 0
    assert all(item["sentiment"] == "negative" for item in data["items"])


def test_research_question_rq2() -> None:
    res = client.get("/api/research-questions/rq2")
    assert res.status_code == 200
    data = res.json()
    assert data["rq_id"] == "rq2"
    assert data["exemplar_citations"]
    assert "top_evidence" in data
    assert "problem_analysis" in data
    pa = data["problem_analysis"]
    assert pa["root_causes"]
    assert abs(sum(c["weight"] for c in pa["root_causes"]) - 100.0) < 1.0
    assert len(data["top_evidence"]) <= 5
    if data["top_evidence"]:
        item = data["top_evidence"][0]
        assert "snippet" in item
        assert "theme_label" in item
        assert item["sentiment"] == "negative"
        assert all(e["sentiment"] == "negative" for e in data["top_evidence"])


def test_aggregates_sentiment() -> None:
    res = client.get("/api/aggregates/sentiment")
    assert res.status_code == 200
    assert "items" in res.json()


def test_unknown_rq_404() -> None:
    res = client.get("/api/research-questions/rq99")
    assert res.status_code == 404


def test_export_csv() -> None:
    res = client.get("/api/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "review_id" in res.text


def test_export_markdown() -> None:
    res = client.get("/api/export/markdown")
    assert res.status_code == 200
    assert "text/markdown" in res.headers.get("content-type", "")


def test_aggregates_themes() -> None:
    res = client.get("/api/aggregates/themes?limit=5")
    assert res.status_code == 200
    assert "items" in res.json()


def test_aggregates_ratings() -> None:
    res = client.get("/api/aggregates/ratings")
    assert res.status_code == 200
    assert "items" in res.json()


def test_word_cloud() -> None:
    res = client.get("/api/word-cloud")
    assert res.status_code == 200
    assert "items" in res.json()


def test_unmet_needs() -> None:
    res = client.get("/api/unmet-needs")
    assert res.status_code == 200
    assert "items" in res.json()


def test_reviews_filter_source() -> None:
    res = client.get("/api/reviews?source_key=reddit&limit=3")
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert item["source_key"] == "reddit"


def test_agent_query_validation() -> None:
    res = client.post("/api/agent/query", json={"question": "ab"})
    assert res.status_code == 422
