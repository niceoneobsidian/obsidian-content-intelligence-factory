from __future__ import annotations

import os
from uuid import uuid4

import pytest

from ocif.postgres_store import PostgresOCIFStore


@pytest.mark.skipif(not os.getenv("OCIF_TEST_POSTGRES_DSN"), reason="PostgreSQL integration DSN not configured")
def test_postgres_consumer_replay_survives_store_recreation() -> None:
    dsn = os.environ["OCIF_TEST_POSTGRES_DSN"]
    source_id, capture_id = str(uuid4()), str(uuid4())
    payload = {
        "contract_version": "0.1.0",
        "source_id": source_id,
        "capture_id": capture_id,
        "submitted_url": "https://example.org/post",
        "normalized_url": "https://example.org/post",
        "capture_status": "partial",
        "captured_at": "2026-10-22T10:00:00+00:00",
        "completed_at": "2026-10-22T10:00:01+00:00",
        "artifacts": [],
        "extraction": None,
        "producer_revision": "postgres-integration-test",
        "warnings": [],
    }
    first_store = PostgresOCIFStore(dsn)
    first_store.initialize()
    first = first_store.import_payload(payload)
    assert first.status == "accepted"
    assert first.observation_id is not None

    # A new store instance models a restarted consumer process.
    restarted_store = PostgresOCIFStore(dsn)
    restarted_store.initialize()
    replay = restarted_store.import_payload(payload)
    assert replay.status == "duplicate"
    assert replay.observation_id == first.observation_id

    changed = {**payload, "warnings": ["payload changed after first import"]}
    assert restarted_store.import_payload(changed).status == "rejected"
    first_store.close()
    restarted_store.close()
