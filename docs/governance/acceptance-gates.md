# OCIF Acceptance Gates

**Status:** Proposed project gates; map to the current NUEGS profile/control registry before marking any control applicable or verified.

## Evidence-state vocabulary

Use the OIS capability lifecycle without collapsing states:

`UNKNOWN → DESIGNED → IMPLEMENTED → TESTED → INTEGRATED → DEPLOYED → ACTIVATED → PRODUCTION VERIFIED`

A document or plan can establish DESIGN intent only. A unit test does not establish integration, deployment or production verification. Missing evidence is `not_assessed`, not a pass.

## Gate G0 — Repository baseline and governance mapping

**Exit criteria**
- Record default branch, current commit, tree inventory, CI configuration and test commands for OCIF, USIE, OIS, OPI and NUEGS.
- Run or record the exact latest available tests for each repository; label remote-only inspection separately from locally executed tests.
- Map applicable NUEGS controls to repository artifacts, owners, verification methods and evidence locations.
- Confirm license and data-handling constraints before copying code or datasets.
- Assign owners to gaps and create tracked work items through the approved OPI/project workflow.

**Evidence:** baseline report, revisions, command outputs, control mapping, open-risk list.

## Gate G1 — Architecture and contract approval

**Exit criteria**
- Review system boundaries and authority ownership.
- Approve ADRs for knowledge schema, persistence, USIE integration mechanism, OPI linkage and publishing boundary.
- Producer and consumer agree on a versioned USIE-to-OCIF contract and failure semantics.
- Security/privacy review covers authorization, untrusted source content, retention, access and data movement.

**Evidence:** reviewed ADRs, contract version, approvals, test fixtures.

## Gate G2 — Evidence ingestion

**Exit criteria**
- Import fixtures for all supported status outcomes.
- Verify provenance, artifact hashes, duplicate handling, recapture history and unknown-version behavior.
- Test malformed payloads, missing/tampered evidence, secrets redaction and untrusted content.
- Demonstrate bounded retry and recovery without overwriting source history.
- Explicitly state platform and extraction coverage. Do not infer it from URL routing or browser capture.

**Evidence:** passing producer/consumer contract tests and a reproducible integration run against disposable data.

## Gate G3 — Knowledge and retrieval

**Exit criteria**
- Approved schema separates evidence, normalized facts and model-generated interpretations.
- Every derived claim can resolve to supporting evidence or is explicitly marked unsupported/uncertain.
- Create a fixed evaluation set for retrieval and research tasks, with expected relevant evidence and scoring criteria.
- Measure citation/provenance coverage, retrieval relevance, duplicate rate and unsupported-claim rate.
- Protect against prompt injection in collected content.

**Evidence:** schema/version, fixtures, evaluation results, known limitations and failure examples.

## Gate G4 — Content workflow

**Exit criteria**
- Versioned brief, draft, edit, review, approval and rejection states exist.
- Content artifacts preserve links to source evidence and the versions of prompts/models/rules used.
- Fact checks and policy checks run before editorial approval.
- Human approval is required before external publication in the initial release.
- Publishing secrets and authenticated sessions are kept outside source control.

**Evidence:** workflow tests, audit trail, approval-denial tests, sample evidence-linked draft.

## Gate G5 — Cross-system integration

**Exit criteria**
- Verify actual OPI task/project interface and OIS authorization/execution interfaces before wiring adapters.
- End-to-end test from OPI-originated objective to USIE evidence import, OCIF draft, approval and measurement using test fixtures or authorized test accounts.
- Validate identity/correlation IDs, idempotency, timeout, duplicate delivery, recovery and error propagation.
- Prove unauthorized publishing and invalid approval are denied at the trusted execution boundary.

**Evidence:** integration run, exact revisions, traces, negative-test outputs and recovery report.

## Gate G6 — Dashboard and operational readiness

**Exit criteria**
- Build the dashboard against stable, versioned API/data contracts, not provisional internal tables.
- Access control, data minimization, observability, retention/deletion, backup/restore, rollback and operational ownership are documented and tested.
- CI and security scans pass; dependency and license review is recorded.
- Deployment and recovery are demonstrated in a controlled environment.
- Independent reviewer signs off on release scope and remaining risks.

**Evidence:** CI links, security review, deployment/restore/rollback run, dashboard contract tests and independent acceptance.

## Required report fields for every gate

- Gate and criterion ID
- Applicable NUEGS control ID and profile revision
- Repository and exact commit SHA
- Verification method and exact command or test
- Result, timestamp, actor and independent reviewer where required
- Evidence URL or artifact location
- Scope and limitations
- Open risks and owner
- Decision: pass, partial, blocked or not assessed

## Governance constraints

The current NUEGS README says its v1.0 release gates remain open. OCIF can adopt its documented principles as project controls, but must not claim formal NUEGS adoption/compliance until applicable controls are mapped and verified against the live specification and enforcement paths.
