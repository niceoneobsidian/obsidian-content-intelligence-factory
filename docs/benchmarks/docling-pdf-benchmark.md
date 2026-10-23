# Docling PDF Benchmark

**Status:** Harness specification; results pending execution against a real fixture corpus  
**Decision target:** Determine whether Docling improves extraction quality enough to justify an optional OCIF adapter.

## Required corpus

Keep fixtures outside Git by default. Store a local manifest with one entry per PDF: stable fixture name, source/license approval, category, SHA-256, byte size, expected page count if known, expected key phrases, expected tables/headers, and known defects. Minimum categories:

1. Digital-text PDF.
2. Scanned PDF requiring OCR.
3. Multi-column research paper.
4. Table-heavy report.
5. Malformed or unsupported PDF as a negative control.

A single PDF is a smoke test, not a representative benchmark.

## Run

From the repository root, in an isolated virtual environment:

```bash
python -m venv .venv-docling
source .venv-docling/bin/activate
python -m pip install --upgrade pip
python -m pip install docling
python tools/benchmark_docling_pdfs.py --input-dir /path/to/approved-pdf-fixtures --output benchmark-results.json
```

The first conversion may download parser models. Cache/model version and machine details must be recorded; do not run against confidential documents without approval.

## Measurements

- input SHA-256, bytes, parser/package version, Python version and platform;
- elapsed seconds, output bytes and characters, detected page count when available;
- success/failure, warning count and error code;
- manual fidelity ratings for reading order, tables, OCR, and citation/page provenance.

Use the same pinned corpus and environment for every comparison. Keep raw outputs out of Git when source documents are restricted. Report per-file results and category-level summaries; do not report only an average.

## Release gate

No production default or quality claim until:
- every fixture hash is verified;
- the corpus contains all four positive categories and a negative control;
- output is inspected against the expected-content checklist;
- repeat runs and resource limits are recorded;
- extraction status and lineage pass the contract tests.

**Current result:** not run in this repository session. No PDF fixture corpus was provided, and the remote GitHub connector cannot execute the script or install Docling.