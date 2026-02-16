"""Reasoning agent that uses an LLM and vector memory for root-cause explanations."""

from __future__ import annotations

import json
from typing import Any

import requests
try:
    import chromadb
    from chromadb.api import ClientAPI
except Exception:  # pragma: no cover - environment-dependent optional dependency
    chromadb = None  # type: ignore[assignment]
    ClientAPI = Any  # type: ignore[assignment]


class ReasoningAgent:
    """Generate root-cause explanations and persist reasoning memory."""

    def __init__(self, persist_dir: str = "./zoneguard_memory", model: str = "llama3.1") -> None:
        self.model = model
        self._memory_store: dict[str, str] = {}
        self.collection = None
        if chromadb is not None:
            self.client: ClientAPI = chromadb.PersistentClient(path=persist_dir)
            self.collection = self.client.get_or_create_collection(name="reasoning_history")

    def _build_prompt(self, event: dict[str, Any], context: list[str]) -> str:
        context_text = "\n".join(context) if context else "No prior context available."
        return (
            "You are ZoneGuard root-cause analyst. Provide concise operational explanation and confidence (0-1)."
            " Focus on demand-supply, weather, and inventory dynamics.\n"
            f"Event: {json.dumps(event)}\n"
            f"Context: {context_text}\n"
            "Output JSON with keys: root_cause, evidence, confidence, risks."
        )

    def _query_context(self, event_id: str, top_k: int = 3) -> list[str]:
        if self.collection is None:
            if event_id in self._memory_store:
                return [self._memory_store[event_id]]
            return []
        res = self.collection.query(query_texts=[event_id], n_results=top_k)
        return [doc for doc in (res.get("documents") or [[]])[0] if isinstance(doc, str)]

    def _call_ollama(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        response.raise_for_status()
        return response.json().get("response", "")

    def reason(self, event: dict[str, Any]) -> dict[str, Any]:
        """Generate explanation using vector context and LLM fallback."""
        event_id = str(event.get("event_id", "unknown-event"))
        context = self._query_context(event_id)
        prompt = self._build_prompt(event, context)

        try:
            explanation = self._call_ollama(prompt)
        except Exception:
            snapshot = event.get("snapshot", {})
            demand = float(snapshot.get("demand", 0.0))
            drivers = float(snapshot.get("drivers", 1.0))
            inventory = float(snapshot.get("inventory", 1.0))
            weather = str(snapshot.get("weather", "clear"))
            pressure = demand / max(drivers, 1.0)
            explanation = json.dumps(
                {
                    "root_cause": "Demand-driver imbalance with environmental disruption",
                    "evidence": [
                        f"Demand/driver pressure={pressure:.2f}",
                        f"Inventory level={inventory:.2f}",
                        f"Weather={weather}",
                    ],
                    "confidence": round(min(0.9, 0.45 + pressure / 5), 2),
                    "risks": ["Service-level breach", "Order delays"],
                }
            )

        if self.collection is None:
            self._memory_store[event_id] = f"event_id={event_id}; explanation={explanation}"
        else:
            self.collection.upsert(
                documents=[f"event_id={event_id}; explanation={explanation}"],
                metadatas=[{"event_id": event_id}],
                ids=[event_id],
            )

        return {"event_id": event_id, "prompt": prompt, "explanation": explanation}

    def ingest_feedback(self, event_id: str, correction: str, rating: int) -> None:
        """Store feedback in vector memory for future retrieval."""
        fb_id = f"feedback:{event_id}:{rating}"
        if self.collection is None:
            self._memory_store[fb_id] = f"feedback for {event_id}: rating={rating}; correction={correction}"
        else:
            self.collection.upsert(
                documents=[f"feedback for {event_id}: rating={rating}; correction={correction}"],
                metadatas=[{"event_id": event_id, "rating": rating}],
                ids=[fb_id],
            )

