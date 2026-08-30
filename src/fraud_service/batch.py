"""Batch composition root for scoring the sample transaction file."""

from pathlib import Path

import pandas as pd

from fraud_service.adapters.sklearn_model import SklearnModel
from fraud_service.domain.entities import Transaction
from fraud_service.service.scorer import FraudScorer

DEFAULT_INPUT_PATH = Path("data/transactions_sample.csv")
DEFAULT_MODEL_PATH = Path("models/fraud_xgb_v3.joblib")
DEFAULT_OUTPUT_PATH = Path("scored.csv")


def run_batch(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> pd.DataFrame:
    """Score every input row and write the batch result as CSV."""
    transactions = pd.read_csv(input_path)
    scorer = FraudScorer(SklearnModel.load(model_path))

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
