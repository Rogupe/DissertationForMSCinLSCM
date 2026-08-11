"""Train the GRU corrector and persist metrics and per-lane corrections.

Run from the repo root:  python -m src.models.train_gru
"""

import numpy as np
import pandas as pd

from src.data.build import PROCESSED
from src.models.gru_corrector import (
    baseline_maes,
    build_panel,
    build_sequences,
    train_model,
    train_val_split,
)

RESULTS = PROCESSED / "gru"


def run(seed=1, epochs=300, out_dir=RESULTS) -> dict:
    panel, lanes, days = build_panel()
    X, y, meta = build_sequences(panel, lanes, days)
    train, val = train_val_split(meta, days)
    model, preds, history = train_model(X, y, train, seed=seed, epochs=epochs)

    maes = baseline_maes(X, y, meta, train, val, lanes)
    maes["gru"] = float(np.abs(y[val] - preds[val]).mean())
    metrics = pd.DataFrame(
        [{"predictor": k, "val_mae_days": v} for k, v in maes.items()])

    rows = []
    for li, lane in enumerate(lanes):
        mask = meta[:, 0] == li
        bias = float(y[train & mask].mean()) if (train & mask).any() else np.nan
        last = int(np.where(mask)[0].max())
        rows.append({"lane_id": lane, "train_mean_dev": bias,
                     "gru_next_day_dev": float(preds[last])})
    corrections = pd.DataFrame(rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_parquet(out_dir / "metrics.parquet", index=False)
    corrections.to_parquet(out_dir / "corrections.parquet", index=False)
    return {"metrics": maes, "outputs": str(out_dir)}


if __name__ == "__main__":
    summary = run()
    for predictor, mae in summary["metrics"].items():
        print(f"{predictor:12s} val MAE: {mae:.4f} days")
    print("outputs:", summary["outputs"])