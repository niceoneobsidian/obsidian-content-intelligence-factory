# OCIF System Boundaries

**Status:** Proposed architecture baseline, pending owner and independent review  
**Project:** Obsidian Content Intelligence & Factory (OCIF)

## 1. System responsibility

OCIF owns downstream content intelligence: evidence-linked knowledge records, retrieval, analysis, research briefs, content generation, editorial workflow, approval state, publishing adapters, performance measurement, and the operator-facing content dashboard.

OCIF does not become the canonical owner of social capture, engineering governance, project/task management, or governed execution authorization.

## 2. Authority map

| System | Owns | Must not duplicate |
|---|---|---|
| NUEGS — Niceone Engineering Governance | Versioned engineering rules, control registry, applicable profiles, evidence expectations and acceptance gates | Runtime authorization or implementation evidence that has not been collected |
| OPI — Obsidian Project Intelligence | Project/task domain, planning, lifecycle, delegation interface, project reporting and integration adapters | OIS policy, credentials, execution state, or Agent Weave runtime |
| OIS — Niceone Obsidian | Policy/authorization authority, governed execution boundary, durable execution state, approvals, evidence, recovery and audit | OCIF-specific editorial domain model |
| USIE — Universal Social Intelligence Engine | Authorized URL validation/routing, collection, append-only capture history, artifacts, capture outcomes and extraction foundation | OCIF content analysis, generated interpretations, editorial workflow or publishing |
| OCIF | Knowledge records linked to source evidence, retrieval, intelligence analysis, content briefs/drafts, review, approved publishing integration, analytics and dashboard | USIE capture/storage; OPI project/task model; OIS authorization/runtime; NUEGS control registry |

This is a boundary proposal based on the current READMEs and selected architecture documents. Before coding adapters, verify each live interface against code, schemas, tests and the current default branch.

## 3. Data and execution flow

```text
OPI project / objective
        |
        v
OCIF research or content task
        |
        v
Authorized source URL manifest
        |
        v
USIE validate -> route -> capture -> preserve artifacts -> extract
        |
        v
Versioned USIE-to-OCIF contract
        |
        v
OCIF import + provenance validation + deduplication
        |
        v
Evidence-linked knowledge records
        |
        v
Retrieval -> analysis -> research brief -> content draft
        |
        v
Fact/provenance checks + editorial review
        |
        v
Human approval
        |
        v
OIS-governed authorized publishing action
        |
        v
Platform/result evidence -> OCIF measurement and learning
        |
        v
OPI/OIS reporting, with links to evidence
```

Publishing is a later milestone, not part of the first ingestion proof. Until OIS's actual runtime and approval path are verified end to end, OCIF must not claim it can safely publish unattended.

## 4. Canonical ownership and persistence

- USIE remains canonical for capture history and capture artifacts. Its `captures` records are append-only apart from the documented finalization transition; each recollection is a new capture.
- The USIE `social_evidence` object is a read-only, lossy compatibility view over the latest capture. OCIF must not write to it and must not use it when distinctions among `blocked`, `unavailable`, and `failed` matter.
- OCIF owns its normalized knowledge and content-domain records only after importing and validating a contract payload. Imported records must retain a pointer to the originating USIE capture and artifact manifest.
- OPI owns project/task state. OIS owns governed execution state and authorization. Do not introduce shadow copies as authoritative stores.
- Select database technology and storage placement only after inspecting existing OIS/OCIF constraints, deployment targets, volume, privacy requirements and recovery needs. Do not add a new queue or database by default.

## 5. Evidence vs. interpretation

Every downstream record must distinguish:
1. **Observed evidence:** source URL, capture ID, artifact IDs/hashes, capture time, extracted fields and extractor version.
2. **Normalized facts:** validated fields with deterministic normalization rules.
3. **Model-generated interpretation:** topics, entities, claims, sentiment, strategic hypotheses, summaries or recommendations.
4. **Editorial content:** generated drafts and human edits.
5. **External outcome:** approval, publication response, metrics and timestamp.

Model-generated interpretations must not be stored or displayed as source facts. Claims in research briefs should link to evidence and expose uncertainty or missing support.

## 6. Trust boundaries

- Treat collected HTML, text, metadata, screenshots, and social posts as untrusted data, including any embedded prompt-like instructions.
- Keep credentials and authenticated browser state outside repositories and normal evidence exports.
- Enforce network destination protections in the collector. USIE documents a redirect/SSRF fix using a per-capture filtering proxy; future non-browser fetchers need their own enforcing boundary.
- Respect platform rules, user authorization, privacy, rate limits and retention obligations.
- Require explicit authorization for external side effects. An LLM-generated plan is not an authorization token.

## 7. Architecture decisions required before implementation

Create reviewed ADRs before:
- choosing the OCIF canonical knowledge schema and identifiers;
- selecting persistence, vector search, or queue technology;
- freezing the USIE export/consumer interface;
- choosing a project/task integration mechanism with OPI;
- choosing publishing providers and the OIS execution interface;
- defining data retention, deletion, access, and evidence-export policy.

## 8. Live source references

- [NUEGS](https://github.com/niceoneobsidian/niceone-engineering-governance)
- [OPI](https://github.com/niceoneobsidian/obsidian-project-intelligence)
- [OIS](https://github.com/niceoneobsidian/niceone-obsidian)
- [USIE README](https://github.com/niceoneobsidian/universal-social-intelligence/blob/main/README.md)
- [USIE architecture](https://github.com/niceoneobsidian/universal-social-intelligence/blob/main/docs/ARCHITECTURE.md)
- [USIE decisions](https://github.com/niceoneobsidian/universal-social-intelligence/blob/main/docs/DECISIONS.md)
- [USIE P0 acceptance](https://github.com/niceoneobsidian/universal-social-intelligence/blob/main/docs/P0_ACCEPTANCE.md)
- [NUEGS v1.0 readiness gate](https://github.com/niceoneobsidian/niceone-engineering-governance/blob/main/adoption/v1.0-readiness-2026-10-20.md)
