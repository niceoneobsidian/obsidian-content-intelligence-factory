"""Strict OCIF consumer for versioned USIE evidence envelopes.

This module uses only the Python standard library. It never fetches source URLs or
executes instructions found in imported content.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping
from urllib.parse import urlsplit

CONTRACT_VERSION = "0.1.0"
SUPPORTED_STATUSES = frozenset({"success", "partial", "blocked", "unavailable", "failed", "cancelled"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
KNOWN_TOP_LEVEL = frozenset(
    {
        "contract_version", "source_id", "submitted_url", "normalized_url", "capture_id",
        "capture_status", "status_reason", "captured_at", "completed_at", "artifacts",
        "extraction", "platform", "producer_revision", "warnings",
    }
)


class ContractError(ValueError):
    """Payload is malformed, unsupported, or has unverifiable provenance."""


@dataclass(frozen=True)
class ImportResult:
    status: str
    source_id: str | None
    capture_id: str | None
    reason: str | None = None
    observation_id: int | None = None


def _timestamp(value: Any, field: str, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field}: expected an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{field}: invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"{field}: timezone is required")
    return parsed.isoformat()


def _url(value: Any, field: str, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field}: URL is required")
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ContractError(f"{field}: only absolute HTTP(S) URLs are supported")
    if parts.username is not None or parts.password is not None:
        raise ContractError(f"{field}: embedded URL credentials are forbidden")
    return value


def _required_string(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field}: non-empty string required")
    return value.strip()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def validate_envelope(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one envelope; raise ContractError on any unsafe ambiguity."""
    if not isinstance(payload, Mapping):
        raise ContractError("payload: expected a JSON object")
    unknown = set(payload) - KNOWN_TOP_LEVEL
    if unknown:
        raise ContractError("unsupported top-level fields: " + ", ".join(sorted(str(key) for key in unknown)))
    version = _required_string(payload, "contract_version")
    if version != CONTRACT_VERSION:
        raise ContractError(f"unsupported contract_version: {version}")
    source_id = _required_string(payload, "source_id")
    capture_id = _required_string(payload, "capture_id")
    submitted_url = _url(payload.get("submitted_url"), "submitted_url")
    normalized_url = _url(payload.get("normalized_url"), "normalized_url")
    status = _required_string(payload, "capture_status")
    if status not in SUPPORTED_STATUSES:
        raise ContractError(f"unsupported capture_status: {status}")
    captured_at = _timestamp(payload.get("captured_at"), "captured_at", required=status not in {"queued"})
    completed_at = _timestamp(payload.get("completed_at"), "completed_at")
    producer_revision = _required_string(payload, "producer_revision")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise ContractError("artifacts: expected a list")
    artifact_by_id: dict[str, dict[str, Any]] = {}
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            raise ContractError(f"artifacts[{index}]: expected an object")
        artifact_id = _required_string(artifact, "artifact_id")
        if artifact_id in artifact_by_id:
            raise ContractError(f"artifacts[{index}]: duplicate artifact_id")
        sha = artifact.get("sha256")
        if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
            raise ContractError(f"artifacts[{index}].sha256: expected lowercase SHA-256")
        size = artifact.get("byte_size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ContractError(f"artifacts[{index}].byte_size: expected non-negative integer")
        artifact_by_id[artifact_id] = {
            "artifact_id": artifact_id,
            "kind": _required_string(artifact, "kind"),
            "location": _required_string(artifact, "location"),
            "sha256": sha,
            "byte_size": size,
            "media_type": str(artifact.get("media_type") or "application/octet-stream"),
        }
    extraction = payload.get("extraction")
    normalized_extraction = None
    if extraction is not None:
        if not isinstance(extraction, Mapping):
            raise ContractError("extraction: expected an object or null")
        extraction_status = _required_string(extraction, "status")
        if extraction_status not in {"success", "partial"}:
            raise ContractError(f"extraction.status: unsupported value {extraction_status}")
        post_text = extraction.get("post_text")
        if post_text is not None and not isinstance(post_text, str):
            raise ContractError("extraction.post_text: expected string or null")
        provenance = extraction.get("provenance", {})
        if not isinstance(provenance, Mapping):
            raise ContractError("extraction.provenance: expected an object")
        checked_provenance: dict[str, dict[str, str]] = {}
        for field, reference in provenance.items():
            if not isinstance(field, str) or not field.strip() or not isinstance(reference, Mapping):
                raise ContractError("extraction.provenance: malformed field reference")
            artifact_id = _required_string(reference, "artifact_id")
            artifact_hash = reference.get("artifact_sha256")
            if not isinstance(artifact_hash, str) or not SHA256_RE.fullmatch(artifact_hash):
                raise ContractError(f"extraction.provenance.{field}: invalid artifact_sha256")
            artifact = artifact_by_id.get(artifact_id)
            if artifact is None:
                raise ContractError(f"extraction.provenance.{field}: unknown artifact_id")
            if artifact["sha256"] != artifact_hash:
                raise ContractError(f"extraction.provenance.{field}: artifact hash mismatch")
            checked_provenance[field] = {
                "artifact_id": artifact_id,
                "artifact_sha256": artifact_hash,
                "locator": _required_string(reference, "locator"),
            }
        if extraction_status == "success" and (not post_text or not post_text.strip()):
            raise ContractError("successful extraction requires non-empty post_text")
        if extraction_status == "success" and not checked_provenance:
            raise ContractError("successful extraction requires artifact-backed field provenance")
        normalized_extraction = {
            "extraction_id": _required_string(extraction, "extraction_id"),
            "extractor": _required_string(extraction, "extractor"),
            "extractor_version": _required_string(extraction, "extractor_version"),
            "schema_version": str(extraction.get("schema_version", "1")),
            "status": extraction_status,
            "post_text": post_text.strip() if isinstance(post_text, str) else None,
            "author": extraction.get("author") if isinstance(extraction.get("author"), str) else None,
            "title": extraction.get("title") if isinstance(extraction.get("title"), str) else None,
            "canonical_url": _url(extraction.get("canonical_url"), "extraction.canonical_url", required=False),
            "metadata": extraction.get("metadata", {}),
            "provenance": checked_provenance,
        }
        if not isinstance(normalized_extraction["metadata"], Mapping):
            raise ContractError("extraction.metadata: expected an object")
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in normalized_extraction["metadata"].items()):
            raise ContractError("extraction.metadata: keys and values must be strings")
    if status == "success":
        if normalized_extraction is None or normalized_extraction["status"] != "success":
            raise ContractError("capture success requires a successful validated extraction")
    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        raise ContractError("warnings: expected a list of strings")
    platform = payload.get("platform")
    if platform is not None and not isinstance(platform, str):
        raise ContractError("platform: expected string or null")
    reason = payload.get("status_reason")
    if reason is not None and not isinstance(reason, str):
        raise ContractError("status_reason: expected string or null")
    return {
        "contract_version": version,
        "source_id": source_id,
        "capture_id": capture_id,
        "submitted_url": submitted_url,
        "normalized_url": normalized_url,
        "capture_status": status,
        "status_reason": reason,
        "captured_at": captured_at,
        "completed_at": completed_at,
        "artifacts": list(artifact_by_id.values()),
        "extraction": normalized_extraction,
        "platform": platform,
        "producer_revision": producer_revision,
        "warnings": warnings,
    }


class OCIFStore:
    """SQLite-backed consumer store; use a file path for durable state."""

    def __init__(self, database: str = "ocif.sqlite3") -> None:
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS observations (
                observation_id INTEGER PRIMARY KEY,
                contract_version TEXT NOT NULL,
                source_id TEXT NOT NULL,
                capture_id TEXT NOT NULL,
                submitted_url TEXT NOT NULL,
                normalized_url TEXT NOT NULL,
                capture_status TEXT NOT NULL,
                status_reason TEXT,
                captured_at TEXT,
                completed_at TEXT,
                platform TEXT,
                producer_revision TEXT NOT NULL,
                extraction_json TEXT,
                artifacts_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                ingest_latency_ms REAL NOT NULL,
                UNIQUE(source_id, capture_id, contract_version)
            );
            CREATE TABLE IF NOT EXISTS quarantine (
                quarantine_id INTEGER PRIMARY KEY,
                payload_hash TEXT NOT NULL,
                reason TEXT NOT NULL,
                received_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS import_events (
                event_id INTEGER PRIMARY KEY,
                event_type TEXT NOT NULL,
                source_id TEXT,
                capture_id TEXT,
                occurred_at TEXT NOT NULL,
                detail_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                observation_id INTEGER NOT NULL REFERENCES observations(observation_id),
                ordinal INTEGER NOT NULL,
                text TEXT NOT NULL,
                artifact_refs_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(observation_id, ordinal)
            );
            CREATE TABLE IF NOT EXISTS retrieval_evaluations (
                evaluation_id INTEGER PRIMARY KEY,
                query TEXT NOT NULL,
                expected_chunk_ids_json TEXT NOT NULL,
                retrieved_chunk_ids_json TEXT NOT NULL,
                recall_at_k REAL NOT NULL,
                reciprocal_rank REAL NOT NULL,
                precision_at_k REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def import_payload(self, payload: Mapping[str, Any]) -> ImportResult:
        started = time.perf_counter()
        try:
            raw_hash = _digest(payload) if isinstance(payload, Mapping) else _digest({"invalid": str(type(payload))})
        except (TypeError, ValueError):
            raw_hash = hashlib.sha256(f"invalid:{type(payload).__name__}".encode("utf-8")).hexdigest()
        try:
            envelope = validate_envelope(payload)
        except ContractError as exc:
            self.connection.execute(
                "INSERT INTO quarantine(payload_hash, reason, received_at) VALUES (?, ?, ?)",
                (raw_hash, str(exc), datetime.now().astimezone().isoformat()),
            )
            self.connection.execute(
                "INSERT INTO import_events(event_type, occurred_at, detail_json) VALUES (?, ?, ?)",
                ("import.rejected", datetime.now().astimezone().isoformat(), _canonical_json({"reason": str(exc), "payload_hash": raw_hash})),
            )
            self.connection.commit()
            return ImportResult("rejected", None, None, str(exc))
        key = (envelope["source_id"], envelope["capture_id"], envelope["contract_version"])
        existing = self.connection.execute(
            "SELECT observation_id, payload_hash FROM observations WHERE source_id=? AND capture_id=? AND contract_version=?",
            key,
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] == raw_hash:
                self._event("import.duplicate", envelope, {"payload_hash": raw_hash})
                return ImportResult("duplicate", key[0], key[1], observation_id=existing["observation_id"])
            reason = "idempotency key already exists with different payload; possible producer mutation"
            self.connection.execute(
                "INSERT INTO quarantine(payload_hash, reason, received_at) VALUES (?, ?, ?)",
                (raw_hash, reason, datetime.now().astimezone().isoformat()),
            )
            self._event("import.conflict", envelope, {"reason": reason, "payload_hash": raw_hash})
            self.connection.commit()
            return ImportResult("rejected", key[0], key[1], reason)
        latency = (time.perf_counter() - started) * 1000.0
        cursor = self.connection.execute(
            """INSERT INTO observations(
                contract_version, source_id, capture_id, submitted_url, normalized_url,
                capture_status, status_reason, captured_at, completed_at, platform,
                producer_revision, extraction_json, artifacts_json, warnings_json,
                payload_hash, ingested_at, ingest_latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                envelope["contract_version"], envelope["source_id"], envelope["capture_id"],
                envelope["submitted_url"], envelope["normalized_url"], envelope["capture_status"],
                envelope["status_reason"], envelope["captured_at"], envelope["completed_at"],
                envelope["platform"], envelope["producer_revision"],
                _canonical_json(envelope["extraction"]) if envelope["extraction"] else None,
                _canonical_json(envelope["artifacts"]), _canonical_json(envelope["warnings"]),
                raw_hash, datetime.now().astimezone().isoformat(), latency,
            ),
        )
        observation_id = int(cursor.lastrowid)
        self._event("import.accepted", envelope, {"observation_id": observation_id, "payload_hash": raw_hash})
        self.connection.commit()
        return ImportResult("accepted", key[0], key[1], observation_id=observation_id)

    def _event(self, event_type: str, envelope: Mapping[str, Any], detail: Mapping[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO import_events(event_type, source_id, capture_id, occurred_at, detail_json) VALUES (?, ?, ?, ?, ?)",
            (event_type, envelope.get("source_id"), envelope.get("capture_id"),
             datetime.now().astimezone().isoformat(), _canonical_json(detail)),
        )

    def reliability_metrics(self) -> dict[str, Any]:
        rows = self.connection.execute("SELECT * FROM observations").fetchall()
        total = len(rows)
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["capture_status"]] = counts.get(row["capture_status"], 0) + 1
        accepted = self.connection.execute(
            "SELECT COUNT(*) FROM import_events WHERE event_type='import.accepted'"
        ).fetchone()[0]
        duplicates = self.connection.execute(
            "SELECT COUNT(*) FROM import_events WHERE event_type='import.duplicate'"
        ).fetchone()[0]
        quarantined = self.connection.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
        provenance_complete = 0
        latency_values: list[float] = []
        for row in rows:
            latency_values.append(float(row["ingest_latency_ms"]))
            extraction = json.loads(row["extraction_json"]) if row["extraction_json"] else None
            artifacts = json.loads(row["artifacts_json"])
            if extraction and extraction.get("provenance") and artifacts:
                provenance_complete += 1
        evals = self.connection.execute(
            "SELECT AVG(recall_at_k), AVG(reciprocal_rank), AVG(precision_at_k) FROM retrieval_evaluations"
        ).fetchone()
        delivered = accepted + duplicates + quarantined
        return {
            "observations": total,
            "capture_status_counts": counts,
            "extraction_success_rate": (counts.get("success", 0) / total) if total else None,
            "partial_rate": (counts.get("partial", 0) / total) if total else None,
            "blocked_rate": (counts.get("blocked", 0) / total) if total else None,
            "unavailable_rate": (counts.get("unavailable", 0) / total) if total else None,
            "failed_rate": (counts.get("failed", 0) / total) if total else None,
            "duplicate_rate": (duplicates / delivered) if delivered else 0.0,
            "quarantined_count": quarantined,
            "provenance_completeness": (provenance_complete / total) if total else None,
            "ingest_latency_ms_mean": (sum(latency_values) / len(latency_values)) if latency_values else None,
            "retrieval_recall_at_k_mean": evals[0],
            "retrieval_mrr_mean": evals[1],
            "retrieval_precision_at_k_mean": evals[2],
        }
