"""Business policies for converting scores into decisions."""

from enum import StrEnum

BLOCK_THRESHOLD = 0.85
REVIEW_BAND_WIDTH = 0.15


class Decision(StrEnum):
    """Action to take for a scored transaction."""

    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"


def decide(
    score: float,
    block_threshold: float = BLOCK_THRESHOLD,
    review_band_width: float = REVIEW_BAND_WIDTH,
) -> Decision:
    """Apply the allow/review/block decision bands to a probability."""
    if not 0.0 <= score <= 1.0:
        raise ValueError("score must be between 0 and 1")
    if not 0.0 <= block_threshold <= 1.0:
        raise ValueError("block_threshold must be between 0 and 1")
    if not 0.0 <= review_band_width <= block_threshold:
        raise ValueError("review_band_width must be between 0 and block_threshold")

    if score >= block_threshold:
        return Decision.BLOCK
    if score >= block_threshold - review_band_width:
        return Decision.REVIEW
    return Decision.ALLOW
