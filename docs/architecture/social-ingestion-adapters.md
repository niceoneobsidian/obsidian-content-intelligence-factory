# Social ingestion and content research adapters

**Status:** Architecture proposal for implementation through OCIF interfaces. External sources remain optional adapters; none is treated as a trusted evidence store by itself.

## Ownership boundaries

- **USIE** owns source capture attempts, terminal status, artifacts, extraction results, provenance, and verified artifact hashes. The existing read-only export adapter is the only accepted handoff to OCIF.
- **OCIF** owns normalized evidence envelopes, quarantine, durable ingestion, retrieval evaluation, evidence-linked research briefs, scored drafts, approval state, execution receipts, and append-only outcome metrics.
- **OIS** owns authorization, policy, idempotency for governed operations, execution records, and audit evidence. OCIF must not call a publishing adapter directly.
- **OPI** owns project tracking, acceptance criteria, blockers, release evidence, and cross-repository delivery status.
- **n8n** may orchestrate scheduled polling and external notifications, but cannot bypass USIE validation or OIS authorization.
- **FeedDeck** is a human-facing feed reader and discovery surface, not a canonical ingestion database.
- **Firecrawl MCP** is an optional web research/capture adapter. Its output must be recorded as a USIE capture with provenance and integrity checks before entering OCIF.

## Adapter matrix

| Source/tool | Role | Integration contract |
|---|---|---|
| Bluesky AT Protocol | Public post discovery and stream ingestion | Use com.atproto.sync.subscribeRepos or a supported relay; checkpoint cursors, reconnect safely, retain source URI/CID and event provenance. |
| Mastodon | Instance REST queries and permitted streams | Discover instance streaming URL from instance configuration; treat deletes as tombstones, and honor OAuth scopes and instance policy. |
| PRAW / Reddit API | Reddit submissions, comments and subreddit research | Use official Reddit API access and current platform terms; rate-limit, persist listing cursors, and store source IDs and timestamps. |
| RSS / YouTube feeds / GitHub activity | Low-friction feed discovery | Poll with conditional requests where supported; use canonical source URLs and stable external IDs. |
| Firecrawl MCP | Web search and structured page extraction | Use only for permitted public pages; record query, source URL, capture time, tool/version, artifact hash and extraction provenance. Do not use it to evade authentication or access controls. |
| FeedDeck | Cross-feed monitoring UI | Use for human discovery and topic triage; route selected URLs into USIE rather than importing its local UI state as evidence. |
| n8n | Scheduling and glue | Trigger bounded USIE jobs, move only versioned envelopes, and record workflow execution IDs. Credentials stay in its credential store; no tokens in payloads. |
| Mixpost | Potential publishing/scheduling adapter | Defer integration until the OIS publish capability, approval digest binding, network-specific consent, rollback and metrics contracts pass. Do not enable live publishing in the current workflow. |

## Canonical event envelope

Each source adapter emits a request to USIE; USIE then emits a terminal capture envelope containing:

- contract_version, source_id, capture_id, submitted and normalized URL
- capture status, status reason, error code, capture/completion timestamps
- artifact manifest: ID, safe relative location, SHA-256, byte size, media type
- extraction status, extractor/version, schema version, field-level artifact provenance
- producer revision and warnings

OCIF re-validates the envelope, re-hashes artifacts, rejects unsafe paths and inconsistent provenance, and writes the observation, quarantine decision and import event transactionally to PostgreSQL. Duplicate keys with identical payloads are no-ops; changed payloads under an existing key are quarantined.

## Knowledge graph and retrieval

Start with PostgreSQL relational provenance and pgvector only where embeddings improve a measured retrieval baseline. Represent entities and relations as versioned records rather than introducing a graph database before evidence of need:

- Evidence → Source → Capture → Artifact → Extraction
- Evidence → Topic / Entity / Claim / Trend
- ResearchBrief → evidence IDs and query version
- Draft → brief ID, scoring formula version, score breakdown, content digest
- Approval → reviewer, draft version and exact content digest
- ExecutionReceipt → OIS invocation, policy version and idempotency key
- OutcomeEvent → source, measurement window, metric values and timestamp

Measure retrieval with a fixed golden query set using recall@k, MRR and precision@k. Keep the baseline keyword retrieval until a vector or reranking candidate improves these metrics on the same dataset.

## Safety and release gates

1. Read-only capture first; no platform writes in the ingestion adapter.
2. Source terms, OAuth scopes, deletion semantics and retention limits are documented per connector.
3. Artifact path and SHA-256 verification happens at export and import boundaries.
4. Postgres restart/replay, duplicate payload, conflicting payload, quarantine and retrieval-golden tests run in CI.
5. Human approval is bound to a draft digest and version. Any edit invalidates prior approval.
6. OIS must authorize the exact approval ID, digest, version and idempotency key before execution.
7. Initial execution is sandbox/no-op only. Live publishing is a separate release requiring reviewed network adapters and explicit approval.
8. Outcomes are append-only and must record metric source and measurement window.

## Official source references

- AT Protocol streaming data: https://atproto.com/guides/streaming-data
- Mastodon streaming API: https://docs.joinmastodon.org/methods/streaming/
- PRAW documentation: https://praw.readthedocs.io/
- n8n documentation: https://docs.n8n.io/
- Official Firecrawl MCP server: https://github.com/firecrawl/firecrawl-mcp-server
- FeedDeck source: https://github.com/feeddeck/feeddeck
- Mixpost source: https://github.com/inovector/mixpost
