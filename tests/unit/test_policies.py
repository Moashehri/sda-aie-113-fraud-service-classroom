"""Tests for decision-band business policy."""

import pytest

from fraud_service.domain.policies import Decision, decide

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, Decision.ALLOW),
        (0.699999, Decision.ALLOW),
        (0.70, Decision.REVIEW),
        (0.849999, Decision.REVIEW),
        (0.85, Decision.BLOCK),
        (1.0, Decision.BLOCK),
    ],
)
def test_decision_boundaries(score: float, expected: Decision) -> None:
    assert decide(score) is expected


@pytest.mark.parametrize("score", [-0.01, 1.01, float("nan")])
def test_invalid_scores_are_rejected(score: float) -> None:
    with pytest.raises(ValueError, match="score must be between"):
        decide(score)
