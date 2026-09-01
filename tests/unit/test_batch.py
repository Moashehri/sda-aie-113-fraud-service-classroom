"""Tests for the batch composition root."""

from pathlib import Path

import pandas as pd
import pytest

from fraud_service import batch
from fraud_service.config import Settings

pytestmark = pytest.mark.unit


def _write_input(path: Path) -> None:
    path.write_text(
        "transaction_id,amount_sar,channel,merchant_category,customer_id,timestamp\n"
        "TXN-BATCH-0001,125.50,pos,GROCERY,CUST-BATCH-1,"
        "2026-01-01T10:30:00+00:00\n",
        encoding="utf-8",
    )


def test_run_batch_scores_and_writes_csv(tmp_path: Path, settings: Settings) -> None:
    input_path = tmp_path / "transactions.csv"
    output_path = tmp_path / "scored.csv"
    _write_input(input_path)

    scored = batch.run_batch(
        input_path=input_path,
        model_path=settings.model_path,
        output_path=output_path,
        settings=settings,
    )

    assert list(scored.columns) == ["transaction_id", "score", "decision"]
    assert scored["transaction_id"].tolist() == ["TXN-BATCH-0001"]
    assert 0.0 <= float(scored.loc[0, "score"]) <= 1.0
    assert scored.loc[0, "decision"] in {"allow", "review", "block"}
    written = pd.read_csv(output_path)
    assert written["transaction_id"].tolist() == scored["transaction_id"].tolist()
    assert written["decision"].tolist() == scored["decision"].tolist()
    assert written["score"].tolist() == pytest.approx(scored["score"].tolist())


def test_run_batch_uses_default_settings_and_model_path(tmp_path: Path) -> None:
    input_path = tmp_path / "transactions.csv"
    output_path = tmp_path / "scored.csv"
    _write_input(input_path)

    scored = batch.run_batch(input_path=input_path, output_path=output_path)

    assert len(scored) == 1
    assert output_path.is_file()


def test_batch_main_reports_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        batch,
        "run_batch",
        lambda: pd.DataFrame(
            {
                "transaction_id": ["TXN-BATCH-0001"],
                "score": [0.1],
                "decision": ["allow"],
            }
        ),
    )

    batch.main()

    output = capsys.readouterr().out
    assert "scored 1 transactions" in output
    assert "allow" in output
