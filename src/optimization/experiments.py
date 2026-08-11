"""Headline experiments: robustness and sensitivity analyses.

Three questions, one per headline result: is the 100-truck result
seed-robust; does the heuristic-vs-optimised gap survive uncertainty
in the 210-pallet capacity constant; and how does the incumbent's
hidden deviation exposure behave across the bias range, including the
adverse (late) direction. Run:  python -m src.optimization.experiments
"""

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

from src.data.build import PROCESSED
from src.optimization.integrate import corrected_deviation, day_metrics
from src.optimization.problem import (
    ScheduleRepair,
    TransportProblem,
    load_problem_data,
)

RESULTS = PROCESSED / "experiments"


def _optimise(demand, capacity=210, pop_size=200, n_gen=500, seed=1):
    problem = TransportProblem(demand, capacity=capacity)
    res = minimize(problem, NSGA2(pop_size=pop_size, repair=ScheduleRepair()),
                   ("n_gen", n_gen), seed=seed, verbose=False)
    return res.F.astype(int)


def seed_robustness(demand, seeds=range(1, 11), pop_size=200, n_gen=500):
    rows, fronts = [], []
    for seed in seeds:
        F = _optimise(demand, pop_size=pop_size, n_gen=n_gen, seed=seed)
        zb = F[F[:, 2] == 0]
        rows.append({"seed": seed,
                     "trucks_min": int(F[:, 0].min()),
                     "zero_backlog_trucks":
                         int(zb[:, 0].min()) if len(zb) else None,
                     "front_size": len(F)})
        fronts.append(F)
    stacked = np.vstack(fronts).astype(float)
    keep = NonDominatedSorting().do(stacked, only_non_dominated_front=True)
    merged = pd.DataFrame(stacked[keep].astype(int),
                          columns=["trucks", "early", "late"]).drop_duplicates()
    return pd.DataFrame(rows), merged


def capacity_sensitivity(demand, capacities=(180, 195, 210, 225, 240),
                         pop_size=200, n_gen=400, seed=1):
    rows = []
    for cap in capacities:
        F = _optimise(demand, capacity=cap, pop_size=pop_size,
                      n_gen=n_gen, seed=seed)
        zb = F[F[:, 2] == 0]
        rows.append({
            "capacity": int(cap),
            "heuristic_trucks": int(np.ceil(demand / cap).sum()),
            "optimised_zero_backlog":
                int(zb[:, 0].min()) if len(zb) else None,
            "floor": int(np.ceil(demand.sum() / cap)),
        })
    return pd.DataFrame(rows)


def deviation_sensitivity(demand, devs=None):
    corrected = corrected_deviation()
    if devs is None:
        devs = np.round(np.arange(-2.0, 2.01, 0.25), 2)
    rows = []
    for dev in devs:
        metrics = day_metrics(demand, demand, float(dev))
        rows.append({"dev_days": float(dev), **metrics,
                     "is_corrected_estimate":
                         bool(abs(dev - corrected) < 0.125)})
    return pd.DataFrame(rows)


def run(out_dir=RESULTS, seeds=range(1, 11), pop_size=200, n_gen=500) -> dict:
    data = load_problem_data()
    demand = data["demand"]

    seeds_df, merged = seed_robustness(demand, seeds, pop_size, n_gen)
    cap_df = capacity_sensitivity(demand, pop_size=pop_size, n_gen=n_gen)
    dev_df = deviation_sensitivity(demand)

    out_dir.mkdir(parents=True, exist_ok=True)
    seeds_df.to_parquet(out_dir / "exp1_seeds.parquet", index=False)
    merged.to_parquet(out_dir / "exp1_merged_front.parquet", index=False)
    cap_df.to_parquet(out_dir / "exp2_capacity.parquet", index=False)
    dev_df.to_parquet(out_dir / "exp3_deviation.parquet", index=False)
    _plot_capacity(cap_df, out_dir / "capacity_sensitivity.png")
    _plot_deviation(dev_df, out_dir / "deviation_sensitivity.png")

    return {
        "zero_backlog_trucks_by_seed":
            seeds_df["zero_backlog_trucks"].tolist(),
        "merged_front_zero_backlog_best":
            int(merged.loc[merged["late"] == 0, "trucks"].min()),
        "capacity_savings":
            dict(zip(cap_df["capacity"],
                     cap_df["heuristic_trucks"]
                     - cap_df["optimised_zero_backlog"])),
        "outputs": str(out_dir),
    }


def _plot_capacity(cap_df, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    ax.plot(cap_df["capacity"], cap_df["heuristic_trucks"], "o-",
            color="#EE7733", label="incumbent heuristic (weekly ceiling)")
    ax.plot(cap_df["capacity"], cap_df["optimised_zero_backlog"], "o-",
            color="#4477AA", label="optimised, zero backlog")
    ax.plot(cap_df["capacity"], cap_df["floor"], "--", color="#888888",
            label="theoretical floor")
    ax.set_xlabel("truck capacity (pallets)")
    ax.set_ylabel("trucks dispatched (35 weeks)")
    ax.set_title("The saving survives capacity uncertainty")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_deviation(dev_df, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    ax.plot(dev_df["dev_days"], dev_df["early_days"], "-", lw=2,
            color="#4477AA", label="hidden earliness (pallet-days)")
    ax.plot(dev_df["dev_days"], dev_df["late_days"], "-", lw=2,
            color="#EE7733", label="hidden lateness (pallet-days)")
    est = dev_df.loc[dev_df["is_corrected_estimate"], "dev_days"]
    if len(est):
        ax.axvline(float(est.iloc[0]), color="#888888", ls="--", lw=1,
                   label="GRU estimate (-0.79 d)")
    ax.set_xlabel("departure deviation (days; negative = early)")
    ax.set_ylabel("incumbent's unseen exposure (pallet-days)")
    ax.set_title("Deviation exposure the deterministic model cannot see")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    for key, value in run().items():
        print(f"{key}: {value}")