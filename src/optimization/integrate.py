"""Integration: GRU-corrected parameters re-enter the optimiser.

The weekly model scores plans in pallet-weeks under a zero-deviation
assumption. Here every pallet's effective arrival is shifted by the
corrector's per-lane departure-deviation estimate (demand-weighted
across the two pallet lanes), and plans are scored in pallet-days.
The deterministic incumbent scores (0, 0) by construction; under
corrected parameters the same plan reveals ~16,000 early pallet-days
the deterministic view cannot see. Run:
python -m src.optimization.integrate
"""

import numpy as np
import pandas as pd

from src.data import loaders
from src.data.build import PROCESSED
from src.optimization.problem import (
    ScheduleRepair,
    TransportProblem,
    load_problem_data,
)

RESULTS = PROCESSED / "integration"


def corrected_deviation() -> float:
    """Demand-weighted GRU departure deviation for the pallet lanes."""
    corr = pd.read_parquet(PROCESSED / "gru" / "corrections.parquet") \
        .set_index("lane_id")
    pal = loaders.load_pallet_release()
    is_tx = pal["Ship To Location"].str.contains("Texas")
    w_tx = pal.loc[is_tx, "# Pallets"].sum()
    w_ca = pal.loc[~is_tx, "# Pallets"].sum()
    return float((corr.loc["oem_a_ca_n", "gru_next_day_dev"] * w_ca
                  + corr.loc["oem_a_tx", "gru_next_day_dev"] * w_tx)
                 / (w_ca + w_tx))


def day_metrics(x, demand, dev_days=0.0) -> dict:
    """Per-pallet lateness in days: 7 * (ship week - due week) + dev."""
    cum_d = np.cumsum(np.asarray(demand, float))
    cum_x = np.cumsum(np.asarray(x, float))
    pallets = np.arange(1, int(cum_d[-1]) + 1)
    due = np.searchsorted(cum_d, pallets, side="left")
    ship = np.searchsorted(cum_x, pallets, side="left")
    l_days = 7.0 * (ship - due) + dev_days
    return {"early_days": float(np.clip(-l_days, 0, None).sum()),
            "late_days": float(np.clip(l_days, 0, None).sum())}


class DayTransportProblem(TransportProblem):
    """Day-resolution objectives under a departure-deviation estimate."""

    def __init__(self, demand, dev_days=0.0, **kwargs):
        super().__init__(demand, **kwargs)
        self.dev_days = dev_days
        self._pallets = np.arange(1, self.total + 1)
        self._due = np.searchsorted(self.cum_demand, self._pallets,
                                    side="left")

    def _evaluate(self, X, out, **kwargs):
        trucks = np.ceil(X / self.capacity).sum(axis=1)
        early = np.empty(len(X))
        late = np.empty(len(X))
        for i, row in enumerate(X):
            ship = np.searchsorted(np.cumsum(row), self._pallets,
                                   side="left")
            l_days = 7.0 * (ship - self._due) + self.dev_days
            early[i] = np.clip(-l_days, 0, None).sum()
            late[i] = np.clip(l_days, 0, None).sum()
        out["F"] = np.column_stack([trucks, early, late])


def run(pop_size=200, n_gen=300, seed=1, out_dir=RESULTS) -> dict:
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.optimize import minimize

    data = load_problem_data()
    demand = data["demand"]
    dev = corrected_deviation()

    plans = pd.read_parquet(
        PROCESSED / "nsga2" / "pareto_plans.parquet").to_numpy()
    front = pd.read_parquet(PROCESSED / "nsga2" / "pareto_front.parquet")
    rescored = front.copy()
    for label, d in (("det", 0.0), ("corr", dev)):
        scores = [day_metrics(x, demand, d) for x in plans]
        rescored[f"early_days_{label}"] = [s["early_days"] for s in scores]
        rescored[f"late_days_{label}"] = [s["late_days"] for s in scores]

    problem = DayTransportProblem(demand, dev_days=dev)
    res = minimize(problem, NSGA2(pop_size=pop_size,
                                  repair=ScheduleRepair()),
                   ("n_gen", n_gen), seed=seed, verbose=False)
    reopt = pd.DataFrame(res.F, columns=["trucks", "early_days", "late_days"])

    incumbent_corr = day_metrics(demand, demand, dev)
    out_dir.mkdir(parents=True, exist_ok=True)
    rescored.to_parquet(out_dir / "front_rescored.parquet", index=False)
    reopt.to_parquet(out_dir / "front_corrected.parquet", index=False)
    _plot(rescored, incumbent_corr, out_dir / "integration.png")

    zb = reopt[reopt["late_days"] == 0]
    return {
        "corrected_deviation_days": round(dev, 4),
        "incumbent_corrected": {k: round(v) for k, v in
                                incumbent_corr.items()},
        "reopt_zero_late_min_trucks": int(zb["trucks"].min()) if len(zb)
                                      else None,
        "outputs": str(out_dir),
    }


def _plot(rescored, incumbent_corr, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.scatter(rescored["early_days_det"], rescored["late_days_det"],
               s=26, color="#4477AA", edgecolors="white", linewidths=0.5,
               label="front, deterministic parameters")
    ax.scatter(rescored["early_days_corr"], rescored["late_days_corr"],
               s=26, color="#EE7733", edgecolors="white", linewidths=0.5,
               label="same front, corrected parameters")
    ax.scatter([0], [0], marker="*", s=240, color="#4477AA", zorder=3,
               label="incumbent, deterministic (0, 0)")
    ax.scatter([incumbent_corr["early_days"]],
               [incumbent_corr["late_days"]], marker="*", s=240,
               color="#EE7733", zorder=3,
               label="incumbent, corrected")
    ax.set_xlabel("earliness (pallet-days)")
    ax.set_ylabel("backlog (pallet-days)")
    ax.set_title("What corrected parameters reveal: same plans, two realities")
    ax.legend(frameon=False, fontsize=8.5)
    ax.grid(alpha=0.25, linewidth=0.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    for key, value in run().items():
        print(f"{key}: {value}")