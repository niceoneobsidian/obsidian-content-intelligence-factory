# OCIF Two-Agent Workstreams

## Coordination rule

Both agents read the current source code, tests, schemas and CI before proposing implementation. Agent ownership is a work boundary, not permission to redefine another system's canonical contract. Both agents share one reviewed contract and one evidence-based gate process.

## Agent 1 — USIE evidence and extraction

### Initial tasks
1. Audit USIE source tree, CLI commands, schema/migrations, capture/extraction models, tests, CI and current exports.
2. Record the exact default-branch commit and run available tests in a controlled checkout when possible.
3. Compare current implementation against README, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and `docs/P0_ACCEPTANCE.md`.
4. Document supported extraction fields and platform coverage from implementation/tests only.
5. Map the proposed contract to canonical USIE records; call out missing fields and unsupported export paths.
6. Propose producer fixtures/export only after contract review.

### Must not
- Claim platform-specific extraction based only on routing support.
- change the legacy `social_evidence` view into a writable canonical store;
- overwrite capture history or weaken evidence hashing/SSRF controls;
- add non-browser fetchers without a separate network-safety design;
- copy credentials, browser state or raw private evidence into OCIF/Git.

### Deliverables
- USIE baseline report with revision and exact test outcomes;
- schema/CLI/extraction capability matrix;
- contract mapping and gaps;
- sanitized fixtures for every supported outcome;
- producer-side contract tests and documented integration limitations.

## Agent 2 — OCIF knowledge and content workflow

### Initial tasks
1. Audit the OCIF repository baseline and current OPI/OIS interfaces.
2. Define the smallest useful knowledge model that preserves source/capture/artifact lineage.
3. Implement strict contract validation and idempotent consumer behavior only after the producer contract is agreed.
4. Build an evaluation set before optimizing retrieval or choosing vector infrastructure.
5. Separate observed fields, normalized facts, inferred claims and editorial content.
6. Define research brief, draft, review, approval, rejection and revision states.
7. Draft dashboard/API contracts after the underlying domain model stabilizes.

### Must not
- redefine USIE's canonical schema or invent an export endpoint;
- duplicate OPI project/task state or OIS execution/approval state;
- treat generated summaries as facts without evidence references;
- enable unattended external publishing in the initial release;
- build production UI against provisional database tables.

### Deliverables
- OCIF schema ADR and lineage model;
- consumer-side contract validation and fixtures;
- retrieval evaluation baseline;
- evidence-linked research/content workflow;
- stable API/UI contract proposal and tests.

## Shared integration protocol

1. Agent 1 proposes a versioned contract mapping from current USIE source.
2. Agent 2 writes consumer fixtures/tests against that proposed version.
3. Both review status semantics, artifact references, hash verification, idempotency and failure behavior.
4. Update the contract only with explicit versioning and a documented compatibility decision.
5. Run producer and consumer tests plus a real local integration test against disposable data.
6. Record exact revisions, commands, outcomes, limitations and gate decision.
7. Route task planning through OPI when its integration interface is verified; until then, use repository issues and link them back to this plan.
8. All external effects pass through verified OIS authorization and execution boundaries.

## First sprint exit

Do not start broad feature implementation until:
- baseline audit exists for all five repositories;
- applicable NUEGS controls and open governance questions are mapped;
- actual OPI/OIS/USIE interfaces have been verified;
- system boundaries and USIE-to-OCIF contract have joint review;
- owners and acceptance criteria are attached to initial work items.
