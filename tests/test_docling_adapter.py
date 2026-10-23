from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "tools" / "docling_adapter.py"
SPEC = importlib.util.spec_from_file_location("docling_adapter", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_rejects_hash_mismatch_before_loading_docling(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.7 fixture")
    with pytest.raises(ValueError, match="artifact_hash_mismatch"):
        MODULE.extract_pdf(pdf, expected_sha256="0" * 64)


def test_rejects_empty_and_oversized_inputs(tmp_path: Path) -> None:
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="empty_document"):
        MODULE.extract_pdf(empty, expected_sha256=hashlib.sha256(b"").hexdigest())

    pdf = tmp_path / "large.pdf"
    pdf.write_bytes(b"%PDF-1.7" + b"x" * 20)
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="document_size_limit_exceeded"):
        MODULE.extract_pdf(pdf, expected_sha256=digest, max_bytes=10)
