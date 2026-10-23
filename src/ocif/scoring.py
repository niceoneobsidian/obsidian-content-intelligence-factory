"""Deterministic, versioned content scoring primitives.

Scores are decision aids, not predictions of virality. Platform metric collection and
cohort normalization belong upstream; this module only scores normalized components.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


class ScoringError(ValueError):
    """A scoring formula or input is invalid."""


@dataclass(frozen=True)
class ScoreResult:
    formula_id: str
    score: float
    coverage: float
    components: Mapping[str, float | None]
    hard_failures: tuple[str, ...]
    eligible: bool


DEFAULT_DRAFT_WEIGHTS: Mapping[str, float] = {
    "objective_fit": 0.20,
    "evidence_strength": 0.20,
    "hook_clarity": 0.15,
    "platform_fit": 0.15,
    "distinctiveness": 0.10,
    "action_path": 0.10,
    "brand_safety": 0.10,
}


def _validate_weights(weights: Mapping[str, float]) -> None:
    if not weights:
        raise ScoringError("at least one weighted component is required")
    if any(not key for key in weights):
        raise ScoringError("component names must be non-empty")
    if any(not isfinite(weight) or weight < 0 for weight in weights.values()):
        raise ScoringError("weights must be finite and non-negative")
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ScoringError("weights must sum to 1.0")


def score_components(
    components: Mapping[str, float | None],
    *,
    weights: Mapping[str, float],
    formula_id: str,
    hard_failures: tuple[str, ...] = (),
) -> ScoreResult:
    """Score normalized [0,1] components with explicit coverage and hard gates.

    Missing components contribute neither points nor coverage. The remaining
    weights are renormalized for the displayed score, while coverage discloses
    how much of the formula was actually measured. A hard failure blocks eligibility.
    """
    _validate_weights(weights)
    if not formula_id.strip():
        raise ScoringError("formula_id is required")
    unknown = set(components) - set(weights)
    if unknown:
        raise ScoringError(f"unknown score components: {', '.join(sorted(unknown))}")

    normalized: dict[str, float | None] = {}
    available_weight = 0.0
    weighted_total = 0.0
    for name, weight in weights.items():
        value = components.get(name)
        if value is None:
            normalized[name] = None
            continue
        if not isfinite(value) or not 0.0 <= value <= 1.0:
            raise ScoringError(f"{name} must be a finite value between 0 and 1")
        normalized[name] = float(value)
        available_weight += weight
        weighted_total += weight * value

    coverage = available_weight
    score = 100.0 * weighted_total / available_weight if available_weight else 0.0
    failures = tuple(dict.fromkeys(item.strip() for item in hard_failures if item.strip()))
    return ScoreResult(
        formula_id=formula_id,
        score=round(score, 4),
        coverage=round(coverage, 4),
        components=normalized,
        hard_failures=failures,
        eligible=coverage > 0.0 and not failures,
    )


def score_draft(
    components: Mapping[str, float | None],
    *,
    formula_id: str = "draft-quality-v1",
    hard_failures: tuple[str, ...] = (),
    weights: Mapping[str, float] = DEFAULT_DRAFT_WEIGHTS,
) -> ScoreResult:
    """Score draft quality using a caller-pinned formula version."""
    return score_components(
        components, weights=weights, formula_id=formula_id, hard_failures=hard_failures
    )


def score_historical_performance(
    components: Mapping[str, float | None],
    *,
    formula_id: str,
    weights: Mapping[str, float],
) -> ScoreResult:
    """Score cohort-normalized historical performance for a defined objective."""
    return score_components(components, weights=weights, formula_id=formula_id)
