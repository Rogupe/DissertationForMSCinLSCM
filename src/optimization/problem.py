"""NSGA-II problem definition for the weekly truck-dispatch plan.

Decision vector: pallets shipped per week over the 35-week pallet-pool
horizon (weeks 19-53, 2026). A repair operator keeps every candidate
shipping exactly the released demand (20,293 pallets), so the search
space contains only complete plans. Trucks are derived at 210 pallets
per truck - the capacity constant of the incumbent plan.

Objectives (all minimised):
    f1  trucks dispatched          (resource-based cost proxy)
    f2  earliness in pallet-weeks  (pull-forward inventory burden)
    f3  backlog in pallet-weeks    (service-level exposure)

The incumbent SCHEDULED TRUCKS plan is exactly the weekly-ceiling
heuristic (verified: ceil(weekly demand / 210) reproduces all 35
weeks) and scores (114, 0, 0) - the on-time corner of the objective
space. The theoretical dispatch floor is ceil(20,293 / 210) = 97.
"""

import numpy as np
from pymoo.core.problem import Problem
from pymoo.core.repair import Repair

from src.data import loaders


def load_problem_data() -> dict:
    """Demand, incumbent plan and constants from the pallet-pool file."""
    wk = loaders.load_pallet_weekly_plan()
    return {
        "weeks": wk["WEEK"].astype(int).tolist(),
        "demand": wk["Pallets EDI"].to_numpy(float),
        "incumbent_trucks": wk["SCHEDULED TRUCKS"].to_numpy(int),
        "capacity": 210,
    }


def _normalise(x, total, upper):
    """Return x as non-negative integers summing exactly to total.

    Largest-remainder scaling, then bounded redistribution for any
    mass lost to the upper clip.
    """
    x = np.clip(np.asarray(x, float), 0, upper)
    if x.sum() <= 0:
        x = np.full_like(x, total / len(x))
    scaled = x * (total / x.sum())
    base = np.floor(scaled).astype(int)
    frac = scaled - base
    base[np.argsort(-frac)[: total - base.sum()]] += 1
    base = np.clip(base, 0, int(upper))
    for _ in range(len(base)):
        leftover = total - base.sum()
        if leftover == 0:
            break
        if leftover > 0:
            room = int(upper) - base
            i = int(np.argmax(room))
            base[i] += min(leftover, room[i])
        else:
            i = int(np.argmax(base))
            base[i] += max(leftover, -base[i])
    return base


def evaluate_plan(x, demand, capacity=210) -> dict:
    """Score one pallet schedule against the released demand."""
    x = np.asarray(x, float)
    cum_x = np.cumsum(x)
    cum_d = np.cumsum(np.asarray(demand, float))
    return {
        "trucks": int(np.ceil(x / capacity).sum()),
        "early": int(np.clip(cum_x - cum_d, 0, None).sum()),
        "late": int(np.clip(cum_d - cum_x, 0, None).sum()),
    }


class TransportProblem(Problem):
    """Tri-objective weekly dispatch problem (vectorised evaluation)."""

    def __init__(self, demand, capacity=210, weekly_upper=2100):
        self.demand = np.asarray(demand, float)
        self.cum_demand = np.cumsum(self.demand)
        self.capacity = capacity
        self.total = int(self.demand.sum())
        super().__init__(n_var=len(self.demand), n_obj=3,
                         xl=0.0, xu=float(weekly_upper))

    def _evaluate(self, X, out, **kwargs):
        trucks = np.ceil(X / self.capacity).sum(axis=1)
        cum = np.cumsum(X, axis=1)
        early = np.clip(cum - self.cum_demand, 0, None).sum(axis=1)
        late = np.clip(self.cum_demand - cum, 0, None).sum(axis=1)
        out["F"] = np.column_stack([trucks, early, late])


class ScheduleRepair(Repair):
    """Project every candidate onto the ship-everything hyperplane."""

    def _do(self, problem, X, **kwargs):
        return np.array([_normalise(row, problem.total, problem.xu[0])
                         for row in X])