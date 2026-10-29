# NICEONE Social Content Pilot (interim)

A local-first, single-user pilot for the NICEONE AI Content Factory while OIS, USIE, OCIF, OPI, Agent Weave and NUEGS continue toward production readiness.

## Included

- Local web UI on your Mac; Python standard library only.
- SQLite draft history, platform selection, optional public HTTPS media URL and future scheduling.
- Optional local AI copy generation through Ollama.
- Human approval gate before publishing.
- Optional Zernio adapter for TikTok, Facebook, Instagram, X and LinkedIn.
- Publishing disabled by default; stored provider responses and idempotency key.

## Important boundary

This is a personal-use pilot, not production-ready. It is not a replacement for OIS, USIE, OCIF or other NICEONE systems. Direct Zernio publishing does not yet route through the verified OIS authorization/execution boundary. Use only as a temporary local tool with that limitation understood. Do not expose it publicly or use unattended autonomous publishing.

Platform approvals still apply. TikTok says unaudited clients can be restricted to private-only posts: https://developers.tiktok.com/docs/en/content-posting-api-get-started. Review Zernio docs at https://docs.zernio.com/ and pricing at https://zernio.com/pricing before enabling paid usage or connecting X.

## Run on macOS

Python 3.11+ is required. No pip installs are needed.

From the repository root:

    export OLLAMA_MODEL="qwen2.5-coder:1.5b"
    python3 apps/social-pilot/app.py

Open http://127.0.0.1:8765 and press Ctrl-C to stop. Drafts are stored in data/social_pilot.sqlite3 relative to the current directory, unless SOCIAL_PILOT_DB is set.

Ollama is optional. If installed and running, the Draft with Ollama button uses the local endpoint at http://127.0.0.1:11434/api/generate. Set OLLAMA_URL or OLLAMA_MODEL to override defaults. Manual drafting works without Ollama.

## Optional Zernio setup

1. Create an API key at https://zernio.com/dashboard/api-keys.
2. Connect the social accounts you want to test.
3. Obtain the real account IDs from Zernio's accounts endpoint/dashboard; never guess IDs.
4. Export configuration in your local shell. Never commit keys or paste them into chat.

    export ZERNIO_API_KEY="YOUR_KEY"
    export ZERNIO_ACCOUNT_IDS="instagram=YOUR_ACCOUNT_ID;facebook=YOUR_ACCOUNT_ID"

Allowed mapping names: tiktok, facebook, instagram, twitter (for X), linkedin. Only map accounts you actually connected.

Publishing remains disabled by default. After reviewing the costs, target accounts, copy and schedule, you may deliberately enable it in the same terminal session:

    export SOCIAL_PILOT_ENABLE_PUBLISH=true
    python3 apps/social-pilot/app.py

Keep the app on loopback. Start with one low-risk test. If a network timeout or partial failure occurs, check the Zernio dashboard before retrying.

## Media and scheduling

- Text-only posts are supported.
- A media URL must be public HTTPS and directly reachable by the provider. The pilot does not upload local files or create public URLs.
- Schedule time is converted to UTC ISO-8601 before being sent.
- One API request does not guarantee successful publication on every platform. Each network has its own permissions, account requirements, quotas and media constraints.

## Known gaps before production

No user authentication, secrets manager, remote deployment, background worker, automatic retry queue, webhook reconciliation, media upload/transcoding, per-platform copy overrides, analytics or OIS execution adapter. Before production, move consequential publishing behind verified OIS policy, approvals, idempotency and evidence; add automated integration tests, security review, secret scanning, observability and recovery.

The Zernio request follows its documented POST /v1/posts contract: content, platforms with account IDs, optional mediaItems, and either publishNow or scheduledFor. Reference: https://docs.zernio.com/posts/create-post.
