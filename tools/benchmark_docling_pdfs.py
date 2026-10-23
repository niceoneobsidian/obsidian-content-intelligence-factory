#!/usr/bin/env python3
"""Benchmark an approved local PDF corpus with optional Docling installed.

The script never sends document contents to a remote service. First-run Docling
model downloads may occur when conversion starts. Results omit local paths and
raw exception messages to avoid leaking environment details.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def convert(path: Path) -> tuple[dict[str, Any], str | None]:
    started = time.perf_counter()
    record: dict[str, Any] = {
        "file_name": path.name,
        "input_sha256": sha256_file(path),
        "input_bytes": path.stat().st_size,
        "status": "failed",
        "warnings": [],
        "output_characters": 0,
        "output_bytes": 0,
        "elapsed_seconds": None,
        "page_count": None,
        "error_code": None,
    }
    try:
        from docling.document_converter import DocumentConverter
        from importlib.metadata import version

        record["processor"] = "docling"
        record["processor_version"] = version("docling")
        document = DocumentConverter().convert(str(path)).document
        markdown = document.export_to_markdown()
        record["output_characters"] = len(markdown)
        record["output_bytes"] = len(markdown.encode("utf-8"))
        pages = getattr(document, "pages", None)
        if pages is not None:
            record["page_count"] = len(pages)
        if not markdown.strip():
            record["status"] = "partial"
            record["warnings"].append("empty_markdown_output")
        else:
            record["status"] = "success"
        record["output_markdown"] = markdown
    except Exception as exc:  # record stable error class, then continue the corpus
        record["error_code"] = type(exc).__name__
    finally:
        record["elapsed_seconds"] = round(time.perf_counter() - started, 4)
    return record, record.pop("output_markdown", None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("benchmark-results.json"))
    parser.add_argument("--max-files", type=int, default=0, help="0 means all PDFs")
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        parser.error("input directory does not exist")
    if args.max_files < 0:
        parser.error("--max-files must be >= 0")

    files = sorted(
        path for path in args.input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    if args.max_files:
        files = files[: args.max_files]
    if not files:
        parser.error("no PDF fixtures found; no benchmark was run")

    rows: list[dict[str, Any]] = []
    output_dir = args.output.parent / f"{args.output.stem}-markdown"
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        record, markdown = convert(path)
        if markdown is not None:
            safe_name = f"{record['input_sha256'][:16]}.md"
            markdown_path = output_dir / safe_name
            markdown_path.write_text(markdown, encoding="utf-8")
            record["markdown_output_file"] = safe_name
        rows.append(record)

    summary = {
        "benchmark_schema_version": "0.1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "fixture_count": len(rows),
        "success_count": sum(row["status"] == "success" for row in rows),
        "partial_count": sum(row["status"] == "partial" for row in rows),
        "failed_count": sum(row["status"] == "failed" for row in rows),
        "results": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"fixtures={len(rows)} success={summary['success_count']} "
        f"partial={summary['partial_count']} failed={summary['failed_count']} "
        f"output_file={args.output.name}"
    )
    return 0 if summary["failed_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
