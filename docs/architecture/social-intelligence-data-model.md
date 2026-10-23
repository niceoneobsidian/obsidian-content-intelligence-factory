# Social intelligence data model

**Status:** Proposed canonical OCIF model; implement behind versioned migrations and repository contracts.  
**Scope:** Evidence-backed research, owned-account analytics, cross-platform normalization, retrieval, scoring and outcome measurement.

## Design rules

1. Preserve source-native facts and raw captures. Never replace source evidence with a normalized guess.
2. Normalize semantics, not just field names. Every metric has a definition, unit, denominator, observation window and availability state.
3. Keep observations immutable. Corrections and refreshed metrics create new observations linked to the prior record.
4. Separate public content metrics from private/owned-account analytics. Record the access class and authorization basis.
5. Missing, withheld, unavailable, zero and stale are different states.
6. All entities are tenant-scoped. Queries, retrieval, embeddings and exports must apply tenant boundaries before ranking.
7. A normalized record is useful only if it links to a USIE capture, source identity, artifact manifest and extraction run.

## Logical entities

| Entity | Purpose | Required identity / lineage |
|---|---|---|
| `source_accounts` | Platform, account and access profile | tenant_id, platform, platform_account_id, access_class |
| `source_objects` | Posts, videos, comments, threads and profiles | tenant_id, platform, native_object_id, object_type |
| `capture_events` | Immutable ingestion attempts and terminal states | capture_id, source_id, contract_version, captured_at |
| `artifacts` | Raw response, export, media metadata and extracted text | artifact_id, capture_id, sha256, size_bytes, media_type |
| `extraction_runs` | Parser/model version, status, warnings and field provenance | extraction_id, artifact_id, extractor_version, schema_version |
| `content_observations` | Normalized content plus source-native fields | observation_id, source_object_id, capture_id, observed_at |
| `metric_definitions` | Metric semantics and comparability rules | metric_key, definition_version, unit, denominator |
| `metric_observations` | Time-stamped metric values | object_id, metric_key, observed_at, window_start, window_end |
| `content_taxonomy` | Pillars, format, campaign, audience hypothesis and intent | taxonomy_version, label, parent_id |
| `content_labels` | Human- or model-assigned tags | observation_id, label_id, method, confidence, reviewer |
| `entities` / `entity_mentions` | Brands, products, people and named concepts | entity_id, mention evidence and extraction lineage |
| `topics` / `topic_memberships` | Topic clusters and model-versioned membership | topic_id, model_version, evidence_id |
| `research_briefs` | Questions, evidence IDs, claims and findings | brief_id, query_version, evidence set, created_at |
| `drafts` / `draft_scores` | Versioned drafts and explainable scoring | draft_id, version, digest, formula_version, component scores |
| `human_approvals` | Approval decision bound to exact draft bytes | approval_id, reviewer_id, draft_id, digest, version |
| `execution_receipts` | OIS invocation and execution boundary result | invocation_id, idempotency_key, approval_id, digest |
| `outcome_events` | Immutable measured results and experiment assignment | event_id, content_id, measurement window, metric source |

These are logical entities, not a mandate to create every table at once. Reuse existing OCIF and USIE tables where their semantics already match. Record schema and migration ownership before implementation.

## Canonical content record

Each normalized content record should contain:

- Identity: `tenant_id`, `platform`, `native_object_id`, `canonical_url`, `object_type`, `author/account reference`.
- Time: `created_at`, `observed_at`, `source_updated_at` when available, `timezone` or explicit UTC.
- Content: source-native text, normalized text, language, media descriptors, link references and parent/thread identifiers.
- Classification: taxonomy version, pillar, format, intent, campaign, audience hypothesis, human/model provenance and confidence.
- Lineage: `capture_id`, `artifact_id`, `extraction_id`, source URL, connector version and source access class.
- Integrity: payload digest, artifact hashes, schema version, retention class and deletion/tombstone state.

Keep raw source JSON in immutable artifacts. Do not force platform-specific fields into a lossy universal structure; preserve them under a namespaced `platform_fields` object.

## Metric normalization

Use a metric registry, not a single overloaded engagement field.

| Canonical metric | Meaning | Comparability rule |
|---|---|---|
| `views` | Platform-defined view count | Compare only where view definitions and content formats are compatible |
| `impressions` | Times content was displayed, if exposed | Do not substitute views |
| `reach` | Unique accounts reached, if exposed | Not interchangeable with impressions |
| `likes` | Native positive reaction count | Preserve native reaction type and API definition |
| `comments` | Comments/replies counted under a stated rule | Document whether replies are included |
| `shares` | Shares/reposts under source definition | Keep reposts distinct if source semantics differ |
| `saves` | Saves/bookmarks, if exposed | Often restricted to owned-account analytics |
| `clicks` | Click count for a defined destination/action | Require event and attribution definition |
| `watch_time_seconds` | Total watch time, where available | Store the source metric and unit |
| `followers_gained` | Growth over a defined interval | Prefer interval delta, not lifetime total |
| `conversions` | Attributed conversion events | Require attribution model and window |
| `spend_minor_units` | Paid media spend in minor currency units | Store ISO currency code and campaign context |

Every metric observation must include `metric_key`, `metric_definition_version`, `value`, `unit`, `observed_at`, `window_start`, `window_end`, `source_method`, `availability_status` and source lineage. Use decimal/numeric storage for rates and money; do not store currency as a floating-point value.

Do not calculate a universal engagement rate until its denominator is explicit. Support named formulas such as `engagements_per_reach`, `engagements_per_impression` and `engagements_per_view`; never silently mix them.

## Storage and retrieval

- PostgreSQL is the source of truth for relational records, lineage, approvals and outcome events.
- Keep original captures and media artifacts in a content-addressed filesystem/object store; persist SHA-256 and safe relative/object keys in PostgreSQL.
- Add pgvector only for use cases that beat a fixed keyword baseline. Keep relational filters and tenant authorization ahead of vector ranking.
- Use full-text search plus optional vector retrieval. Persist query version, candidate IDs, ranking model and evaluation results for reproducibility.
- Treat knowledge graphs as versioned relational entity/relation records initially. Add a graph database only when measured traversals justify its operational cost.
- For analytics, materialize daily/content-level aggregates from immutable metric observations. Keep raw facts and derived aggregates separate.

## Data quality and retention

Validate required identity fields, timezone-aware timestamps, metric units, schema versions, tenant ownership, artifact hashes, extraction provenance and source permissions. Quarantine malformed or conflicting payloads with an explicit reason and replay path. Preserve deletions as tombstones where the source contract requires them; apply source terms and retention rules to raw artifacts and derived data.

## Platform access references

- YouTube Analytics and Reporting APIs: https://developers.google.com/youtube/analytics
- YouTube Analytics metric definitions: https://developers.google.com/youtube/analytics/metrics
- TikTok Research Tools access and eligibility: https://developers.tiktok.com/products/research-api/
- TikTok API documentation: https://developers.tiktok.com/doc/tiktok-api-v2-introduction/
- LinkedIn Community Management API overview and access tiers: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-overview
- Meta developer documentation: https://developers.facebook.com/docs/
- X developer platform: https://developer.x.com/en
- Reddit developer documentation: https://www.reddit.com/dev/api/
- Bluesky developer documentation: https://docs.bsky.app/
- Mastodon API documentation: https://docs.joinmastodon.org/

Connector availability is not uniform. YouTube Analytics requires authorized access to the relevant channel/content owner. LinkedIn APIs require product access and permissions. TikTok Research Tools are restricted to qualifying approved research use and are not a general-purpose commercial analytics feed. Treat all connector capabilities as feature-gated and verify the current platform terms before implementation.
