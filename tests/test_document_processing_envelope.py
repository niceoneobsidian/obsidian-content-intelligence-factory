from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ocif.document_processing import build_envelope


def adapter_result() -> dict:
    return {
        "contract_version": "0.1.0",
        "processor_id": "docling",
        "processor_version": "2.0.0",
        "artifact_sha256": hashlib.sha256(b"pdf").hexdigest(),
        "artifact_size_bytes": 3,
        "media_type": "application/pdf",
        "extraction_status": "success",
        "markdown": "extracted text must not be copied into envelope",
        "page_count": 2,
        "warnings": [],
        "error_code": None,
    }


def envelope_kwargs() -> dict:
    return {
        "document_id": "doc-1",
        "source_id": "source-1",
        "artifact_id": "artifact-1",
        "options_digest": hashlib.sha256(b"{}").hexdigest(),
        "output_refs": ["objects/sha256/abc.md"],
        "started_at": "2026-10-23T00:00:00+00:00",
        "completed_at": "2026-10-23T00:00:01+00:00",
    }


def test_envelope_maps_lineage_and_excludes_markdown() -> None:
    result = adapter_result()
    envelope = build_envelope(result, **(envelope_kwargs() | {"capture_id": "capture-1"}))

    assert envelope["document_id"] == "doc-1"
    assert envelope["capture_id"] == "capture-1"
    assert envelope["artifact_sha256"] == result["artifact_sha256"]
    assert envelope["page_provenance"] == [{"page_number": 1}, {"page_number": 2}]
    assert envelope["output_refs"] == ["objects/sha256/abc.md"]
    assert "markdown" not in envelope
    assert "extracted text must not be copied into envelope" not in json.dumps(envelope)


def test_envelope_rejects_missing_lineage_and_unsafe_output_refs() -> None:
    result = adapter_result()
    with pytest.raises(ValueError, match="document_id_source_id_and_artifact_id_required"):
        build_envelope(result, **(envelope_kwargs() | {"document_id": ""}))
    with pytest.raises(ValueError, match="invalid_output_reference"):
        build_envelope(result, **(envelope_kwargs() | {"output_refs": ["/private/local/path.md"]}))
    with pytest.raises(ValueError, match="invalid_output_reference"):
        build_envelope(result, **(envelope_kwargs() | {"output_refs": ["a/../private.md"]}))


def test_envelope_has_schema_required_fields() -> None:
    envelope = build_envelope(adapter_result(), **envelope_kwargs())
    schema_path = (
        Path(__file__).parents[1]
        / "docs"
        / "contracts"
        / "document-processing-envelope.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert set(schema["required"]).issubset(envelope)
    assert set(envelope).issubset(schema["properties"])
