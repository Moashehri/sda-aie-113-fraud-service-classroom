"""Batch composition root for scoring the sample transaction file."""

from pathlib import Path

import pandas as pd

from fraud_service.adapters.sklearn_model import SklearnModel
from fraud_service.config import Settings, get_settings
from fraud_service.domain.entities import Transaction
from fraud_service.service.scorer import FraudScorer

DEFAULT_INPUT_PATH = Path("data/transactions_sample.csv")
DEFAULT_OUTPUT_PATH = Path("scored.csv")


def run_batch(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    model_path: str | Path | None = None,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    settings: Settings | None = None,
) -> pd.DataFrame:
    """Score every input row and write the batch result as CSV."""
    app_settings = settings or get_settings()
    transactions = pd.read_csv(input_path)
    scorer = FraudScorer(
        SklearnModel.load(model_path or app_settings.model_path),
        block_threshold=app_settings.block_threshold,
        review_band_width=app_settings.review_band_width,
    )

    results = []
    for row in transactions.to_dict(orient="records"):
        result = scorer.score(Transaction.from_mapping(row))
        results.append(
            {
                "transaction_id": result.transaction_id,
                "score": result.score,
                "decision": result.decision.value,
            }
        )

    scored = pd.DataFrame(results, columns=["transaction_id", "score", "decision"])
    scored.to_csv(output_path, index=False)
    return scored


def main() -> None:
    scored = run_batch()
    print(f"scored {len(scored):,} transactions")
    print(scored["decision"].value_counts().to_string())


if __name__ == "__main__":
    main()
