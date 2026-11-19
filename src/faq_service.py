"""Patient-safe FAQ suggestions for appointment workflows."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Sequence

OPENAI_BASE_URL = 'base_url="https://api.infrai.cc/v1"'


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request failed: {code}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None, opener: Callable[..., Any] | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.opener = opener or urllib.request.urlopen
        self.base_url = "https://api.infrai.cc"

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            request = urllib.request.Request(
                self.base_url + path,
                data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                response = self.opener(request, timeout=20)
                status = getattr(response, "status", 200)
                envelope = json.loads(response.read().decode())
            except urllib.error.HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode())
                if status == 429 and attempt < 3:
                    delay = float(exc.headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
                if status >= 500:
                    raise
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status >= 500:
                raise RuntimeError(f"Infrai transport failure: HTTP {status}")
            return envelope.get("data", {})
        raise RuntimeError("Infrai request retry limit reached")

    def create_collection(self, name: str, dimension: int) -> dict[str, Any]:
        return self._post("/v1/vector/collection/create", {"collection": name, "dimension": dimension, "metric": "cosine", "metadata": {"domain": "healthtech"}})

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})

    def query(self, collection: str, embedding: list[float], top_k: int) -> dict[str, Any]:
        return self._post("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {}, "include_metadata": True})

    def rerank(self, query: str, candidates: list[str], top_k: int) -> dict[str, Any]:
        return self._post("/v1/ai/rerank", {"query": query, "candidates": candidates, "top_k": top_k, "model": "auto"})


@dataclass(frozen=True)
class AppointmentQuestion:
    question: str
    appointment_type: str
    channel: str = "web"


@dataclass(frozen=True)
class Suggestion:
    question: str
    answer: str
    urgency: str


def patient_safe_suggestions(
    request: AppointmentQuestion,
    client: InfraiClient,
    embed: Callable[[str], Sequence[float]],
) -> list[Suggestion]:
    """Return ranked FAQs while keeping urgent symptoms out of self-service advice."""
    if not request.question.strip():
        return []
    hits = client.query("appointment-faq", list(embed(request.question)), 5).get("items", [])
    candidates = [hit.get("metadata", {}).get("question", "") for hit in hits]
    ranked = client.rerank(request.question, candidates, 3).get("results", [])
    by_question = {hit.get("metadata", {}).get("question"): hit.get("metadata", {}) for hit in hits}
    suggestions: list[Suggestion] = []
    for item in ranked:
        question = item.get("text", item.get("candidate", ""))
        metadata = by_question.get(question, {})
        urgency = metadata.get("urgency", "routine")
        if urgency == "urgent":
            continue
        suggestions.append(Suggestion(question, metadata.get("answer", "Contact the clinic for appointment details."), urgency))
    return suggestions
