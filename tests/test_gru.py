"""Verification of the GRU corrector dataset, baselines and training."""

import numpy as np
import pytest

from src.models.train_gru import run

from src.data.loaders import DATA_DIR
from src.models.gru_corrector import (
    baseline_maes,
    build_panel,
    build_sequences,
    train_model,
    train_val_split,
)

pytestmark = pytest.mark.skipif(
    not DATA_DIR.exists(),
    reason="raw data files are not distributed with the repository",
)


@pytest.fixture(scope="module")
def dataset():
    panel, lanes, days = build_panel()
    X, y, meta = build_sequences(panel, lanes, days)
    train, val = train_val_split(meta, days)
    return panel, lanes, days, X, y, meta, train, val


def test_dataset_shapes(dataset):
    panel, lanes, days, X, y, meta, train, val = dataset
    assert len(lanes) == 9
    assert X.shape == (276, 7, 5)
    assert (int(train.sum()), int(val.sum())) == (177, 99)


def test_baselines(dataset):
    _, lanes, _, X, y, meta, train, val = dataset
    maes = baseline_maes(X, y, meta, train, val, lanes)
    assert maes["global_mean"] == pytest.approx(0.3776, abs=1e-3)
    assert maes["lane_mean"] == pytest.approx(0.1126, abs=1e-3)
    assert maes["persistence"] == pytest.approx(0.0488, abs=1e-3)
def test_training_learns(dataset):
    _, lanes, _, X, y, meta, train, val = dataset
    model, preds, history = train_model(X, y, train, epochs=150)
    assert history[-1] < history[0] * 0.5          # loss actually falls
    gru_mae = float(np.abs(y[val] - preds[val]).mean())
    maes = baseline_maes(X, y, meta, train, val, lanes)
    # The GRU must at minimum dominate the global mean; whether it
    # beats lane-mean/persistence on one month is the research finding.
    assert gru_mae < maes["global_mean"]
    print(f"\nGRU val MAE: {gru_mae:.4f} vs {maes}")
def test_gru_runner_writes_outputs(tmp_path):
    summary = run(epochs=50, out_dir=tmp_path)
    assert (tmp_path / "metrics.parquet").exists()
    assert (tmp_path / "corrections.parquet").exists()
    assert summary["metrics"]["gru"] < summary["metrics"]["global_mean"]