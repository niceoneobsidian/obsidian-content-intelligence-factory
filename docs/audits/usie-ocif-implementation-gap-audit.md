# USIE / OCIF Implementation Gap Audit and Delivery Plan

**Audit type:** Remote read-only source inspection; no local checkout, code execution, CI run, API credential, or live provider request was available during this audit.
**USIE inspected revision:** `75fe1c23545c05c7d0894a3e6550f22f7cd2348e` (`main`).
**OCIF inspected revision:** `5b72f96c969b1a40bd7f1f24d59e455c13ea925a` (`main`).
**Decision:** Implement one evidence-first vertical slice before expanding providers or building a production dashboard.

## 1. Executive finding

USIE has meaningful implemented foundations for URL-based collection, security, evidence storage, generic metadata extraction, and tests. It does not yet implement a provider-neutral social API feed or webhook receiver.

OCIF is currently an architecture/planning baseline: the inspected tree contains README, AGENTS.md, and documentation/contracts, but no application source package, executable API, persistence implementation, or test suite. Its USIE-to-OCIF contract explicitly says it is a draft and not an implemented API/export format.

Therefore the integration, knowledge/retrieval, trend-analysis, editorial, publishing, and measurement capabilities are targets, not working application features at the inspected revision.

## 2. Evidence: implemented vs documented

### USIE — implemented in source tree

- `src/usie/urlsafety.py`, `routing.py`: URL validation, normalization and platform routing.
- `src/usie/capture/browser.py`, `capture/proxy.py`: browser capture and destination filtering.
- `src/usie/db/migrations.py`, `db/repository.py`: SQLite schema/migrations and repository operations for runs, jobs, sources, captures/artifacts and audit.
- `src/usie/evidence.py`: evidence file storage/integrity primitives.
- `src/usie/extraction/base.py`, `extraction/opengraph.py`: extraction protocol and generic Open Graph/Twitter Card/JSON-LD extraction from saved DOM.
- `src/usie/collector.py`, `cli.py`, `status.py`: collection orchestration, CLI and status classification.
- Tests exist for architecture/CLI, browser integration, collector, DB, evidence, extraction, logging/config, proxy, repository, routing, status, and URL safety.

The repository's P0 acceptance document reports 147 tests passing in a Linux/Python 3.12 environment, while explicitly stating that live social platforms and macOS were not verified. This audit did not rerun those tests.

### USIE — not implemented/verified in inspected tree

- Official platform API adapters and credential lifecycle.
- Provider-neutral API response contracts and normalized API observations.
- Rate-limit/quota scheduler for external APIs.
- Inbound webhook server, signature verification, durable inbox, replay protection and delivery idempotency.
- Verified live platform API integration or production certification.

### OCIF — implemented at the inspected revision

- README architecture and repository boundaries.
- Proposed USIE-to-OCIF evidence contract.
- Proposed system boundaries, roadmap, acceptance gates, and agent operating rules.

### OCIF — documented/planned, not implemented at the inspected revision

- Application package and runtime/API.
- Persistent knowledge/observation/claim models.
- USIE importer, contract validator, quarantine and idempotent import.
- Retrieval/evaluation pipeline and evidence-linked research generation.
- Trend metrics and topic/entity analysis.
- Content brief/draft/version/review/approval workflow.
- Publishing adapters and performance measurement.
- Dashboard, operational telemetry and end-to-end tests.

## 3. Required architecture decisions

1. USIE remains canonical for capture history, evidence artifacts and acquisition outcomes.
2. API records must be modeled as API observations, not forged into rendered-DOM captures. Share provenance primitives, but keep acquisition-specific schemas explicit.
3. OCIF stores references, hashes, approved excerpts and normalized facts as permitted; it does not silently duplicate raw capture stores.
4. The importer must preserve exact outcome semantics and reject/quarantine unknown or malformed contract versions.
5. Source text is untrusted input. Separate observed fields, deterministic normalization, model inference and editorial content.
6. OIS remains the authorization boundary for consequential external effects. Human approval remains required before external publishing in the initial release.
7. Dashboard implementation follows stable contracts, not provisional database tables.

## 4. Platform recommendation

**First adapter: YouTube Data API, read-only.** This fits creator/topic research in AI, software engineering and automation and returns structured resources. The official documentation currently specifies a default `search.list` limit of 100 calls/day; account for this explicitly. It is not a push-stream/webhook feed.

Do not start with Reddit for commercial trend research until its current terms/access pathway are reviewed for this exact use. Reddit's 2026 official guidance says research access is through Reddit for Researchers and restricts model training/commercial use. X may be a subsequent adapter if the required access tier and cost are confirmed. Provider choice must follow current terms, quota and required fields, not assumptions about “free” access.

References:
- https://developers.google.com/youtube/data/getting-started
- https://developers.google.com/youtube/v3/docs/search/list
- https://developers.google.com/youtube/data/determine_quota_cost
- https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data

## 5. Exact delivery sequence

### M0 — Freeze the baseline (USIE + OCIF)
**Work:** Record exact revisions, CI commands/results, schema versions, current extractor coverage and runtime constraints. Execute tests from local checkouts before behavior changes.
**Acceptance:** reproducible baseline report with commands, exit codes and exact commits; remote-only observations clearly labeled.
**Tests:** existing USIE `pytest`, `ruff check src tests`, `mypy`; OCIF test/build command documented as unavailable until a package exists.

### M1 — Approve data contract
**Work:** Upgrade `docs/contracts/usie-to-ocif.md` from draft to a reviewed producer/consumer contract. Define API observation vs capture, idempotency key, status mapping, timestamps, hashes, retention/deletion and producer version.
**Acceptance:** schema examples validate; no unsupported field or endpoint claims; status semantics are lossless.
**Tests:** JSON-schema/Pydantic valid/invalid fixtures; unknown version, unknown status, missing provenance, duplicate IDs and secret-redaction cases.

### M2 — USIE API vertical slice
**Work:** Add YouTube read-only adapter behind an injectable transport; implement explicit quota accounting, bounded pagination and typed errors.
**Acceptance:** actual authorized test request works with secret supplied out of band; fixtures reproduce results offline; quotas/errors are visible; no data stored outside approved retention policy.
**Tests:** success, empty results, malformed JSON/schema, 401/403, 429/retry-after, 5xx timeout, cancellation, quota exhaustion, redaction, idempotent re-fetch and provider field omissions.

### M3 — USIE durable observation and export
**Work:** Add versioned migrations/repository methods for provider observations and a sanitized export/fixture command. Keep existing capture history and compatibility view semantics unchanged.
**Acceptance:** new API observations are append-only, hash/provenance verified and exportable; failed migration leaves prior DB usable.
**Tests:** migration-upgrade/failure, transaction rollback, duplicate import, changed observation, crash recovery, tamper detection, data minimization and CLI tests.

### M4 — OCIF runnable foundation
**Work:** Create package layout, configuration, persistence abstraction, migration strategy, CI, typed domain models for `EvidenceReference`, `Observation`, `Claim`, and `ResearchBrief`. Do not implement a large UI yet.
**Acceptance:** fresh checkout installs; lint/typecheck/tests pass; records link to source/capture/artifact hashes; no raw secret/session material.
**Tests:** model validation, migrations, provenance invariants, retention/deletion, untrusted content handling and clean-environment CI.

### M5 — OCIF importer and evidence store
**Work:** Implement a versioned USIE contract consumer, deterministic normalization, idempotent import and quarantine.
**Acceptance:** importing the same capture twice produces one logical import; a later capture remains a separate observation; source history stays in USIE.
**Tests:** producer/consumer contract fixtures for success, partial, blocked, unavailable, failed and cancellation/interruption; missing/tampered artifact, unsupported schema, duplicate delivery, restart recovery and cross-repo contract compatibility.

### M6 — Research and retrieval
**Work:** Add topic/entity tags, evidence-linked claims, retrieval and a fixed evaluation set. Keep model-generated inferences distinct from observations.
**Acceptance:** each material claim links to supporting evidence or is explicitly uncertain/unsupported; freshness and coverage are visible.
**Tests:** retrieval relevance baseline, citation/provenance coverage, unsupported-claim rate, duplicate rate, stale evidence, contradictory evidence and prompt-injection fixtures.

### M7 — Research brief and content workflow
**Work:** Generate structured research briefs, then platform-specific drafts with model/prompt/rule versions, review history, approve/reject states and human approval.
**Acceptance:** complete trace from source observation to draft; no external publishing before human approval.
**Tests:** evidence-link preservation, fact-check failures, review/rejection, revision history, unauthorized publish denied and audit trace completeness.

### M8 — OIS integration, publishing and measurement
**Work:** Verify the live OIS authorization/execution API first; integrate only through that boundary. Add one provider only after auth, terms, idempotency and reconciliation review.
**Acceptance:** positive and negative authorization tests pass; publication results and metrics are traceable; rollback/reconciliation are documented.
**Tests:** denied approval, expired/replayed approval, duplicate action, timeout-after-success, provider rate limit, recovery and measurement fixture integrity.

### M9 — Dashboard and operations
**Work:** Build against stable versioned APIs. Add access controls, observability, backup/restore, retention/deletion, deployment and rollback.
**Acceptance:** independent G0–G6 review, controlled deployment/recovery evidence, no unverified production claims.
**Tests:** API contract, access control, load/latency target, restore/rollback drill, secret scan, dependency/license review and security acceptance.

## 6. Release blockers

- No OCIF executable application exists at the inspected revision.
- No USIE API adapter or webhook receiver exists at the inspected revision.
- The producer/consumer contract is draft and has no implemented export/import integration.
- No live platform API call, cross-repository integration test, or production deployment was verified during this remote audit.
- Provider terms, quotas, retention and commercial permissions must be reviewed before real collection at scale.

## 7. Verification status of this report

This report is based on GitHub tree/file inspection and official provider documentation. No source code was changed as part of the audit itself, and no local test command was run. It is a source-grounded implementation plan, not a production-readiness attestation.
