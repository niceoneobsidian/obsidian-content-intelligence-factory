from __future__ import annotations

import pytest

from ocif.scoring import (
    DEFAULT_DRAFT_WEIGHTS,
    ScoringError,
    score_draft,
    score_historical_performance,
)


def test_draft_score_is_deterministic_and_explains_coverage() -> None:
    values = {
        "objective_fit": 0.8,
        "evidence_strength": 1.0,
        "hook_clarity": 0.6,
        "platform_fit": 0.9,
        "distinctiveness": 0.7,
        "action_path": 0.8,
        "brand_safety": 1.0,
    }
    first = score_draft(values)
    second = score_draft(values)
    assert first == second
    assert first.score == 82.5
    assert first.coverage == 1.0
    assert first.eligible is True


def test_missing_components_are_visible_in_coverage() -> None:
    result = score_draft({"objective_fit": 1.0, "evidence_strength": None})
    assert result.score == 100.0
    assert result.coverage == DEFAULT_DRAFT_WEIGHTS["objective_fit"]
    assert result.components["evidence_strength"] is None


def test_hard_failure_blocks_eligibility_even_with_high_score() -> None:
    result = score_draft(
        {key: 1.0 for key in DEFAULT_DRAFT_WEIGHTS},
        hard_failures=("unsupported factual claim",),
    )
    assert result.score == 100.0
    assert result.eligible is False
    assert result.hard_failures == ("unsupported factual claim",)


def test_all_missing_components_are_not_eligible() -> None:
    result = score_draft({key: None for key in DEFAULT_DRAFT_WEIGHTS})
    assert result.score == 0.0
    assert result.coverage == 0.0
    assert result.eligible is False


@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), float("inf")])
def test_out_of_range_components_are_rejected(value: float) -> None:
    with pytest.raises(ScoringError):
        score_draft({"objective_fit": value})


def test_historical_score_requires_explicit_formula_id_and_weights() -> None:
    result = score_historical_performance(
        {"engagement": 0.8, "conversion": 0.5},
        formula_id="qualified-traffic-v1",
        weights={"engagement": 0.4, "conversion": 0.6},
    )
    assert result.score == 62.0
    assert result.formula_id == "qualified-traffic-v1"
