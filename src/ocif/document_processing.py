"""Map a Docling adapter result into the versioned OCIF provenance envelope."""
import hashlib
import re
import uuid


_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")


def build_envelope(
    result: dict,
    *,
    document_id: str,
    source_id: str,
    artifact_id: str,
    options_digest: str,
    output_refs: list[str],
    started_at: str,
    completed_at: str,
    extraction_run_id: str | None = None,
    capture_id: str | None = None,
    producer_revision: str | None = None,
) -> dict:
    """Build envelope metadata after extracted Markdown has been persisted.

    Markdown is deliberately not copied into this envelope. The caller supplies
    real processing timestamps and durable output references.
    """
    if not document_id or not source_id or not artifact_id:
        raise ValueError("document_id_source_id_and_artifact_id_required")
    artifact_hash = str(result.get("artifact_sha256", ""))
    if not _SHA256.fullmatch(artifact_hash):
        raise ValueError("invalid_artifact_sha256")
    if not _SHA256.fullmatch(options_digest):
        raise ValueError("invalid_options_digest")
    if int(result.get("artifact_size_bytes", 0)) < 1:
        raise ValueError("invalid_artifact_size")
    if not started_at or not completed_at:
        raise ValueError("processing_timestamps_required")
    if any(not ref or ref.startswith("/") or chr(92) in ref for ref in output_refs):
        raise ValueError("invalid_output_reference")
    if any(any(part == chr(46) * 2 for part in ref.split("/")) for ref in output_refs):
        raise ValueError("invalid_output_reference")
    status = result.get("extraction_status")
    if status not in {"success", "partial", "unsupported", "failed", "quarantined"}:
        raise ValueError("invalid_extraction_status")
    if status in {"success", "partial"} and not output_refs:
        raise ValueError("output_refs_required_for_usable_result")
    if status in {"unsupported", "failed", "quarantined"} and output_refs:
        raise ValueError("output_refs_forbidden_without_usable_result")
    page_count = result.get("page_count")
    if page_count is not None and (not isinstance(page_count, int) or page_count < 0):
        raise ValueError("invalid_page_count")
    processor_id = str(result["processor_id"])
    processor_version = str(result["processor_version"])
    stable_key = ":".join(
        (artifact_hash.lower(), processor_id, processor_version, "0.1.0", options_digest.lower())
    )
    idempotency_key = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
    return {
        "contract_version": "0.1.0",
        "document_id": document_id,
        "source_id": source_id,
        "capture_id": capture_id,
        "artifact_id": artifact_id,
        "artifact_sha256": artifact_hash.lower(),
        "artifact_size_bytes": int(result["artifact_size_bytes"]),
        "media_type": result.get("media_type", "application/pdf"),
        "processor_id": processor_id,
        "processor_version": processor_version,
        "options_digest": options_digest.lower(),
        "extraction_run_id": extraction_run_id or str(uuid.uuid4()),
        "idempotency_key": idempotency_key,
        "extraction_status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "output_refs": list(output_refs),
        "page_provenance": (
            [{"page_number": page} for page in range(1, page_count + 1)]
            if page_count is not None else []
        ),
        "warnings": list(result.get("warnings") or []),
        "error_code": result.get("error_code"),
        "producer_revision": producer_revision,
    }


def to_ois_input(envelope: dict) -> dict:
    """Map the provenance envelope to the least-privilege OIS capability input."""
    required = (
        "source_id",
        "capture_id",
        "artifact_id",
        "artifact_sha256",
        "artifact_size_bytes",
        "media_type",
        "options_digest",
        "idempotency_key",
    )
    missing = [field for field in required if envelope.get(field) in (None, "")]
    if missing:
        raise ValueError("missing_ois_capability_fields:" + ",".join(missing))
    return {field: envelope[field] for field in required}
