# USIE-to-OCIF Evidence Contract

**Contract ID:** `ocif.usie-import`  
**Version:** `0.1.0-draft`  
**Status:** Candidate contract implemented in open PRs; not merged or stable

## 1. Purpose

Define the minimum information OCIF needs to import USIE collection/extraction outcomes without taking ownership of USIE's canonical data or losing provenance.

This document is a proposed consumer contract. It does not assert that USIE currently exposes a JSON export endpoint, public SDK, or stable API. The implementation mechanism must be selected after inspecting the current USIE CLI, repository interfaces, schema and tests.

## 2. Contract rules

1. Use canonical `captures` and associated artifact/extraction records, not the lossy `social_evidence` compatibility view, when the distinction between outcomes matters.
2. Never infer successful extraction from a page load, screenshot, DOM snapshot or HTTP 200 alone.
3. Every imported observation must have stable source identity, capture identity, explicit outcome, timestamps and provenance.
4. Import is idempotent for the same source capture and contract version; a later recapture is a new observation, not an overwrite.
5. This strict candidate rejects unknown fields; extensibility requires a reviewed contract-version change. Unknown data must not silently become trusted facts.
6. Invalid or incomplete records are quarantined/rejected with a reason. They must not silently disappear or be upgraded to success.
7. Raw evidence stays in USIE unless a reviewed data-transfer policy explicitly allows copying it. OCIF may store references, hashes, approved excerpts and normalized metadata.
8. Contract/schema changes are versioned and tested by both producer and consumer.

## 3. Required logical envelope

The exact field names are proposed and require mapping to the actual USIE schema.

| Field | Required | Meaning |
|---|---:|---|
| `contract_version` | Yes | Version of this consumer contract |
| `source_id` | Yes | USIE's stable source identifier |
| `submitted_url` | Yes | URL as submitted for the collection job, preserved verbatim |
| `normalized_url` | Yes | URL used for canonical source identity |
| `capture_id` | Yes | Unique capture attempt identifier |
| `capture_status` | Yes | Exact canonical USIE outcome; no lossy remapping |
| `status_reason` | Yes, when present | Evidence-based reason code or explanation |\n| `error_code` | Yes, when present | Canonical producer error code; never inferred by the consumer |
| `captured_at` | Yes | Timestamp with timezone |
| `completed_at` | Yes | Timestamp with timezone; accepted imports must be finalized |
| `artifacts[]` | Yes, possibly empty | Artifact ID/type, safe relative location, SHA-256, non-negative byte size and media type |
| `extraction` | Conditional | Extractor ID/version, schema version, validation outcome, fields and evidence references |
| `platform` | If known | Router/platform classification; not a guarantee of adapter support |
| `producer_revision` | Yes | USIE commit/version that produced the record |
| `warnings[]` | Yes, may be empty | Known limitations, incomplete extraction, blocked access or unsupported cases |

Do not include cookies, authorization headers, raw secrets, or unredacted session material in the envelope.

## 4. Outcome semantics

Preserve the exact canonical USIE status. This candidate accepts exactly `success`, `partial`, `blocked`, `unavailable`, `failed`, and `cancelled`. A new live-schema status must be mapped in a reviewed contract update; until then it is rejected/quarantined.

- `success`: accepted only when USIE's validated extraction rules say success.
- `partial`: evidence exists but required extraction or validation is incomplete.
- `blocked`: access denial or an observed access wall, according to USIE rules.
- `unavailable`: an observed not-found/unavailable outcome; do not infer deletion from a generic network error.
- `failed`: collection or processing failure with an error code/reason.
- `cancelled`: preserve the canonical value and reason; do not collapse it to `failed`.

The consumer must tolerate new statuses by safely quarantining unknown values and surfacing a compatibility error rather than guessing.

## 5. Extraction semantics

USIE's documented generic metadata adapter reads saved DOM evidence and does not fetch pages itself or provide platform-specific extraction. A browser-only capture is at best `partial`; `success` requires validated extraction, non-empty post text under current rules, and artifact-hash provenance.

OCIF must therefore model fields as:
- `observed`: directly supported by a referenced artifact;
- `normalized`: deterministically derived from observed fields;
- `inferred`: model-generated and accompanied by method/model version, confidence or uncertainty, and evidence references;
- `unknown`: not supported by available evidence.

A platform label is routing metadata, not proof that content extraction is implemented for that platform.

## 6. Idempotency and updates

- Suggested import key: `(source_id, capture_id, contract_version)`, subject to review.
- Reimporting the same key must not create duplicate knowledge observations.
- A new `capture_id` must create a new observation and preserve prior lineage.
- Corrections should be represented as versioned derived records or supersession links, not destructive edits to source evidence.
- If an artifact hash changes or referenced evidence is missing, mark provenance validation failed and quarantine the import.

## 7. Failure and retry behavior

Consumers must distinguish:
- schema/contract incompatibility (no blind retry);
- transient storage/transport failure (bounded retry with backoff);
- duplicate delivery (idempotent success);
- missing/tampered artifact (quarantine and alert);
- blocked/unavailable source (preserve observation; do not retry indefinitely);
- unsupported extraction (retain evidence and partial status).

All retry limits and quarantine behavior must be configured and tested, not improvised in an agent prompt.

## 8. Contract acceptance tests

Both repositories must test fixtures for:
- `success` with valid extraction and hashes;
- `partial` with evidence but no validated extraction;
- `blocked`;
- `unavailable`;
- `failed` with reason/error code;
- cancelled/interrupted if emitted by the selected schema;
- duplicate delivery of the same capture;
- recapture of the same source with a different capture ID;
- missing artifact, hash mismatch, malformed timestamp, unknown status and unknown contract version;
- secrets/redaction and hostile prompt-like content in source text.

## 9. Implementation sequence

1. Agent 1 documents actual USIE schema, CLI and existing export options from source code and tests.
2. Jointly map the proposed envelope to canonical fields and record differences.
3. Add producer-side fixture generation/export only after selecting an interface and approval.
4. Add OCIF consumer validation and contract tests using fixtures.
5. Run local integration tests against a disposable USIE data directory.
6. Record revisions, commands, outcomes and limitations. Do not claim live-platform support from fixture tests.

## 10. Source-of-truth references

- [USIE architecture](https://github.com/niceoneobsidian/universal-social-intelligence/blob/main/docs/ARCHITECTURE.md)
- [USIE decisions](https://github.com/niceoneobsidian/universal-social-intelligence/blob/main/docs/DECISIONS.md)
- [USIE P0 acceptance](https://github.com/niceoneobsidian/universal-social-intelligence/blob/main/docs/P0_ACCEPTANCE.md)
