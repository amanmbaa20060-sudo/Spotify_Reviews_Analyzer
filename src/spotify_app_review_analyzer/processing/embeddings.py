from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from spotify_app_review_analyzer.core.settings import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchHit:
    review_id: str
    score: float
    text: str


class EmbeddingStore:
    def __init__(self, model_dir: Path | None = None) -> None:
        self.model_dir = Path(model_dir or settings.embedding_model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.vectorizer_path = self.model_dir / "tfidf_vectorizer.pkl"
        self.matrix_path = self.model_dir / "tfidf_matrix.pkl"
        self.index_path = self.model_dir / "tfidf_index.pkl"
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.review_ids: list[str] = []

    def fit_transform(self, texts: list[str], review_ids: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self.vectorizer = TfidfVectorizer(
            max_features=settings.embedding_max_features,
            stop_words="english",
            ngram_range=(1, 2),
        )
        self.matrix = self.vectorizer.fit_transform(texts)
        self.review_ids = review_ids
        self._persist()
        dense = self.matrix.toarray()
        return [row.tolist() for row in dense]

    def transform(self, text: str) -> list[float]:
        if self.vectorizer is None:
            self._load()
        if self.vectorizer is None:
            raise RuntimeError("Embedding vectorizer is not fitted")
        vec = self.vectorizer.transform([text]).toarray()[0]
        return vec.tolist()

    def search(self, query: str, *, top_k: int = 5) -> list[SearchHit]:
        if self.matrix is None or self.vectorizer is None:
            self._load()
        if self.matrix is None or self.vectorizer is None or not self.review_ids:
            return []

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix).flatten()
        if scores.size == 0:
            return []

        top_idx = np.argsort(scores)[::-1][:top_k]
        hits: list[SearchHit] = []
        for idx in top_idx:
            score = float(scores[idx])
            if score <= 0:
                continue
            hits.append(
                SearchHit(review_id=self.review_ids[int(idx)], score=round(score, 4), text="")
            )
        return hits

    def _persist(self) -> None:
        with self.vectorizer_path.open("wb") as f:
            pickle.dump(self.vectorizer, f)
        with self.matrix_path.open("wb") as f:
            pickle.dump(self.matrix, f)
        with self.index_path.open("wb") as f:
            pickle.dump(self.review_ids, f)
        logger.info("Persisted TF-IDF embedding model to %s", self.model_dir)

    def _load(self) -> None:
        if not self.vectorizer_path.exists():
            return
        with self.vectorizer_path.open("rb") as f:
            self.vectorizer = pickle.load(f)
        with self.matrix_path.open("rb") as f:
            self.matrix = pickle.load(f)
        with self.index_path.open("rb") as f:
            self.review_ids = pickle.load(f)
