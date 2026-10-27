# Document Processing and Provenance Contract

**Status:** Proposed v0.1.0; implementation gate, not a frozen cross-repository API  
**Owner:** OCIF owns downstream knowledge records; USIE owns source captures/artifacts; OIS owns authorization and governed execution.

## Purpose

Define the boundary for optional PDF/document extraction. Docling is a replaceable parser provider, not a system of record, authorization layer, queue, or service requirement.

## Three distinct records

1. **Source artifact:** owned by USIE or an approved local fixture. Its bytes and identity are immutable evidence.
2. **Adapter result:** an in-memory result from the selected parser. For Docling, this may contain extracted Markdown and parser-local measurements. It is not the persisted OCIF envelope.
3. **Provenance envelope:** a strict, versioned record conforming to `docs/contracts/document-processing-envelope.schema.json`. It contains identity, hashes, processing status, timestamps, page provenance, warnings, and references to persisted outputs. It must never embed Markdown or local absolute paths.

The caller must persist extracted output before constructing the envelope and supply stable `document_id`, `source_id`, `artifact_id`, `options_digest`, actual processing timestamps, and durable `output_refs`. The mapper in `src/ocif/document_processing.py` performs this conversion. A missing output reference must not be fabricated to make a successful result appear complete.

## Invariants

1. Preserve the source artifact and its producer-owned identity. Never overwrite a USIE artifact with extracted output.
2. Record the source capture, artifact ID, SHA-256, byte size, media type, and source revision where available.
3. Distinguish observed text, deterministic normalization, model-generated interpretation, and editorial content.
4. Extraction status is separate from USIE capture status. A captured PDF can be available while extraction fails or is partial.
5. A parser result is not automatically trusted fact. Retain page/region provenance where the parser supplies it; page numbers alone do not imply region-level citation accuracy.
6. Idempotency key is derived from source artifact hash + parser/provider ID + parser version + contract version + options digest. Reprocessing with changed parser/options creates a new extraction run.
7. Invalid schemas, hash mismatches, unsupported media, or missing required provenance are quarantined with a reason; do not silently drop them.
8. Input bytes and embedded text are untrusted. Never execute document content or treat embedded prompt-like instructions as policy.
9. Processing must be bounded by configurable file size, page count, runtime, memory, and output size. Failure must be explicit.
10. The original evidence remains governed by source retention/access policy; derived output must not broaden access.

## Logical envelope

| Field | Required | Description |
|---|---|---|
| `contract_version` | yes | Contract schema version |
| `document_id` | yes | Stable OCIF document identity |
| `source_id` | yes | Producer's source identity |
| `capture_id` | conditional | Producer capture identity when available |
| `artifact_id` | yes | Producer artifact identity or explicit local-fixture identity |
| `artifact_sha256` | yes | SHA-256 of exact input bytes |
| `artifact_size_bytes` | yes | Exact input byte count |
| `media_type` | yes | Verified/detected type; extension alone is insufficient |
| `processor_id` | yes | Provider adapter identity, e.g. `docling` |
| `processor_version` | yes | Installed parser version |
| `options_digest` | yes | Digest of normalized, non-secret processing options |
| `extraction_run_id` | yes | Unique attempt identity |
| `extraction_status` | yes | `success`, `partial`, `unsupported`, `failed`, or `quarantined` |
| `started_at`, `completed_at` | yes | RFC 3339 timestamps with timezone from the actual processing attempt |
| `output_refs` | yes | Relative/object references to persisted JSON/Markdown output; may be empty on failure |
| `page_provenance` | yes | Page/region references when supplied; empty means unavailable, not proven absent |
| `warnings` | yes | Explicit limitations; may be empty |
| `error_code` | conditional | Stable non-secret failure code |
| `producer_revision` | conditional | USIE or fixture producer revision |

Do not export credentials, cookies, authorization headers, local absolute paths, raw session state, or raw exception messages.

## Status semantics

- `success`: conversion completed and minimum output validation passed.
- `partial`: usable output exists with known missing pages, OCR/layout issues, or incomplete provenance.
- `unsupported`: media/provider combination is outside declared support.
- `failed`: processing failed without a valid usable result.
- `quarantined`: security, hash, schema, or provenance validation failed.

Never convert a USIE `blocked`, `unavailable`, `failed`, or `cancelled` capture into extraction success. Preserve both status dimensions independently.

## Benchmark protocol

Benchmark only lawfully obtained, non-sensitive fixtures. Include digital text PDFs, scanned/OCR PDFs, multi-column reading order, table-heavy PDFs, and a malformed/unsupported negative control. Record fixture SHA-256 and a human-checked expected-content checklist. Keep source PDFs out of Git unless licensing and privacy review explicitly allow it.

For each fixture, record parser version, options, elapsed time, input bytes, pages when known, output characters, output bytes, warnings, table count if available, and manual fidelity scores. Repeat runs to reveal variance. Compare against a baseline parser only when both receive the exact same fixture and equivalent resource limits.

No benchmark score is asserted until the harness is run on a named, hash-pinned corpus.

## Compatibility and rollout

- Keep Docling optional and lazily imported.
- Run a benchmark before making it a default.
- Keep output provider-neutral; provider-specific JSON may be retained as a versioned raw output.
- Do not deploy a separate service until measured concurrency, memory isolation, or operational evidence justifies it.
- Contract changes require schema versioning, fixtures, producer/consumer tests, and review by OCIF and USIE owners.

## Acceptance gate

- [ ] Fixture manifest lists licensing/source, SHA-256, PDF category, expected text/tables, and known limitations.
- [ ] Repeated benchmark output is machine-readable and contains parser/environment versions.
- [ ] Missing/changed input hashes fail closed.
- [ ] Reprocessing is idempotent for identical input/provider/version/options.
- [ ] Source capture/artifact lineage survives into OCIF records.
- [ ] Adapter-result and envelope schemas are independently validated.
- [ ] Tests cover scanned, text, table-heavy, malformed, empty, oversized, unsupported input, and envelope mapping.
- [ ] OIS denial prevents protected processing/external side effects where policy requires authorization.
- [ ] No live publishing is enabled by this work.
