"""Deterministic, evidence-linked retrieval and evaluation for OCIF.

The first implementation deliberately avoids embedding/API dependencies. Retrieval
quality is measurable and replaceable behind this interface.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Iterable, Sequence

from .ingestion import OCIFStore, _canonical_json

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{1,}", re.IGNORECASE)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float
    source_id: str
    capture_id: str
    capture_status: str
    submitted_url: str
    artifacts: tuple[dict[str, str], ...]


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_RE.findall(text)]


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size < 80:
        raise ValueError("chunk_size must be at least 80 characters")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []
    paragraphs = re.split(r"\n{1,}", normalized)
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        while len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(paragraph[:chunk_size].strip())
            paragraph = paragraph[chunk_size - overlap :]
        candidate = f"{current}\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            tail = current[-overlap:] if current and overlap else ""
            current = f"{tail}\n{paragraph}".strip() if tail else paragraph
    if current:
        chunks.append(current)
    # Remove adjacent duplicate fragments caused by short overlap windows.
    return list(dict.fromkeys(chunk for chunk in chunks if chunk))


def build_index(store: OCIFStore, *, chunk_size: int = 600, overlap: int = 80) -> int:
    """Chunk validated evidence text. Re-running is idempotent for unchanged records."""
    connection = store.connection
    rows = connection.execute(
        """SELECT observation_id, source_id, capture_id, capture_status,
                  extraction_json, artifacts_json
           FROM observations WHERE capture_status IN ('success', 'partial')
           AND extraction_json IS NOT NULL"""
    ).fetchall()
    added = 0
    for row in rows:
        extraction = json.loads(row["extraction_json"])
        text = extraction.get("post_text")
        provenance = extraction.get("provenance") or {}
        if not isinstance(text, str) or not text.strip() or not provenance:
            continue
        artifact_refs = [
            {"artifact_id": ref["artifact_id"], "artifact_sha256": ref["artifact_sha256"],
             "field": field, "locator": ref["locator"]}
            for field, ref in sorted(provenance.items())
        ]
        for ordinal, chunk in enumerate(_chunk_text(text, chunk_size, overlap)):
            chunk_id = hashlib.sha256(
                f"{row['observation_id']}:{ordinal}:{chunk}".encode("utf-8")
            ).hexdigest()
            cursor = connection.execute(
                """INSERT OR IGNORE INTO chunks(
                    chunk_id, observation_id, ordinal, text, artifact_refs_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (chunk_id, row["observation_id"], ordinal, chunk, _canonical_json(artifact_refs),
                 datetime.now().astimezone().isoformat()),
            )
            added += cursor.rowcount
    connection.commit()
    return added


def retrieve(store: OCIFStore, query: str, *, top_k: int = 5,
             allowed_statuses: Iterable[str] = ("success", "partial")) -> list[RetrievedChunk]:
    """Lexical baseline retrieval with status filtering applied before ranking."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if top_k < 1:
        raise ValueError("top_k must be positive")
    allowed = tuple(sorted(set(allowed_statuses)))
    if not allowed:
        return []
    placeholders = ",".join("?" for _ in allowed)
    rows = store.connection.execute(
        f"""SELECT c.chunk_id, c.text, c.artifact_refs_json, o.source_id, o.capture_id,
                   o.capture_status, o.submitted_url, o.artifacts_json
            FROM chunks c JOIN observations o USING(observation_id)
            WHERE o.capture_status IN ({placeholders})""",
        allowed,
    ).fetchall()
    query_tokens = _tokens(query)
    if not query_tokens:
        return []
    query_counts = Counter(query_tokens)
    ranked: list[RetrievedChunk] = []
    for row in rows:
        tokens = _tokens(row["text"])
        counts = Counter(tokens)
        if not counts:
            continue
        # Small, deterministic BM25-inspired score; no external model or network call.
        score = sum(
            query_counts[token] * (counts[token] / (counts[token] + 1.2))
            for token in query_counts
        )
        if score <= 0:
            continue
        artifacts = json.loads(row["artifacts_json"])
        hash_by_id = {item["artifact_id"]: item["sha256"] for item in artifacts}
        refs = json.loads(row["artifact_refs_json"])
        # Every citation returned to callers must still point at an imported artifact hash.
        safe_refs = tuple(
            {**ref, "artifact_hash_verified": str(hash_by_id.get(ref["artifact_id"]) == ref["artifact_sha256"])}
            for ref in refs
        )
        if not safe_refs or any(ref["artifact_hash_verified"] != "True" for ref in safe_refs):
            continue
        ranked.append(
            RetrievedChunk(
                chunk_id=row["chunk_id"], text=row["text"], score=score,
                source_id=row["source_id"], capture_id=row["capture_id"],
                capture_status=row["capture_status"], submitted_url=row["submitted_url"],
                artifacts=safe_refs,
            )
        )
    ranked.sort(key=lambda item: (-item.score, item.chunk_id))
    return ranked[:top_k]


def evaluate_retrieval(store: OCIFStore, query: str, expected_chunk_ids: Sequence[str],
                       *, top_k: int = 5) -> dict[str, float]:
    """Evaluate a golden query using recall@k, MRR and precision@k."""
    expected = set(expected_chunk_ids)
    results = retrieve(store, query, top_k=top_k)
    actual = [item.chunk_id for item in results]
    hits = [index + 1 for index, item in enumerate(actual) if item in expected]
    recall = len(set(actual) & expected) / len(expected) if expected else 1.0
    reciprocal_rank = 1.0 / min(hits) if hits else 0.0
    precision = len(set(actual) & expected) / top_k
    store.connection.execute(
        """INSERT INTO retrieval_evaluations(
            query, expected_chunk_ids_json, retrieved_chunk_ids_json,
            recall_at_k, reciprocal_rank, precision_at_k, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (query, _canonical_json(sorted(expected)), _canonical_json(actual), recall,
         reciprocal_rank, precision, datetime.now().astimezone().isoformat()),
    )
    store.connection.commit()
    return {"recall_at_k": recall, "mrr": reciprocal_rank, "precision_at_k": precision}


def evidence_linked_brief(store: OCIFStore, question: str, *, top_k: int = 5) -> dict[str, object]:
    """Return an extractive brief; does not invent claims or call an LLM."""
    results = retrieve(store, question, top_k=top_k)
    claims = [
        {
            "text": item.text,
            "claim_type": "source_excerpt",
            "evidence": {
                "source_id": item.source_id,
                "capture_id": item.capture_id,
                "url": item.submitted_url,
                "chunk_id": item.chunk_id,
                "artifacts": list(item.artifacts),
                "capture_status": item.capture_status,
            },
            "retrieval_score": item.score,
        }
        for item in results
    ]
    return {
        "question": question,
        "mode": "extractive_evidence_only",
        "claims": claims,
        "unsupported": len(claims) == 0,
        "warning": "Retrieved excerpts are evidence, not independently verified truth; model inference is not performed.",
    }
