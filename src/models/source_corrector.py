"""Source corrector: supplier lead-time promises, corrected.

Synthetic scenario (seed 42, from the prior-phase design): ten inbound
suppliers feed the theorised Queretaro SMT lines. Each supplier quotes
a fixed lead time; actual receipts deviate with supplier-specific bias,
seasonal congestion and, for the critical supplier S05 (ICs and LED
drivers), a slow upward drift. The corrector learns each supplier's
promise error from receipt history. It is the inbound mirror of the
Deliver corrector and reuses the same GRU architecture unchanged.

Run:  python -m src.models.source_corrector
"""

import numpy as np
import pandas as pd

from src.data.build import PROCESSED
from src.models.gru_corrector import baseline_maes, train_model

SEED = 42
N_WEEKS = 104
WINDOW = 8

SUPPLIERS = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10"]
QUOTED_DAYS = {"S01": 7, "S02": 10, "S03": 14, "S04": 5, "S05": 21,
               "S06": 12, "S07": 9, "S08": 30, "S09": 6, "S10": 16}
SPEND_SHARE = {"S01": 0.06, "S02": 0.08, "S03": 0.10, "S04": 0.04, "S05": 0.24,
               "S06": 0.09, "S07": 0.07, "S08": 0.12, "S09": 0.05, "S10": 0.15}
LOG_BIAS = {"S01": 0.00, "S02": 0.05, "S03": -0.04, "S04": 0.00, "S05": 0.16,
            "S06": 0.08, "S07": 0.00, "S08": 0.06, "S09": -0.02, "S10": 0.04}
SIGMA = {"S01": 0.05, "S02": 0.10, "S03": 0.09, "S04": 0.06, "S05": 0.22,
         "S06": 0.12, "S07": 0.05, "S08": 0.14, "S09": 0.06, "S10": 0.11}


def simulate_receipts(seed=SEED) -> pd.DataFrame:
    """Weekly purchase orders over two years, one per supplier."""
    rng = np.random.default_rng(seed)
    rows = []
    for week in range(N_WEEKS):
        season = 0.06 * np.sin(2 * np.pi * week / 52)
        for supplier in SUPPLIERS:
            drift = 0.15 * (week / N_WEEKS) if supplier == "S05" else 0.0
            quoted = QUOTED_DAYS[supplier]
            actual = quoted * np.exp(LOG_BIAS[supplier] + drift + season
                                     + rng.normal(0.0, SIGMA[supplier]))
            rows.append({"week": week, "supplier": supplier,
                         "quoted_days": quoted, "actual_days": actual,
                         "deviation_days": actual - quoted})
    return pd.DataFrame(rows)


def criticality_table(receipts: pd.DataFrame) -> pd.DataFrame:
    """Criticality = spend share x lead-time risk (deviation std)."""
    risk = receipts.groupby("supplier")["deviation_days"].std()
    out = pd.DataFrame({
        "supplier": SUPPLIERS,
        "spend_share": [SPEND_SHARE[s] for s in SUPPLIERS],
        "lead_time_risk_days": [risk[s] for s in SUPPLIERS],
    })
    out["criticality"] = out["spend_share"] * out["lead_time_risk_days"]
    return out.sort_values("criticality", ascending=False).reset_index(drop=True)


def build_sequences(receipts: pd.DataFrame):
    """Sliding windows per supplier; deviation is feature index 2, the
    convention shared by every SCOR corrector so the baseline helpers
    apply unchanged."""
    X, y, meta = [], [], []
    for si, supplier in enumerate(SUPPLIERS):
        g = receipts[receipts["supplier"] == supplier].sort_values("week")
        feats = np.column_stack([
            np.ones(len(g)),
            g["quoted_days"].to_numpy(float) / 30.0,
            g["deviation_days"].to_numpy(float),
            np.sin(2 * np.pi * g["week"].to_numpy(float) / 52),
            np.cos(2 * np.pi * g["week"].to_numpy(float) / 52),
        ])
        target = g["deviation_days"].to_numpy(float)
        for t in range(WINDOW, len(g)):
            X.append(feats[t - WINDOW:t])
            y.append(target[t])
            meta.append((si, int(g["week"].iloc[t])))
    return np.array(X), np.array(y), np.array(meta)


def train_val_split(meta, frac=0.7):
    split_week = int(N_WEEKS * frac)
    train = meta[:, 1] <= split_week
    return train, ~train


def run(seed=SEED, epochs=150, out_dir=None) -> dict:
    out_dir = out_dir or PROCESSED / "scor" / "source"
    receipts = simulate_receipts(seed)
    crit = criticality_table(receipts)
    X, y, meta = build_sequences(receipts)
    train, val = train_val_split(meta)
    model, preds, history = train_model(X, y, train, seed=seed, epochs=epochs)

    maes = baseline_maes(X, y, meta, train, val, SUPPLIERS)
    maes["gru"] = float(np.abs(y[val] - preds[val]).mean())
    metrics = pd.DataFrame(
        [{"predictor": k, "val_mae_days": v} for k, v in maes.items()])

    rows = []
    for si, supplier in enumerate(SUPPLIERS):
        mask = meta[:, 0] == si
        bias = float(y[train & mask].mean()) if (train & mask).any() else np.nan
        last = int(np.where(mask)[0].max())
        rows.append({"supplier": supplier, "quoted_days": QUOTED_DAYS[supplier],
                     "train_mean_deviation": bias,
                     "gru_next_deviation": float(preds[last])})
    corrections = pd.DataFrame(rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_parquet(out_dir / "metrics.parquet", index=False)
    corrections.to_parquet(out_dir / "corrections.parquet", index=False)
    crit.to_parquet(out_dir / "criticality.parquet", index=False)
    return {"metrics": maes,
            "most_critical_supplier": crit.loc[0, "supplier"],
            "outputs": str(out_dir)}


if __name__ == "__main__":
    summary = run()
    for predictor, mae in summary["metrics"].items():
        print(f"{predictor:12s} val MAE: {mae:.3f} days")
    print("most critical supplier:", summary["most_critical_supplier"])
    print("outputs:", summary["outputs"])
