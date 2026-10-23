"""Optional Docling adapter for the OCIF document-processing boundary.

This module is intentionally independent of OCIF persistence and OIS execution APIs.
Callers must authorize access, persist evidence, and record the returned metadata.
Install Docling separately; importing this module does not require Docling.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DocumentProcessingResult:
    contract_version: str
    processor_id: str
    processor_version: str
    artifact_sha256: str
    artifact_size_bytes: int
    media_type: str
    extraction_status: str
    markdown: str | None
    page_count: int | None
    warnings: tuple[str, ...]
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable result envelope."""
        result = asdict(self)
        result["warnings"] = list(self.warnings)
        return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_pdf(
    path: str | Path,
    *,
    expected_sha256: str,
    max_bytes: int = 50 * 1024 * 1024,
) -> DocumentProcessingResult:
    """Convert one local PDF without writing over its source artifact.

    Authorization, capture lineage, output persistence, timeouts, page limits,
    quarantine, and durable retry policy belong to the caller's governed boundary.
    This function verifies input identity and byte limits before importing Docling.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    size = source.stat().st_size
    if size <= 0:
        raise ValueError("empty_document")
    if max_bytes <= 0 or size > max_bytes:
        raise ValueError("document_size_limit_exceeded")
    actual_hash = _sha256(source)
    if actual_hash.lower() != expected_sha256.lower():
        raise ValueError("artifact_hash_mismatch")

    try:
        from docling.document_converter import DocumentConverter
        from importlib.metadata import version
    except ImportError as exc:
        raise RuntimeError("docling_optional_dependency_missing") from exc

    try:
        converted = DocumentConverter().convert(str(source))
        document = converted.document
        markdown = document.export_to_markdown()
        pages = getattr(document, "pages", None)
        page_count = len(pages) if pages is not None else None
        warnings: list[str] = []
        if not markdown.strip():
            warnings.append("empty_markdown_output")
            status = "partial"
        else:
            status = "success"
        if page_count is None:
            warnings.append("page_count_unavailable")
        return DocumentProcessingResult(
            contract_version="0.1.0",
            processor_id="docling",
            processor_version=version("docling"),
            artifact_sha256=actual_hash,
            artifact_size_bytes=size,
            media_type="application/pdf",
            extraction_status=status,
            markdown=markdown,
            page_count=page_count,
            warnings=tuple(warnings),
        )
    except Exception as exc:
        # Do not leak full document content or local paths into the error envelope.
        return DocumentProcessingResult(
            contract_version="0.1.0",
            processor_id="docling",
            processor_version=_installed_version(),
            artifact_sha256=actual_hash,
            artifact_size_bytes=size,
            media_type="application/pdf",
            extraction_status="failed",
            markdown=None,
            page_count=None,
            warnings=(),
            error_code=type(exc).__name__,
        )


def _installed_version() -> str:
    try:
        from importlib.metadata import version

        return version("docling")
    except Exception:
        return "unknown"
