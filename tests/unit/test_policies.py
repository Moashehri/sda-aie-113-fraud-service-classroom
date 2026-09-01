import pytest

from fraud_service.domain.entities import Decision
from fraud_service.domain.policies import decide


@pytest.mark.unit
@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.05, Decision.ALLOW),  # well below review threshold
        (0.29, Decision.ALLOW),  # exactly below review threshold (0.72 - 0.42 = 0.30)
        (0.30, Decision.REVIEW),  # exactly at review threshold
        (0.71, Decision.REVIEW),  # below block threshold
        (0.72, Decision.BLOCK),  # exactly at block threshold
        (0.90, Decision.BLOCK),  # well above block threshold
    ],
)
def test_should_decide(score: float, expected: Decision) -> None:
    actual = decide(
        score=score,
        block_threshold=0.72,
        review_band_width=0.42,  # review band is 0.30 to 0.72
    )
    assert actual == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("score", "block_threshold", "review_band_width", "message"),
    [
        (1.1, 0.85, 0.15, "score"),
        (0.5, -0.1, 0.15, "block_threshold"),
        (0.5, 0.85, 0.90, "review_band_width"),
    ],
)
def test_invalid_decision_parameters_fail_before_scoring(
    score: float,
    block_threshold: float,
    review_band_width: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        decide(score, block_threshold, review_band_width)
