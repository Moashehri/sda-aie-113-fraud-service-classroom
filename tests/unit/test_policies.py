import pytest

from fraud_service.domain.entities import Decision
from fraud_service.domain.policies import decide

@pytest.mark.unit
@pytest.mark.parametrize("score, expected", [
    (0.05, Decision.ALLOW),   # well below review threshold
    (0.29, Decision.ALLOW),   # exactly below review threshold (0.72 - 0.42 = 0.30)
    (0.30, Decision.REVIEW),  # exactly at review threshold
    (0.71, Decision.REVIEW),  # below block threshold
    (0.72, Decision.BLOCK),   # exactly at block threshold
    (0.90, Decision.BLOCK),   # well above block threshold
])
def test_should_decide(score, expected):
    actual = decide(
        score=score, 
        block_threshold=0.72,
        review_band_width=0.42  # review band is 0.30 to 0.72
    )
    assert actual == expected