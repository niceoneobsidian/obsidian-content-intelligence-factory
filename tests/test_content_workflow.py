from __future__ import annotations

import os
from uuid import uuid4

import pytest

from ocif.workflow import (
    ApprovalStale,
    AuthorizationDenied,
    ContentWorkflow,
)


@pytest.mark.skipif(not os.getenv("OCIF_TEST_POSTGRES_DSN"), reason="PostgreSQL DSN not configured")
def test_content_workflow_requires_human_approval_and_ois_authorization() -> None:
    workflow = ContentWorkflow(os.environ["OCIF_TEST_POSTGRES_DSN"])
    workflow.initialize()
    objective = f"Measure topic response {uuid4()}"
    brief_id = workflow.create_research_brief(
        objective,
        ["evidence-usie-capture-1", "evidence-usie-capture-2"],
        "Evidence-backed brief: the selected topic is gaining discussion across captured sources.",
    )
    draft_id = workflow.create_draft(
        brief_id,
        "A concise, evidence-led draft for human review.",
        {"evidence": 0.9, "clarity": 0.8, "novelty": 0.7, "brand_fit": 0.9},
    )
    approval_id = workflow.approve_draft(draft_id, "human-reviewer-1")
    called = []

    def denied(_request):
        return {"allowed": False, "reason": "policy denied"}

    def executor(_request):
        called.append(True)
        return {"external_side_effects": False, "mode": "sandbox_noop"}

    with pytest.raises(AuthorizationDenied):
        workflow.execute_approved(
            approval_id, idempotency_key=str(uuid4()), authorize=denied, execute_noop=executor
        )
    assert called == []

    def authorized(request):
        return {
            "allowed": True,
            "invocation_id": f"ois-{request['idempotency_key']}",
            "policy_version": "test-policy-v1",
        }
    key = str(uuid4())
    result = workflow.execute_approved(
        approval_id, idempotency_key=key, authorize=authorized, execute_noop=executor
    )
    assert result["status"] == "succeeded"
    assert result["execution"]["external_side_effects"] is False
    assert len(called) == 1

    replay = workflow.execute_approved(
        approval_id, idempotency_key=key, authorize=authorized, execute_noop=executor
    )
    assert replay["receipt_id"] == result["receipt_id"]
    assert replay["replayed"] is True
    assert len(called) == 1

    first_event = workflow.record_outcome(
        result["receipt_id"], {"impressions": 120, "engagements": 9}, source="fixture-analytics"
    )
    second_event = workflow.record_outcome(
        result["receipt_id"], {"impressions": 250, "engagements": 21}, source="fixture-analytics"
    )
    assert second_event > first_event


@pytest.mark.skipif(not os.getenv("OCIF_TEST_POSTGRES_DSN"), reason="PostgreSQL DSN not configured")
def test_content_edit_invalidates_existing_approval() -> None:
    workflow = ContentWorkflow(os.environ["OCIF_TEST_POSTGRES_DSN"])
    workflow.initialize()
    brief_id = workflow.create_research_brief(
        f"Approval invalidation {uuid4()}",
        ["evidence-capture-1"],
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
