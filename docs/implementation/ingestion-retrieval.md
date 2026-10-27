# OCIF Ingestion and Retrieval Baseline

**Status:** Implemented in a feature branch; not locally executed or integration-certified.  
**Contract:** candidate wire version `0.1.0`; the cross-repository contract remains subject to joint review.

## Implemented

- Strict envelope validation for the candidate USIE-to-OCIF contract.
- Absolute HTTP(S) URL validation; embedded credentials are rejected.
- Finalized capture outcomes only: `success`, `partial`, `blocked`, `unavailable`, `failed`, `cancelled`.
- Successful capture requires successful extraction, non-empty extracted text, artifact-backed provenance, and matching SHA-256 references.
- SQLite import ledger with unique `(source_id, capture_id, contract_version)` key.
- Exact duplicate delivery is idempotent. A repeated key with changed payload is rejected and quarantined; recaptures with a new capture ID remain separate.
- Append-only import events and quarantine reasons. Rejected raw payloads are not stored.
- Deterministic character/paragraph chunking and a lexical retrieval baseline. Only evidence-linked success/partial text is indexed.
- Retrieval returns source ID, capture ID, URL, chunk ID, capture status, artifact IDs/hashes and locators.
- Golden-query metrics: recall@k, MRR and precision@k.
- Reliability metrics: outcome counts/rates, duplicate rate, quarantine count, provenance completeness, ingest latency and aggregate retrieval metrics.

## Local verification

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check src tests
```

These commands are the required verification sequence; no result is claimed until they are run against the branch.

## Known limits

- The current retrieval implementation is a deterministic lexical baseline, not vector search, semantic reranking or an LLM research agent.
- The consumer accepts a JSON envelope; it does not fetch URLs, access USIE's database directly, or expose an HTTP endpoint.
- The USIE export adapter verifies artifact files on the producer side, but the current consumer verifies envelope hashes and references, not remote file bytes. An authorized artifact-resolution interface is still required for end-to-end byte verification.
- Scope/tenant authorization is not implemented in the local SQLite store. Do not expose this store to multi-tenant users or treat post-retrieval filtering as a security boundary.
- The import API does not itself grant execution permission. Any scheduled or externally triggered workflow must pass through a trusted OIS capability and policy boundary.
- Contract version `0.1.0` is a candidate until USIE and OCIF owners approve the mapping and fixtures.

## Acceptance gate

Before marking this integrated: run unit tests; test against a disposable USIE database and evidence directory; verify tampered/missing artifacts; verify denied OIS authorization creates no import; test bounded retries and recovery; and record actual revisions, test counts, exit codes and evidence IDs.
