from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from ocif.ingestion import OCIFStore, validate_envelope
from ocif.retrieval import build_index, evaluate_retrieval, evidence_linked_brief, retrieve


ARTIFACT_HASH = hashlib.sha256(b"fixture evidence").hexdigest()


def payload(*, capture_id: str = "capture-1", status: str = "success") -> dict:
    extraction_status = "partial" if status == "partial" else "success"
    return {
        "contract_version": "0.1.0",
        "source_id": "source-1",
        "submitted_url": "https://example.org/posts/1",
        "normalized_url": "https://example.org/posts/1",
        "capture_id": capture_id,
        "capture_status": status,
        "status_reason": None,
        "error_code": None,
        "captured_at": "2026-10-22T10:00:00+00:00",
        "completed_at": "2026-10-22T10:00:01+00:00",
        "artifacts": [{
            "artifact_id": "artifact-1",
            "kind": "rendered_dom_html",
            "location": "evidence/capture-1/page.html",
            "sha256": ARTIFACT_HASH,
            "byte_size": 17,
            "media_type": "text/html",
        }],
        "extraction": {
            "extraction_id": "extract-1",
            "extractor": "generic_metadata",
            "extractor_version": "0.1.0",
            "schema_version": "1",
            "status": extraction_status,
            "post_text": "Football strategy shapes audience attention and content performance.",
            "author": "Example Author",
            "title": "Football strategy",
            "canonical_url": "https://example.org/posts/1",
            "metadata": {"lang": "en"},
            "provenance": {
                "post_text": {
                    "artifact_id": "artifact-1",
                    "artifact_sha256": ARTIFACT_HASH,
                    "locator": "meta[property=og:description]",
                }
            },
        },
        "platform": "UNIVERSAL",
        "producer_revision": "test-revision",
        "warnings": [],
    }


class IngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = OCIFStore(str(Path(self.tmp.name) / "ocif.sqlite3"))

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_valid_payload_is_imported_and_reimport_is_idempotent(self) -> None:
        item = payload()
        self.assertEqual(validate_envelope(item)["capture_status"], "success")
        first = self.store.import_payload(item)
        second = self.store.import_payload(item)
        self.assertEqual(first.status, "accepted")
        self.assertEqual(second.status, "duplicate")
        count = self.store.connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        self.assertEqual(count, 1)

    def test_same_key_with_mutated_payload_is_rejected(self) -> None:
        self.store.import_payload(payload())
        mutated = payload()
        mutated["warnings"] = ["changed after initial delivery"]
        result = self.store.import_payload(mutated)
        self.assertEqual(result.status, "rejected")
        self.assertIn("different payload", result.reason or "")

    def test_recapture_is_a_new_observation(self) -> None:
        self.store.import_payload(payload(capture_id="capture-1"))
        result = self.store.import_payload(payload(capture_id="capture-2"))
        self.assertEqual(result.status, "accepted")
        count = self.store.connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        self.assertEqual(count, 2)

    def test_hash_mismatch_is_quarantined(self) -> None:
        item = payload()
        item["extraction"]["provenance"]["post_text"]["artifact_sha256"] = "0" * 64
        result = self.store.import_payload(item)
        self.assertEqual(result.status, "rejected")
        count = self.store.connection.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
        self.assertEqual(count, 1)

    def test_unknown_contract_version_and_unknown_fields_are_rejected(self) -> None:
        item = payload()
        item["contract_version"] = "99.0"
        self.assertEqual(self.store.import_payload(item).status, "rejected")
        item = payload()
        item["unreviewed_extension"] = {"trusted": True}
        self.assertEqual(self.store.import_payload(item).status, "rejected")

    def test_success_without_provenance_is_rejected(self) -> None:
        item = payload()
        item["extraction"]["provenance"] = {}
        self.assertEqual(self.store.import_payload(item).status, "rejected")

    def test_hostile_or_malformed_input_does_not_crash_consumer(self) -> None:
        self.assertEqual(self.store.import_payload({"contract_version": "0.1.0"}).status, "rejected")
        self.assertEqual(self.store.import_payload({"not": object()}).status, "rejected")

    def test_blocked_status_is_preserved_not_upgraded(self) -> None:
        item = payload(status="blocked")
        item["extraction"] = None
        item["artifacts"] = []
        result = self.store.import_payload(item)
        self.assertEqual(result.status, "accepted")
        row = self.store.connection.execute(
            "SELECT capture_status FROM observations WHERE capture_id='capture-1'"
        ).fetchone()
        self.assertEqual(row["capture_status"], "blocked")

    def test_index_retrieval_and_evidence_linked_brief(self) -> None:
        self.store.import_payload(payload())
        self.assertGreaterEqual(build_index(self.store, chunk_size=120, overlap=20), 1)
        results = retrieve(self.store, "football strategy", top_k=3)
        self.assertTrue(results)
        self.assertEqual(results[0].capture_id, "capture-1")
        self.assertTrue(results[0].artifacts)
        brief = evidence_linked_brief(self.store, "football strategy")
        self.assertFalse(brief["unsupported"])
        self.assertEqual(brief["mode"], "extractive_evidence_only")
        chunk_id = results[0].chunk_id
        metrics = evaluate_retrieval(self.store, "football strategy", [chunk_id], top_k=3)
        self.assertEqual(metrics["recall_at_k"], 1.0)
        self.assertEqual(metrics["mrr"], 1.0)

    def test_reliability_metrics_are_computed_from_stored_events(self) -> None:
        self.store.import_payload(payload())
        self.store.import_payload(payload())
        metrics = self.store.reliability_metrics()
        self.assertEqual(metrics["observations"], 1)
        self.assertEqual(metrics["duplicate_rate"], 0.5)
        self.assertEqual(metrics["provenance_completeness"], 1.0)


if __name__ == "__main__":
    unittest.main()
