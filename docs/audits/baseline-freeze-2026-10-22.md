# Repository Baseline Freeze — Social Intelligence OS

**Snapshot date:** 2026-10-22  
**Scope:** OCIF, USIE, OIS, OPI, NUEGS  
**Method:** GitHub remote metadata, recursive repository trees, open pull requests, and GitHub Actions run/job metadata. No local checkout or shell execution was available through this audit.  
**Working-tree state:** Not observable remotely; do not interpret as clean.

## 1. Default-branch baseline

| Repository | Default branch | HEAD commit | Git tree SHA | Source state |
|---|---|---|---|---|
| [OCIF](https://github.com/niceoneobsidian/obsidian-content-intelligence-factory) | `main` | `5b72f96c969b1a40bd7f1f24d59e455c13ea925a` | `92a737a300f0218aba7940b10a077be9880d84b7` | Architecture, boundaries, contract, roadmap and gates are on main; consumer implementation is in PR #2. |
| [USIE](https://github.com/niceoneobsidian/universal-social-intelligence) | `main` | `75fe1c23545c05c7d0894a3e6550f22f7cd2348e` | `a3107749b3bb48cc28e477839e544e0ce85c849c` | Capture/evidence/extraction foundation and tests exist; OCIF export adapter is in PR #6. |
| [OIS](https://github.com/niceoneobsidian/niceone-obsidian) | `main` | `7b94c0bc749681241ce2e7fa22aceb929c089591` | `b9072533deecb112ccff9319e8c61ac361c8c1e2` | Existing social-growth, PostgreSQL and governance infrastructure; OCIF governed execution changes are in PR #251. |
| [OPI](https://github.com/niceoneobsidian/obsidian-project-intelligence) | `main` | `db10b58e5e91b7ef264d999e0f94c6262a688b2c` | `586aaa9136ec9577bf35396f651d384964065662` | Task model, integration adapter, runtime bridge and tests exist. |
| [NUEGS](https://github.com/niceoneobsidian/niceone-engineering-governance) | `main` | `e0ba4d4f6c356c2a69e1a5481c82ef2f6b1bff7e` | `c59ed39c64f4acc15564861977671e527978646f` | Policy/schema tests, registry validation and adoption evidence exist. |

These hashes identify the remote branch snapshot observed during the audit. They do not describe uncommitted local files.

## 2. CI and test evidence observed

| Repository / ref | Evidence | Result | Interpretation |
|---|---|---|---|
| OCIF PR #2, `0806867121c3c905ce4414ce38f7e30cf774a53e` | [OCIF CI run 39878578964](https://github.com/niceoneobsidian/obsidian-content-intelligence-factory/actions/runs/39878578964) | Passed | Python 3.12 lint and test job passed with PostgreSQL service and pinned USIE checkout. This is branch CI, not main. |
| USIE PR #6, `2330a6fc8f1552695f880d3b1070f19964db1b5c` | [USIE CI run 39878011551](https://github.com/niceoneobsidian/universal-social-intelligence/actions/runs/39878011551) | Passed | Formatting, lint, types and complete test-suite steps passed on the export branch. |
| OIS PR #251, `01055fe66ce8ba8ce8d44d0043651019eb0f9378` | [Architecture/conformance run 39878589272](https://github.com/niceoneobsidian/niceone-obsidian/actions/runs/39878589272) | Passed | Architecture, conformance and integration job passed on the PR branch. |
| OIS PR #251 | [OSV Scanner run 39878589502](https://github.com/niceoneobsidian/niceone-obsidian/actions/runs/39878589502) | Failed | The scan step succeeded, but the report step failed. Treat the security workflow as unresolved until diagnosed. |
| OIS main | [Gitleaks run 39752580371](https://github.com/niceoneobsidian/niceone-obsidian/actions/runs/39752580371) | Failed | Main has a recorded secret-scan failure; investigate before release. |
| OPI main, `db10b58e5e91b7ef264d999e0f94c6262a688b2c` | [CI run 39248296207](https://github.com/niceoneobsidian/obsidian-project-intelligence/actions/runs/39248296207) | Failed | OPI is not CI-green on the observed default-branch head. Fetch job logs and repair before claiming integration readiness. |
| NUEGS main, `e0ba4d4f6c356c2a69e1a5481c82ef2f6b1bff7e` | [Validation run 39443482339](https://github.com/niceoneobsidian/niceone-engineering-governance/actions/runs/39443482339) | Passed | Registry/policy tests, registry validation and profile resolution passed. |

CI evidence is scoped to the named SHA and job. A successful PR job does not establish that a PR is merged, that every required check passed, or that production infrastructure has been exercised.

## 3. Active implementation PRs — do not duplicate

- OCIF [PR #2](https://github.com/niceoneobsidian/obsidian-content-intelligence-factory/pull/2): evidence-first importer, SQLite reference store, PostgreSQL consumer store, quarantine/idempotency, retrieval evaluation and restart/replay tests. Draft; contract approval and full integration acceptance remain open.
- OCIF [PR #3](https://github.com/niceoneobsidian/obsidian-content-intelligence-factory/pull/3): implementation-gap audit and delivery plan.
- USIE [PR #6](https://github.com/niceoneobsidian/universal-social-intelligence/pull/6): read-only OCIF export adapter from canonical `captures`, `sources`, `artifacts` and `extraction_results`; producer-side tests.
- OIS [PR #251](https://github.com/niceoneobsidian/niceone-obsidian/pull/251): governed OCIF import capability and production-shaped composition with PostgreSQL-backed OIS execution, evidence and idempotency stores. Multi-tenant isolation and production conformance remain release gates.

## 4. Baseline decisions

1. USIE's append-only `captures` table is canonical; `social_evidence` is a lossy, read-only compatibility view and is not an import source.
2. USIE owns capture history and artifact storage. OCIF imports validated envelopes, approved excerpts and provenance; it must not silently assume access to USIE's private evidence directory.
3. `ocif.usie-import` version `0.1.0` is a **candidate**, not yet a jointly approved stable contract. Preserve exact statuses: `success`, `partial`, `blocked`, `unavailable`, `failed`, `cancelled`.
4. Contract approval requires exact producer/consumer fixture parity, including timestamps, error/status reason, artifact fields, extraction field provenance and artifact integrity behavior.
5. OCIF PostgreSQL import must pass real database integration tests for duplicate delivery, changed-payload conflict, quarantine, transaction behavior, process restart and replay.
6. OIS must prove authorization denial before consumer invocation, stable invocation identity and durable recovery with the actual PostgreSQL OCIF consumer—not only an injected importer.
7. Evidence retrieval must use a fixed golden-query dataset and report recall@k, MRR and precision@k; no quality claim without a measured baseline.
8. End-to-end content workflow remains incomplete until evidence → brief → scored draft → version-bound human approval → governed execution boundary → measured outcome is tested.
9. Human approval remains mandatory before any external publishing action. No direct publishing is enabled by this baseline.
10. The local working tree, branch protection, uncommitted changes and secrets outside GitHub are explicitly outside this remote snapshot.

## 5. Immediate blockers

1. Diagnose OIS main Gitleaks failure and the OIS PR OSV report-step failure.
2. Diagnose OPI main CI failure.
3. Review/merge only after the OCIF, USIE and OIS PR heads have all required checks green and code review confirms contract parity.
4. Run the PostgreSQL restart/replay test in CI with the real OCIF `PostgresOCIFStore` and real USIE export fixture.
5. Record an explicit contract approval decision after fixture parity and status semantics are verified.
6. Produce retrieval evaluation output and a complete human-approval-to-outcome integration trace before declaring the vertical slice complete.

## 6. Evidence boundary

This is a remote metadata and repository-source audit. It is not a local checkout report, a complete branch-protection audit, a secrets clearance, or a production deployment attestation. Any unknown result must remain `not_assessed` until backed by fresh evidence.
