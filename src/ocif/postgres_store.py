"""PostgreSQL-backed OCIF import consumer for shared production runtimes.

Validation and idempotency semantics match the SQLite reference consumer. This module
uses psycopg lazily so the standard-library-only local consumer remains usable.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from .ingestion import ContractError, ImportResult, _canonical_json, _digest, validate_envelope


class PostgresOCIFStore:
    """Durable PostgreSQL consumer with transactional observation/event writes."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS ocif_observations (
        observation_id BIGSERIAL PRIMARY KEY,
        contract_version TEXT NOT NULL, source_id TEXT NOT NULL, capture_id TEXT NOT NULL,
        submitted_url TEXT NOT NULL, normalized_url TEXT NOT NULL, capture_status TEXT NOT NULL,
        status_reason TEXT, error_code TEXT, captured_at TEXT, completed_at TEXT, platform TEXT,
        producer_revision TEXT NOT NULL, extraction_json JSONB, artifacts_json JSONB NOT NULL,
        warnings_json JSONB NOT NULL, payload_hash TEXT NOT NULL, ingested_at TIMESTAMPTZ NOT NULL,
        ingest_latency_ms DOUBLE PRECISION NOT NULL,
        UNIQUE(source_id, capture_id, contract_version)
    );
    CREATE TABLE IF NOT EXISTS ocif_quarantine (
        quarantine_id BIGSERIAL PRIMARY KEY, payload_hash TEXT NOT NULL, reason TEXT NOT NULL,
        received_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS ocif_import_events (
        event_id BIGSERIAL PRIMARY KEY, event_type TEXT NOT NULL, source_id TEXT, capture_id TEXT,
        occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(), detail_json JSONB NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_ocif_events_capture
        ON ocif_import_events(source_id, capture_id, occurred_at);
    """

    def __init__(
        self,
        dsn: str | None = None,
        *,
        connection_factory: Callable[[], Any] | None = None,
        artifact_root: str | Path | None = None,
    ) -> None:
        self._artifact_root = Path(artifact_root).expanduser().resolve() if artifact_root else None
        if connection_factory is None and not (dsn and dsn.strip()):
            raise ValueError(
                "PostgreSQL DSN or connection_factory is required"
            )
        if connection_factory is not None:
            self._connect: Callable[[], Any] = connection_factory
        else:
            def connect() -> Any:
                try:
                    import psycopg
                except ImportError as exc:  # pragma: no cover - deployment configuration
                    raise RuntimeError("install ocif[postgres] to use PostgresOCIFStore") from exc
                assert dsn is not None
                return psycopg.connect(dsn)
            self._connect = connect

    def initialize(self) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(self.SCHEMA)

    def close(self) -> None:
        """No persistent connection is held by this adapter."""

    def _event(
        self,
        cursor: Any,
        event_type: str,
        envelope: Mapping[str, Any] | None,
        detail: Mapping[str, Any],
    ) -> None:
        cursor.execute(
            """INSERT INTO ocif_import_events(event_type, source_id, capture_id, detail_json)
               VALUES (%s, %s, %s, %s::jsonb)""",
            (
                event_type,
                envelope.get("source_id") if envelope else None,
                envelope.get("capture_id") if envelope else None,
                _canonical_json(detail),
            ),
        )

    def _verify_artifact_files(self, envelope: Mapping[str, Any]) -> None:
        artifacts = envelope.get("artifacts", [])
        if not artifacts:
            return
        if self._artifact_root is None:
            raise ContractError("artifact_root is required to verify artifact-bearing envelopes")
        root = self._artifact_root
        for artifact in artifacts:
            relative = PurePosixPath(str(artifact["location"]))
            candidate = (root / Path(*relative.parts)).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file():
                raise ContractError(f"artifact {artifact['artifact_id']}: missing or unsafe file")
            if candidate.stat().st_size != int(artifact["byte_size"]):
                raise ContractError(f"artifact {artifact['artifact_id']}: byte size mismatch")
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if digest != artifact["sha256"]:
                raise ContractError(f"artifact {artifact['artifact_id']}: SHA-256 mismatch")

    def import_payload(self, payload: Mapping[str, Any]) -> ImportResult:
        started = datetime.now().astimezone()
        try:
            raw_hash = (
                _digest(payload)
                if isinstance(payload, Mapping)
                else _digest({"invalid": type(payload).__name__})
            )
        except (TypeError, ValueError):
            raw_hash = hashlib.sha256(
                f"invalid:{type(payload).__name__}".encode()
            ).hexdigest()
        try:
            envelope = validate_envelope(payload)
            self._verify_artifact_files(envelope)
        except ContractError as exc:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ocif_quarantine(payload_hash, reason) VALUES (%s, %s)",
                    (raw_hash, str(exc)),
                )
                self._event(
                    cursor,
                    "import.rejected",
                    None,
                    {"reason": str(exc), "payload_hash": raw_hash},
                )
            return ImportResult("rejected", None, None, str(exc))

        key = (envelope["source_id"], envelope["capture_id"], envelope["contract_version"])
        elapsed_ms = (datetime.now().astimezone() - started).total_seconds() * 1000.0
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO ocif_observations(
                   contract_version, source_id, capture_id, submitted_url, normalized_url,
                   capture_status, status_reason, error_code, captured_at, completed_at, platform,
                   producer_revision, extraction_json, artifacts_json, warnings_json, payload_hash,
                   ingested_at, ingest_latency_ms)
                   VALUES (
                       %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                       %s::jsonb, %s::jsonb, %s::jsonb, %s, now(), %s
                   )
                   ON CONFLICT(source_id, capture_id, contract_version) DO NOTHING
                   RETURNING observation_id""",
                (envelope["contract_version"], envelope["source_id"], envelope["capture_id"],
                 envelope["submitted_url"], envelope["normalized_url"], envelope["capture_status"],
                 envelope["status_reason"], envelope["error_code"], envelope["captured_at"],
                 envelope["completed_at"], envelope["platform"], envelope["producer_revision"],
                 _canonical_json(envelope["extraction"]) if envelope["extraction"] else None,
                 _canonical_json(envelope["artifacts"]), _canonical_json(envelope["warnings"]),
                 raw_hash, elapsed_ms),
            )
            inserted = cursor.fetchone()
            if inserted is not None:
                observation_id = int(inserted[0])
                self._event(
                    cursor,
                    "import.accepted",
                    envelope,
                    {"observation_id": observation_id, "payload_hash": raw_hash},
                )
                return ImportResult("accepted", key[0], key[1], observation_id=observation_id)

            cursor.execute(
                """SELECT observation_id, payload_hash FROM ocif_observations
                   WHERE source_id=%s AND capture_id=%s AND contract_version=%s FOR UPDATE""", key,
            )
            existing = cursor.fetchone()
            if existing is None:
                raise RuntimeError(
                    "conflicting OCIF observation disappeared during idempotency check"
                )
            observation_id, existing_hash = int(existing[0]), str(existing[1])
            if existing_hash == raw_hash:
                self._event(
                    cursor,
                    "import.duplicate",
                    envelope,
                    {"observation_id": observation_id, "payload_hash": raw_hash},
                )
                return ImportResult("duplicate", key[0], key[1], observation_id=observation_id)
            reason = "idempotency key reused with changed payload; possible producer mutation"
            cursor.execute(
                "INSERT INTO ocif_quarantine(payload_hash, reason) VALUES (%s, %s)",
                (raw_hash, reason),
            )
            self._event(
                cursor,
                "import.conflict",
                envelope,
                {"reason": reason, "payload_hash": raw_hash},
            )
            return ImportResult("rejected", key[0], key[1], reason)
