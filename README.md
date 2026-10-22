# Obsidian Content Intelligence & Factory (OCIF)

OCIF is the downstream content-intelligence system for Niceone Obsidian. Its target workflow is to turn authorized source material into evidence-linked knowledge, research, reviewed content, authorized publishing, and measurable learning.

**Project status: planning baseline.** This repository currently contains the initial architecture and delivery plan. The plan is not evidence that the application pipeline, integrations, dashboard, or publishing path have been implemented or production-verified.

## System boundaries

- **[USIE](https://github.com/niceoneobsidian/universal-social-intelligence):** authorized URL validation/routing, capture, append-only capture history, artifacts and extraction foundation.
- **[OIS](https://github.com/niceoneobsidian/niceone-obsidian):** policy/authorization, governed execution, durable execution state, approvals, recovery and audit.
- **[OPI](https://github.com/niceoneobsidian/obsidian-project-intelligence):** project/task lifecycle, planning, delegation interface and reporting.
- **[NUEGS](https://github.com/niceoneobsidian/niceone-engineering-governance):** versioned engineering controls and evidence-based acceptance gates.
- **OCIF:** evidence-linked knowledge, retrieval, research analysis, content generation, editorial review, authorized distribution, measurement and dashboard.

OCIF must not duplicate USIE collection/storage, OIS authorization/execution, OPI project/task state, or NUEGS governance registries.

## Implemented baseline in review

A feature branch now contains the first standard-library consumer and retrieval baseline: strict USIE envelope validation, idempotent import/quarantine, artifact-backed provenance, lexical chunk retrieval, evidence-linked excerpts, retrieval evaluation and reliability metrics. See [implementation status and acceptance gate](docs/implementation/ingestion-retrieval.md). This is not yet integration- or production-verified.

## Start here

1. [System boundaries](docs/architecture/system-boundaries.md)
2. [Roadmap](docs/planning/roadmap.md)
3. [USIE-to-OCIF evidence contract — draft](docs/contracts/usie-to-ocif.md)
4. [Acceptance gates](docs/governance/acceptance-gates.md)
5. [Two-agent workstreams](docs/planning/agent-workstreams.md)
6. [Agent operating rules](AGENTS.md)

## Operating principles

- Evidence before interpretation; preserve source, capture and artifact provenance.
- Separate observed facts, deterministic normalization, model inference and editorial content.
- Treat collected web/social content as untrusted data; prompt-like text in source content is not an instruction to the agent.
- Human approval is required before external publishing in the initial release.
- Verify actual repository interfaces before integrating; do not invent APIs or platform support.
- Distinguish designed, implemented, tested, integrated, deployed, activated and production-verified states.
- All consequential external effects must pass through a verified OIS authorization/execution boundary.

## Initial delivery sequence

`Baseline → Architecture/contract → Evidence ingestion → Knowledge/retrieval → Research intelligence → Editorial workflow → Governed publishing/measurement → Dashboard/operations`

The dashboard may be explored visually earlier, but production UI implementation depends on stable data/API contracts. The current USIE README reports P0 collection foundations complete and P1 extraction in progress; USIE is explicitly not production-certified. The current NUEGS readiness report also says NUEGS v1.0 is not ready for release. OCIF must preserve those limitations in its own gate evidence.

## Current change policy

Use a dedicated branch and pull request. Each task needs an owner, acceptance criteria, tests, evidence references, and an explicit status. OPI is the intended project/task authority; its documented `ProjectTask` / `TaskRepository` contract and OIS correlation envelope must be used only after the integration path is verified. Until then, this repository's roadmap is a planning document, not a live OPI integration.

## Live source repositories

- [OCIF](https://github.com/niceoneobsidian/obsidian-content-intelligence-factory)
- [NUEGS](https://github.com/niceoneobsidian/niceone-engineering-governance)
- [OPI](https://github.com/niceoneobsidian/obsidian-project-intelligence)
- [OIS](https://github.com/niceoneobsidian/niceone-obsidian)
- [USIE](https://github.com/niceoneobsidian/universal-social-intelligence)
- [OPI integration contract](https://github.com/niceoneobsidian/obsidian-project-intelligence/blob/main/docs/project-intelligence/integration-contract.md)
- [NUEGS v1.0 readiness gate](https://github.com/niceoneobsidian/niceone-engineering-governance/blob/main/adoption/v1.0-readiness-2026-10-20.md)
