from __future__ import annotations

import os
from uuid import uuid4

import pytest

from ocif.postgres_store import PostgresOCIFStore
from ocif.workflow import (
    ApprovalStale,
    AuthorizationDenied,
    ContentWorkflow,
)


def seed_capture(dsn: str) -> str:
    source_id, capture_id = str(uuid4()), str(uuid4())
    store = PostgresOCIFStore(dsn)
    store.initialize()
    result = store.import_payload({
        "contract_version": "0.1.0",
        "source_id": source_id,
        "capture_id": capture_id,
        "submitted_url": "https://example.org/research",
        "normalized_url": "https://example.org/research",
        "capture_status": "partial",
        "captured_at": "2026-10-22T10:00:00+00:00",
        "completed_at": "2026-10-22T10:00:01+00:00",
        "artifacts": [],
        "extraction": None,
        "producer_revision": "workflow-test",
        "warnings": [],
    })
    assert result.status == "accepted"
    return capture_id


@pytest.mark.skipif(not os.getenv("OCIF_TEST_POSTGRES_DSN"), reason="PostgreSQL DSN not configured")
def test_content_workflow_requires_human_approval_and_ois_authorization() -> None:
    dsn = os.environ["OCIF_TEST_POSTGRES_DSN"]
    capture_ids = [seed_capture(dsn), seed_capture(dsn)]
    workflow = ContentWorkflow(dsn)
    workflow.initialize()
    objective = f"Measure topic response {uuid4()}"
    brief_id = workflow.create_research_brief(
        objective,
        capture_ids,
        "Evidence-backed brief: the selected topic is gaining discussion across captured sources.",
    )
    draft_id = workflow.create_draft(
        brief_id,
        "A concise, evidence-led draft for human review.",
        {"evidence": 0.9, "clarity": 0.8, "novelty": 0.7, "brand_fit": 0.9},
    )
    approval_id = workflow.approve_draft(draft_id, "human-reviewer-1")
    def denied(_request):
        return {"allowed": False, "reason": "policy denied"}

    with pytest.raises(AuthorizationDenied):
        workflow.execute_approved(
            approval_id, idempotency_key=str(uuid4()), authorize=denied
        )

    def authorized(request):
        return {
            **request,
            "allowed": True,
            "invocation_id": f"ois-{request['idempotency_key']}",
            "capability_version": "1.0.0",
        }
    key = str(uuid4())
    result = workflow.execute_approved(
        approval_id, idempotency_key=key, authorize=authorized
    )
    assert result["status"] == "succeeded"
    assert result["execution"]["external_side_effects"] is False
    assert result["execution"]["mode"] == "sandbox_noop"

    replay = workflow.execute_approved(
        approval_id, idempotency_key=key, authorize=authorized
    )
    assert replay["receipt_id"] == result["receipt_id"]
    assert replay["replayed"] is True

    first_event = workflow.record_outcome(
        result["receipt_id"], {"impressions": 120, "engagements": 9}, source="fixture-analytics"
    )
    second_event = workflow.record_outcome(
        result["receipt_id"], {"impressions": 250, "engagements": 21}, source="fixture-analytics"
    )
    assert second_event > first_event


@pytest.mark.skipif(not os.getenv("OCIF_TEST_POSTGRES_DSN"), reason="PostgreSQL DSN not configured")
def test_content_edit_invalidates_existing_approval() -> None:
    dsn = os.environ["OCIF_TEST_POSTGRES_DSN"]
    capture_id = seed_capture(dsn)
    workflow = ContentWorkflow(dsn)
    workflow.initialize()
    brief_id = workflow.create_research_brief(
        f"Approval invalidation {uuid4()}",
        [capture_id],
        "Brief tied to one capture.",
    )
    draft_id = workflow.create_draft(brief_id, "Version one", {"clarity": 0.8})
    approval_id = workflow.approve_draft(draft_id, "reviewer")
    workflow.revise_draft(draft_id, "Version two changes the approved content", {"clarity": 0.9})
    with pytest.raises(ApprovalStale):
        workflow.execute_approved(
            approval_id,
            idempotency_key=str(uuid4()),
            authorize=lambda _request: {"allowed": True, "invocation_id": "must-not-run"},
        )
