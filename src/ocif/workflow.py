"""Evidence-linked content workflow with approval-bound execution.

The OCIF workflow owns content state. Execution is fail-closed: an OIS authorization
adapter must approve the exact draft digest and approval ID before an executor runs.
The default executor is a no-op receipt; this module never publishes to social networks.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from uuid import uuid4


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class WorkflowError(RuntimeError):
    """The requested workflow transition is invalid or not authorized."""


class ApprovalStale(WorkflowError):
    """The draft changed after the approval was issued."""


class AuthorizationDenied(WorkflowError):
    """OIS did not authorize execution."""


class ContentWorkflow:
    """PostgreSQL-backed evidence-to-outcome workflow.

    The authorization callback is the OIS boundary. It must return a mapping with
    allowed=true and an OIS invocation identifier. If it denies or raises, the
    executor is not called. The default executor creates a sandbox/no-op receipt.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS ocif_research_briefs (
      brief_id TEXT PRIMARY KEY, objective TEXT NOT NULL, evidence_ids JSONB NOT NULL,
      body TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS ocif_content_drafts (
      draft_id TEXT PRIMARY KEY, brief_id TEXT NOT NULL REFERENCES ocif_research_briefs(brief_id),
      content TEXT NOT NULL, content_sha256 TEXT NOT NULL, score DOUBLE PRECISION NOT NULL,
      score_formula_version TEXT NOT NULL, score_breakdown JSONB NOT NULL,
      version INTEGER NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS ocif_human_approvals (
      approval_id TEXT PRIMARY KEY, draft_id TEXT NOT NULL REFERENCES ocif_content_drafts(draft_id),
      content_sha256 TEXT NOT NULL, draft_version INTEGER NOT NULL, reviewer_id TEXT NOT NULL,
      decision TEXT NOT NULL CHECK (decision IN ('approved','rejected')),
      approved_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS ocif_execution_receipts (
      receipt_id TEXT PRIMARY KEY,
      approval_id TEXT NOT NULL REFERENCES ocif_human_approvals(approval_id),
      draft_id TEXT NOT NULL REFERENCES ocif_content_drafts(draft_id), content_sha256 TEXT NOT NULL,
      idempotency_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL,
      authorization_json JSONB NOT NULL, execution_json JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS ocif_outcome_events (
      event_id BIGSERIAL PRIMARY KEY,
      receipt_id TEXT NOT NULL REFERENCES ocif_execution_receipts(receipt_id),
      metrics_json JSONB NOT NULL, source TEXT NOT NULL,
      recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_ocif_briefs_created ON ocif_research_briefs(created_at);
    CREATE INDEX IF NOT EXISTS idx_ocif_drafts_brief ON ocif_content_drafts(brief_id);
    CREATE INDEX IF NOT EXISTS idx_ocif_outcomes_receipt
      ON ocif_outcome_events(receipt_id, recorded_at);
    CREATE OR REPLACE FUNCTION ocif_reject_workflow_history_mutation()
    RETURNS trigger LANGUAGE plpgsql AS $
    BEGIN
      RAISE EXCEPTION 'OCIF execution receipts and outcome events are append-only';
    END;
    $;
    DROP TRIGGER IF EXISTS trg_ocif_receipt_immutable ON ocif_execution_receipts;
    CREATE TRIGGER trg_ocif_receipt_immutable
      BEFORE UPDATE OR DELETE ON ocif_execution_receipts
      FOR EACH ROW EXECUTE FUNCTION ocif_reject_workflow_history_mutation();
    DROP TRIGGER IF EXISTS trg_ocif_outcome_immutable ON ocif_outcome_events;
    CREATE TRIGGER trg_ocif_outcome_immutable
      BEFORE UPDATE OR DELETE ON ocif_outcome_events
      FOR EACH ROW EXECUTE FUNCTION ocif_reject_workflow_history_mutation();
    """

    def __init__(self, dsn: str) -> None:
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN is required")
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - installation guard
            raise RuntimeError("install ocif[postgres] to use ContentWorkflow") from exc
        self._connect = lambda: psycopg.connect(dsn)

    def initialize(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(self.SCHEMA)

    def create_research_brief(self, objective: str, evidence_ids: Sequence[str], body: str) -> str:
        if not objective.strip() or not body.strip() or not evidence_ids:
            raise ValueError("objective, brief body and at least one evidence ID are required")
        if any(not isinstance(item, str) or not item.strip() for item in evidence_ids):
            raise ValueError("evidence IDs must be non-empty strings")
        brief_id = str(uuid4())
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(DISTINCT capture_id) FROM ocif_observations "
                "WHERE capture_id = ANY(%s)",
                (list(dict.fromkeys(evidence_ids)),),
            )
            row = cur.fetchone()
            if row is None or int(row[0]) != len(set(evidence_ids)):
                raise WorkflowError("every evidence ID must reference an imported OCIF capture")
            cur.execute(
                "INSERT INTO ocif_research_briefs(brief_id,objective,evidence_ids,body) "
                "VALUES (%s,%s,%s::jsonb,%s)",
                (brief_id, objective.strip(), _json(list(dict.fromkeys(evidence_ids))),
                 body.strip()),
            )
        return brief_id

    @staticmethod
    def score_draft(
        dimensions: Mapping[str, float], *, formula_version: str = "content-score-v1"
    ) -> tuple[float, dict[str, float]]:
        """Score normalized dimensions with a stable, versioned equal-weight formula."""
        if formula_version != "content-score-v1":
            raise ValueError(f"unsupported scoring formula: {formula_version}")
        if not dimensions:
            raise ValueError("at least one scoring dimension is required")
        normalized: dict[str, float] = {}
        for key, value in dimensions.items():
            if not key.strip() or isinstance(value, bool) or not 0 <= value <= 1:
                raise ValueError("score dimensions must be named numeric values in [0, 1]")
            normalized[key] = round(float(value), 4)
        breakdown = {key: round(value * 100, 2) for key, value in sorted(normalized.items())}
        return round(sum(normalized.values()) / len(normalized) * 100, 2), breakdown

    def create_draft(
        self, brief_id: str, content: str, dimensions: Mapping[str, float],
        *, formula_version: str = "content-score-v1",
    ) -> str:
        if not content.strip():
            raise ValueError("draft content is required")
        score, breakdown = self.score_draft(dimensions, formula_version=formula_version)
        draft_id = str(uuid4())
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM ocif_research_briefs WHERE brief_id=%s", (brief_id,))
            if cur.fetchone() is None:
                raise WorkflowError("research brief does not exist")
            cur.execute(
                "INSERT INTO ocif_content_drafts(draft_id,brief_id,content,content_sha256,score,"
                "score_formula_version,score_breakdown,version) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,1)",
                (draft_id, brief_id, content, _digest(content), score, formula_version,
                 _json(breakdown)),
            )
        return draft_id

    def revise_draft(
        self, draft_id: str, content: str, dimensions: Mapping[str, float],
        *, formula_version: str = "content-score-v1",
    ) -> int:
        if not content.strip():
            raise ValueError("draft content is required")
        score, breakdown = self.score_draft(dimensions, formula_version=formula_version)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT version FROM ocif_content_drafts WHERE draft_id=%s FOR UPDATE",
                (draft_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise WorkflowError("draft does not exist")
            version = int(row[0]) + 1
            cur.execute(
                "UPDATE ocif_content_drafts SET content=%s,content_sha256=%s,score=%s,"
                "score_formula_version=%s,score_breakdown=%s::jsonb,version=%s,updated_at=now() "
                "WHERE draft_id=%s",
                (content, _digest(content), score, formula_version, _json(breakdown),
                 version, draft_id),
            )
        return version

    def approve_draft(self, draft_id: str, reviewer_id: str, *, decision: str = "approved") -> str:
        if not reviewer_id.strip() or decision not in {"approved", "rejected"}:
            raise ValueError("reviewer ID and valid decision are required")
        approval_id = str(uuid4())
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT content_sha256,version FROM ocif_content_drafts "
                "WHERE draft_id=%s FOR UPDATE",
                (draft_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise WorkflowError("draft does not exist")
            cur.execute(
                "INSERT INTO ocif_human_approvals(approval_id,draft_id,content_sha256,"
                "draft_version,"
                "reviewer_id,decision) VALUES (%s,%s,%s,%s,%s,%s)",
                (approval_id, draft_id, str(row[0]), int(row[1]), reviewer_id.strip(), decision),
            )
        return approval_id

    def execute_approved(
        self, approval_id: str, *, idempotency_key: str,
        authorize: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        execute_noop: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Require current human approval and OIS authorization before executor invocation."""
        if not idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT a.approval_id,a.draft_id,a.content_sha256,a.draft_version,a.reviewer_id,
                          a.decision,d.content,d.content_sha256,d.version
                   FROM ocif_human_approvals a JOIN ocif_content_drafts d ON d.draft_id=a.draft_id
                   WHERE a.approval_id=%s FOR UPDATE OF a,d""",
                (approval_id,),
            )
            row = cur.fetchone()
            if row is None or row[5] != "approved":
                raise AuthorizationDenied("no approved human decision found")
            if (
                str(row[2]) != str(row[7])
                or int(row[3]) != int(row[8])
                or _digest(str(row[6])) != str(row[7])
            ):
                raise ApprovalStale("draft content changed after approval; approval is invalid")
            request = {
                "action": "ocif.content.execute", "approval_id": str(row[0]),
                "draft_id": str(row[1]), "content_sha256": str(row[2]),
                "draft_version": int(row[3]), "reviewer_id": str(row[4]),
                "idempotency_key": idempotency_key, "mode": "sandbox_noop",
            }
            cur.execute(
                "SELECT receipt_id,status,execution_json,approval_id,draft_id,content_sha256 "
                "FROM ocif_execution_receipts WHERE idempotency_key=%s",
                (idempotency_key,),
            )
            existing = cur.fetchone()
            if existing is not None:
                if existing[1] != "succeeded":
                    raise WorkflowError(
                        "previous execution with this idempotency key did not succeed"
                    )
                if (
                    str(existing[3]) != approval_id
                    or str(existing[4]) != str(row[1])
                    or str(existing[5]) != str(row[2])
                ):
                    raise WorkflowError(
                        "idempotency key was already used for a different approved draft"
                    )
                return {"receipt_id": str(existing[0]), "status": str(existing[1]),
                        "execution": existing[2], "replayed": True}
            authorization = authorize(request)
            if not isinstance(authorization, Mapping) or authorization.get("allowed") is not True:
                raise AuthorizationDenied("OIS authorization denied the execution request")
            if not authorization.get("invocation_id"):
                raise AuthorizationDenied("OIS authorization response lacks invocation_id")
            executor = execute_noop or (
                lambda req: {"mode": req["mode"], "external_side_effects": False}
            )
            execution = executor(request)
            receipt_id = str(uuid4())
            cur.execute(
                "INSERT INTO ocif_execution_receipts(receipt_id,approval_id,draft_id,"
                "content_sha256,"
                "idempotency_key,status,authorization_json,execution_json) "
                "VALUES (%s,%s,%s,%s,%s,'succeeded',%s::jsonb,%s::jsonb)",
                (receipt_id, approval_id, str(row[1]), str(row[2]), idempotency_key,
                 _json(dict(authorization)), _json(dict(execution))),
            )
            return {"receipt_id": receipt_id, "status": "succeeded",
                    "execution": dict(execution), "replayed": False}

    def record_outcome(self, receipt_id: str, metrics: Mapping[str, Any], *, source: str) -> int:
        if not source.strip() or not metrics:
            raise ValueError("outcome source and non-empty metrics are required")
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM ocif_execution_receipts WHERE receipt_id=%s", (receipt_id,))
            if cur.fetchone() is None:
                raise WorkflowError("execution receipt does not exist")
            cur.execute(
                "INSERT INTO ocif_outcome_events(receipt_id,metrics_json,source) "
                "VALUES (%s,%s::jsonb,%s) RETURNING event_id",
                (receipt_id, _json(dict(metrics)), source.strip()),
            )
            return int(cur.fetchone()[0])
