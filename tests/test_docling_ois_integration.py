from __future__ import annotations

import hashlib

from ocif.document_processing import build_envelope, to_ois_input

from ois.integration.ocif_document_processing import OCIFDocumentProcessingCapability
from ois.integration.spine import OISSpine, SpineRequest
from ois.kernel.policy import DefaultPolicyEngine
from ois.registries import CapabilityRegistry


def make_envelope() -> dict:
    artifact_hash = hashlib.sha256(b"approved PDF fixture").hexdigest()
    options_digest = hashlib.sha256(b'{"ocr":true}').hexdigest()
    result = {
        "artifact_sha256": artifact_hash,
        "artifact_size_bytes": len(b"approved PDF fixture"),
        "media_type": "application/pdf",
        "processor_id": "docling",
        "processor_version": "2.0.0",
        "extraction_status": "success",
        "markdown": "persisted separately",
        "page_count": 1,
        "warnings": [],
        "error_code": None,
    }
    return build_envelope(
        result,
        document_id="document-1",
        source_id="source-1",
        capture_id="capture-1",
        artifact_id="artifact-1",
        options_digest=options_digest,
        output_refs=["derived/sha256/document-1.md"],
        started_at="2026-10-23T10:00:00+00:00",
        completed_at="2026-10-23T10:00:01+00:00",
    )


def make_spine(processor, permissions=("ocif.document.process",)) -> OISSpine:
    registry = CapabilityRegistry()
    registry.register(OCIFDocumentProcessingCapability(processor, sleep=lambda _seconds: None))
    return OISSpine(
        registry,
        policy=DefaultPolicyEngine(allowed_permissions=permissions),
    )


def make_request(envelope: dict) -> SpineRequest:
    return SpineRequest(
        objective="Process an approved hash-bound PDF artifact",
        capability_id="ocif.document.process",
        capability_version="1.0.0",
        tenant_id="tenant-test",
        input=to_ois_input(envelope),
    )


def test_envelope_reaches_real_ois_document_capability() -> None:
    envelope = make_envelope()

    def processor(payload):
        return {
            "extraction_status": "success",
            "artifact_sha256": payload["artifact_sha256"],
            "processor_id": "docling",
            "processor_version": "2.0.0",
            "output_refs": envelope["output_refs"],
            "warnings": [],
        }

    result = make_spine(processor).submit(make_request(envelope), invocation_id="doc-process-1")
    assert result.status == "succeeded"
    assert result.output["capture_id"] == envelope["capture_id"]
    assert result.output["artifact_sha256"] == envelope["artifact_sha256"]
    assert result.output["idempotency_key"] == envelope["idempotency_key"]


def test_ois_policy_denial_prevents_document_processor_invocation() -> None:
    envelope = make_envelope()
    called = False

    def processor(_payload):
        nonlocal called
        called = True
        return {}

    result = make_spine(processor, permissions=()).submit(
        make_request(envelope), invocation_id="doc-process-denied"
    )
    assert result.status == "denied"
    assert called is False
