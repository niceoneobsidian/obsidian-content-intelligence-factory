from __future__ import annotations

import hashlib
import json
import tempfile
import uuid
from pathlib import Path

from usie.db.repository import SqliteRepository
from usie.integrations.ocif import export_capture

from ocif.ingestion import OCIFStore


def _export_real_sqlite_capture(base: Path) -> dict:
    evidence_root = base / "evidence"
    evidence_root.mkdir()
    data = b"USIE to OCIF end-to-end evidence"
    digest = hashlib.sha256(data).hexdigest()
    (evidence_root / "page.html").write_bytes(data)

    repository = SqliteRepository(base / "usie.sqlite3")
    run_id, source_id, job_id, capture_id, artifact_id, extraction_id = (
        str(uuid.uuid4()) for _ in range(6)
    )
    timestamp = "2026-10-22T10:00:00+00:00"
    url = "https://example.org/posts/integration"
    connection = repository._conn
    connection.execute(
        "INSERT INTO runs(run_id, started_at, status, input_count, config_json, "
        "tool_versions_json) VALUES (?, ?, 'success', 1, '{}', '{}')",
        (run_id, timestamp),
    )
    connection.execute(
        "INSERT INTO sources(source_id, source_url, normalized_url, platform, first_seen_at) "
        "VALUES (?, ?, ?, 'UNIVERSAL', ?)",
        (source_id, url, url, timestamp),
    )
    connection.execute(
        "INSERT INTO jobs(job_id, run_id, source_id, submitted_url, status, created_at) "
        "VALUES (?, ?, ?, ?, 'success', ?)",
        (job_id, run_id, source_id, url, timestamp),
    )
    connection.execute(
        "INSERT INTO captures(capture_id, job_id, run_id, source_id, attempt, captured_at, "
        "finished_at, status, submitted_url, issues_json) "
        "VALUES (?, ?, ?, ?, 1, ?, ?, 'success', ?, '[]')",
        (capture_id, job_id, run_id, source_id, timestamp, timestamp, url),
    )
    connection.execute(
        "INSERT INTO artifacts(artifact_id, capture_id, kind, relative_path, sha256, "
        "byte_size, media_type, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            artifact_id, capture_id, "rendered_dom_html", "page.html", digest, len(data),
            "text/html", "Integration test artifact", timestamp,
        ),
    )
    provenance = {
        "post_text": {
            "artifact_id": artifact_id,
            "artifact_sha256": digest,
            "locator": "meta[property=og:description]",
        }
    }
    connection.execute(
        "INSERT INTO extraction_results(extraction_id, capture_id, extractor, "
        "extractor_version, status, post_text, title, canonical_url, metadata_json, "
        "issues_json, schema_version, created_at, source_id, normalized_url, provenance_json) "
        "VALUES (?, ?, 'generic_metadata', '0.1.0', 'success', ?, ?, ?, '{}', '[]', "
        "'1', ?, ?, ?, ?)",
        (
            extraction_id, capture_id, "Evidence from a real SQLite fixture", "Integration",
            url, timestamp, source_id, url, json.dumps(provenance),
        ),
    )
    connection.commit()
    try:
        return export_capture(
            repository, evidence_root, capture_id, producer_revision="integration-test"
        )
    finally:
        repository.close()


def test_real_usie_export_is_consumed_with_provenance_and_safe_deduplication() -> None:
    with tempfile.TemporaryDirectory() as directory:
        envelope = _export_real_sqlite_capture(Path(directory))
        store = OCIFStore(str(Path(directory) / "ocif.sqlite3"))
        try:
            first = store.import_payload(envelope)
            duplicate = store.import_payload(envelope)
            assert first.status == "accepted"
            assert duplicate.status == "duplicate"
            assert first.observation_id == duplicate.observation_id

            row = store.connection.execute(
                "SELECT extraction_json, artifacts_json FROM observations "
                "WHERE capture_id = ?",
                (envelope["capture_id"],),
            ).fetchone()
            extraction = json.loads(row["extraction_json"])
            artifacts = json.loads(row["artifacts_json"])
            assert extraction["provenance"]["post_text"]["artifact_sha256"] == (
                artifacts[0]["sha256"]
            )

            changed = dict(envelope)
            changed["warnings"] = ["mutated after initial export"]
            assert store.import_payload(changed).status == "rejected"

            recapture = dict(envelope)
            recapture["capture_id"] = str(uuid.uuid4())
            accepted_recapture = store.import_payload(recapture)
            assert accepted_recapture.status == "accepted"
            assert accepted_recapture.observation_id != first.observation_id

            malformed = dict(envelope)
            malformed["unsupported_extension"] = True
            assert store.import_payload(malformed).status == "rejected"
            assert store.connection.execute(
                "SELECT COUNT(*) FROM observations"
            ).fetchone()[0] == 2
        finally:
            store.close()
