"""Return corrector: rack-return promises, corrected.

Synthetic scenario (seed 42, grounded in the prior-phase Little's law
fleet model): returnable racks cycle plant -> outbound transit ->
customer dwell -> return transit. The contractual assumption promises a
fixed cycle; in reality customer dwell dominates the variance, with
per-customer bias, month-end retention and an AR(1) congestion state
for the worst customer. The corrector predicts tomorrow's cycle
deviation per customer with the same GRU architecture as every other
SCOR corrector. The runner also sizes the rack fleet at the mean and
p95 cycle via Little's law, the variability cost in racks.

Run:  python -m src.models.return_corrector
"""

import numpy as np
import pandas as pd

from src.data.build import PROCESSED
from src.models.gru_corrector import baseline_maes, train_model

SEED = 42
N_DAYS = 730
WINDOW = 7
CONTRACT_DAYS = 10.0
SHIPMENTS_PER_DAY = 12.0

CUSTOMERS = ["CUST-A", "CUST-B", "CUST-C", "CUST-D", "CUST-E"]
DWELL_MEAN = {"CUST-A": 5.0, "CUST-B": 7.5, "CUST-C": 4.2,
              "CUST-D": 9.0, "CUST-E": 6.0}
DWELL_SIGMA = {"CUST-A": 1.2, "CUST-B": 2.2, "CUST-C": 0.9,
               "CUST-D": 3.2, "CUST-E": 1.6}


def simulate_cycles(seed=SEED) -> pd.DataFrame:
    """Daily mean rack cycle (days) per customer, with components kept
    so the dwell share of variance is measurable."""
    rng = np.random.default_rng(seed)
    congestion = 0.0
    rows = []
    for day in range(N_DAYS):
        congestion = 0.9 * congestion + rng.normal(0.0, 0.7)
        day_of_month = day % 30
        month_end_hold = 1.8 if day_of_month >= 25 else 0.0
        for customer in CUSTOMERS:
            extra = congestion if customer == "CUST-D" else 0.0
            dwell = max(0.5, DWELL_MEAN[customer] + extra + month_end_hold
                        + rng.normal(0.0, DWELL_SIGMA[customer]))
            transit = 4.0 + rng.normal(0.0, 1.2)
            cycle = transit + dwell
            rows.append({"day": day, "day_of_month": day_of_month,
                         "customer": customer, "dwell_days": dwell,
                         "transit_days": transit, "cycle_days": cycle,
                         "deviation_days": cycle - CONTRACT_DAYS})
    return pd.DataFrame(rows)


def dwell_variance_share(cycles: pd.DataFrame) -> float:
    return float(cycles["dwell_days"].var()
                 / (cycles["dwell_days"].var() + cycles["transit_days"].var()))


def fleet_sizing(cycles: pd.DataFrame) -> dict:
    """Little's law: fleet = shipments/day x cycle time."""
    mean_fleet = SHIPMENTS_PER_DAY * float(cycles["cycle_days"].mean())
    p95_fleet = SHIPMENTS_PER_DAY * float(cycles["cycle_days"].quantile(0.95))
    return {"fleet_at_mean": round(mean_fleet),
            "fleet_at_p95": round(p95_fleet),
            "variability_cost_racks": round(p95_fleet - mean_fleet)}


def build_sequences(cycles: pd.DataFrame):
    """Sliding windows per customer; deviation is feature index 2."""
    X, y, meta = [], [], []
    for ci, customer in enumerate(CUSTOMERS):
        g = cycles[cycles["customer"] == customer].sort_values("day")
        feats = np.column_stack([
            np.ones(len(g)),
            np.full(len(g), CONTRACT_DAYS / 10.0),
            g["deviation_days"].to_numpy(float),
            np.sin(2 * np.pi * g["day_of_month"].to_numpy(float) / 30),
            np.cos(2 * np.pi * g["day_of_month"].to_numpy(float) / 30),
        ])
        target = g["deviation_days"].to_numpy(float)
        for t in range(WINDOW, len(g)):
            X.append(feats[t - WINDOW:t])
            y.append(target[t])
            meta.append((ci, int(g["day"].iloc[t])))
    return np.array(X), np.array(y), np.array(meta)


def train_val_split(meta, frac=0.7):
    split_day = int(N_DAYS * frac)
    train = meta[:, 1] <= split_day
    return train, ~train


def run(seed=SEED, epochs=150, out_dir=None) -> dict:
    out_dir = out_dir or PROCESSED / "scor" / "return"
    cycles = simulate_cycles(seed)
    X, y, meta = build_sequences(cycles)
    train, val = train_val_split(meta)
    model, preds, history = train_model(X, y, train, seed=seed, epochs=epochs)

    maes = baseline_maes(X, y, meta, train, val, CUSTOMERS)
    maes["gru"] = float(np.abs(y[val] - preds[val]).mean())
    metrics = pd.DataFrame(
        [{"predictor": k, "val_mae_days": v} for k, v in maes.items()])

    rows = []
    for ci, customer in enumerate(CUSTOMERS):
        mask = meta[:, 0] == ci
        bias = float(y[train & mask].mean())
        last = int(np.where(mask)[0].max())
        rows.append({"customer": customer, "contract_days": CONTRACT_DAYS,
                     "train_mean_deviation": bias,
                     "gru_next_deviation": float(preds[last])})
    corrections = pd.DataFrame(rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_parquet(out_dir / "metrics.parquet", index=False)
    corrections.to_parquet(out_dir / "corrections.parquet", index=False)
    return {"metrics": maes,
            "dwell_variance_share": round(dwell_variance_share(cycles), 3),
            "fleet": fleet_sizing(cycles),
            "outputs": str(out_dir)}


if __name__ == "__main__":
    summary = run()
    for predictor, mae in summary["metrics"].items():
        print(f"{predictor:12s} val MAE: {mae:.3f} days")
    print("dwell variance share:", summary["dwell_variance_share"])
    print("fleet:", summary["fleet"])
    print("outputs:", summary["outputs"])
