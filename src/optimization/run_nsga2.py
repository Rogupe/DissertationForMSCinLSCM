"""NSGA-II runner: optimise the dispatch plan, persist front and figure.

Outputs land under data/processed/nsga2 (gitignored): the Pareto front
and plans as parquet, and the front figure as PNG. Run from the repo
root with:  python -m src.optimization.run_nsga2
"""

from pathlib import Path

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

from src.data.build import PROCESSED
from src.optimization.problem import (
    ScheduleRepair,
    TransportProblem,
    evaluate_plan,
    load_problem_data,
)

RESULTS = PROCESSED / "nsga2"


def run(pop_size=200, n_gen=500, seed=1, out_dir: Path = RESULTS) -> dict:
    data = load_problem_data()
    problem = TransportProblem(data["demand"])
    res = minimize(problem, NSGA2(pop_size=pop_size, repair=ScheduleRepair()),
                   ("n_gen", n_gen), seed=seed, verbose=False)

    front = pd.DataFrame(res.F.astype(int), columns=["trucks", "early", "late"])
    plans = pd.DataFrame(np.rint(res.X).astype(int),
                         columns=[f"wk{w}" for w in data["weeks"]])
    incumbent = evaluate_plan(data["demand"], data["demand"])

    out_dir.mkdir(parents=True, exist_ok=True)
    front.to_parquet(out_dir / "pareto_front.parquet", index=False)
    plans.to_parquet(out_dir / "pareto_plans.parquet", index=False)
    _plot(front, incumbent, out_dir / "pareto.png")

    zero_backlog = front[front["late"] == 0]
    best_zb = None
    if len(zero_backlog):
        best_zb = zero_backlog.loc[zero_backlog["trucks"].idxmin()]
    return {
        "solutions": len(front),
        "trucks_min": int(front["trucks"].min()),
        "trucks_max": int(front["trucks"].max()),
        "incumbent_trucks": incumbent["trucks"],
        "zero_backlog_best": None if best_zb is None else
            {"trucks": int(best_zb["trucks"]), "early": int(best_zb["early"])},
        "outputs": str(out_dir),
    }


def _plot(front, incumbent, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    scatter = ax.scatter(front["early"], front["late"], c=front["trucks"],
                         cmap="Blues", vmin=front["trucks"].min() - 4,
                         s=34, edgecolors="white", linewidths=0.6)
    ax.scatter([incumbent["early"]], [incumbent["late"]], marker="*",
               s=260, color="#B3261E", zorder=3,
               label=f"incumbent plan ({incumbent['trucks']} trucks)")

    zb = front[front["late"] == 0]
    if len(zb):
        best = zb.loc[zb["trucks"].idxmin()]
        ax.annotate(f"{int(best['trucks'])} trucks, zero backlog",
                    xy=(best["early"], best["late"]),
                    xytext=(best["early"] * 0.55, front["late"].max() * 0.18),
                    fontsize=9, arrowprops={"arrowstyle": "-", "lw": 0.7})

    fig.colorbar(scatter, label="trucks dispatched")
    ax.set_xlabel("earliness (pallet-weeks)")
    ax.set_ylabel("backlog (pallet-weeks)")
    ax.set_title("Weekly dispatch plan: Pareto front vs incumbent")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(alpha=0.25, linewidth=0.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    for key, value in run().items():
        print(f"{key}: {value}")