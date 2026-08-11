"""Make corrector: process cycle-time promises, corrected.

Synthetic scenario (seed 42, from the prior-phase design): a theorised
PCB plant in Queretaro runs a 12-step process route with a nominal
cycle time per product family. Actual daily overruns carry family bias,
a weekday effect and an AR(1) machine-congestion state centred on the
bottleneck step. The corrector learns tomorrow's overrun per family
from the recent history, using the same GRU architecture as every
other SCOR corrector.

Run:  python -m src.models.make_corrector
"""

import numpy as np
import pandas as pd

from src.data.build import PROCESSED
from src.models.gru_corrector import baseline_maes, train_model

SEED = 42
N_DAYS = 730
WINDOW = 7
NOMINAL_MINUTES = 90.0

FAMILIES = ["FAM-A", "FAM-B", "FAM-C"]
FAMILY_BIAS_MIN = {"FAM-A": 4.0, "FAM-B": 0.0, "FAM-C": 8.0}
FAMILY_SIGMA = {"FAM-A": 2.0, "FAM-B": 1.2, "FAM-C": 3.5}


def simulate_overruns(seed=SEED) -> pd.DataFrame:
    """Daily mean cycle-time overrun (minutes) per product family."""
    rng = np.random.default_rng(seed)
    congestion = 0.0
    rows = []
    for day in range(N_DAYS):
        congestion = 0.85 * congestion + rng.normal(0.0, 1.4)
        weekday = day % 7
        weekday_load = 2.5 if weekday in (0, 4) else 0.0
        for family in FAMILIES:
            overrun = (FAMILY_BIAS_MIN[family] + congestion + weekday_load
                       + rng.normal(0.0, FAMILY_SIGMA[family]))
            rows.append({"day": day, "weekday": weekday, "family": family,
                         "nominal_minutes": NOMINAL_MINUTES,
                         "overrun_minutes": overrun})
    return pd.DataFrame(rows)


def build_sequences(overruns: pd.DataFrame):
    """Sliding windows per family; deviation is feature index 2."""
    X, y, meta = [], [], []
    for fi, family in enumerate(FAMILIES):
        g = overruns[overruns["family"] == family].sort_values("day")
        feats = np.column_stack([
            np.ones(len(g)),
            g["nominal_minutes"].to_numpy(float) / 100.0,
            g["overrun_minutes"].to_numpy(float),
            np.sin(2 * np.pi * g["weekday"].to_numpy(float) / 7),
            np.cos(2 * np.pi * g["weekday"].to_numpy(float) / 7),
        ])
        target = g["overrun_minutes"].to_numpy(float)
        for t in range(WINDOW, len(g)):
            X.append(feats[t - WINDOW:t])
            y.append(target[t])
            meta.append((fi, int(g["day"].iloc[t])))
    return np.array(X), np.array(y), np.array(meta)


def train_val_split(meta, frac=0.7):
    split_day = int(N_DAYS * frac)
    train = meta[:, 1] <= split_day
    return train, ~train


def run(seed=SEED, epochs=150, out_dir=None) -> dict:
    out_dir = out_dir or PROCESSED / "scor" / "make"
    overruns = simulate_overruns(seed)
    X, y, meta = build_sequences(overruns)
    train, val = train_val_split(meta)
    model, preds, history = train_model(X, y, train, seed=seed, epochs=epochs)

    maes = baseline_maes(X, y, meta, train, val, FAMILIES)
    maes["gru"] = float(np.abs(y[val] - preds[val]).mean())
    metrics = pd.DataFrame(
        [{"predictor": k, "val_mae_minutes": v} for k, v in maes.items()])

    rows = []
    for fi, family in enumerate(FAMILIES):
        mask = meta[:, 0] == fi
        bias = float(y[train & mask].mean())
        last = int(np.where(mask)[0].max())
        rows.append({"family": family, "nominal_minutes": NOMINAL_MINUTES,
                     "train_mean_overrun": bias,
                     "gru_next_overrun": float(preds[last])})
    corrections = pd.DataFrame(rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_parquet(out_dir / "metrics.parquet", index=False)
    corrections.to_parquet(out_dir / "corrections.parquet", index=False)
    return {"metrics": maes, "outputs": str(out_dir)}


if __name__ == "__main__":
    summary = run()
    for predictor, mae in summary["metrics"].items():
        print(f"{predictor:12s} val MAE: {mae:.3f} minutes")
    print("outputs:", summary["outputs"])
