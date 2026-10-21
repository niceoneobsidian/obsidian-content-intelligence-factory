# OCIF Roadmap

**Status:** Initial plan; estimates intentionally omitted until baseline and owners are confirmed.

## North-star outcome

Turn authorized social sources and other approved research inputs into evidence-linked knowledge, useful intelligence, reviewed content, authorized distribution and measurable feedback—without confusing observed evidence with model interpretation or bypassing OIS governance.

## Milestones

### M0 — Baseline and project setup
- Inventory OCIF, USIE, OIS, OPI and NUEGS source trees, default branches, CI, tests and current interfaces.
- Record exact revisions and test outcomes; do not treat remote README review as a local test.
- Map applicable NUEGS controls and unresolved governance decisions.
- Establish OPI-tracked epics/tasks, owners, dependencies and evidence fields.
- **Exit:** reviewed baseline report and initial architecture decisions backlog.

### M1 — Architecture and interface agreement
- Confirm authority boundaries and the OCIF domain.
- Audit USIE CLI, schema, migrations, extraction models and current export surfaces.
- Audit OIS authorization/execution contracts and OPI task/project integration contracts.
- Approve the USIE-to-OCIF contract and knowledge model ADR.
- **Exit:** producer/consumer contract reviewed; no guessed APIs or duplicated authorities.

### M2 — Evidence ingestion vertical slice
- Generate sanitized USIE fixtures from canonical capture/extraction records.
- Implement OCIF contract validation, provenance checks, idempotent import and quarantine.
- Preserve exact outcomes, capture history, artifact references and hashes.
- Test success, partial, blocked, unavailable, failed and supported cancellation/interruption cases.
- **Exit:** reproducible contract tests and disposable-data integration run.

### M3 — Knowledge and retrieval
- Build evidence-linked source/observation records and versioned derived-claim records.
- Add deterministic normalization and source/entity linking only where supported.
- Establish retrieval evaluation data and scoring before selecting more complex search infrastructure.
- **Exit:** measurable retrieval baseline, traceable claims and explicit unsupported/uncertain states.

### M4 — Research intelligence
- Generate topic maps, entity summaries, trend hypotheses and research briefs from retrieved evidence.
- Require claim-to-evidence links and separate observation from inference.
- Evaluate completeness, relevance, freshness and unsupported-claim rate.
- **Exit:** reviewed research brief workflow with repeatable quality evaluation.

### M5 — Content production and editorial workflow
- Convert approved briefs into platform-specific draft variants.
- Track draft versions, evidence lineage, prompt/model/rule versions, reviewer decisions and revision history.
- Add fact-checking, policy checks, originality checks and human editorial approval.
- **Exit:** end-to-end draft/review/reject/approve flow with audit evidence.

### M6 — Governed publishing and measurement
- Select one publishing provider only after provider/API, terms, auth and OIS boundary review.
- Integrate through OIS's verified authorization and execution interface; do not add a direct bypass.
- Begin with explicit human approval and a test account or sandbox where available.
- Record publication response, URL/ID, timestamp and subsequent metrics as external evidence.
- **Exit:** positive and negative authorization tests, idempotency/reconciliation and measurement fixtures pass.

### M7 — Dashboard and operations
- Design UI/UX from stable API contracts and real user workflows.
- Show source provenance, capture status, evidence gaps, research claims, content review state and performance measures.
- Add access controls, observability, retention/deletion, backup/restore, rollback and operational runbooks.
- **Exit:** independent acceptance against G0–G6; release scope and limitations documented.

## Critical path

`M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7`

Dashboard visual exploration may happen earlier, but production UI implementation depends on stable contracts. Publishing must not be used to prove ingestion or intelligence quality; each stage has its own acceptance criteria.

## Workstream allocation

- **Agent 1 — Source/evidence pipeline:** USIE audit, extraction coverage, canonical schema mapping, producer fixtures/export, evidence safety and producer-side tests.
- **Agent 2 — Knowledge/content product:** OCIF knowledge model, import consumer, retrieval evaluation, research intelligence, editorial flow and dashboard/API contracts.
- **Joint ownership:** system boundaries, contract approval, cross-system identity, integration tests, OPI task setup and release review.
- **Governance/reviewer:** NUEGS control mapping, risk acceptance, independent review and gate decisions.

## Planning system

Use OPI as the project/task authority once its current application interface and deployment path are verified. Until then, this repository's roadmap and GitHub issues are a transparent planning record, not proof of a live OPI integration. Each work item should include owner, dependencies, acceptance criteria, risk, evidence state, relevant commit/PR, and gate.

## Initial work item IDs

- `OCIF-001` Baseline audit and governance mapping
- `OCIF-002` Architecture boundary review and ADR backlog
- `OCIF-003` USIE source/schema/CLI/export audit
- `OCIF-004` OIS execution and approval interface audit
- `OCIF-005` OPI task/project integration audit
- `OCIF-006` USIE-to-OCIF contract review
- `OCIF-007` Evidence ingestion and contract fixtures
- `OCIF-008` Knowledge schema and provenance validation
- `OCIF-009` Retrieval evaluation set and baseline
- `OCIF-010` Research brief workflow
- `OCIF-011` Editorial workflow and approval states
- `OCIF-012` Single authorized publishing/measurement path
- `OCIF-013` Dashboard/API contracts and UI
- `OCIF-014` Production readiness and independent acceptance
