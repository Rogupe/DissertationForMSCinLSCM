"""Verification of the NSGA-II problem definition."""

import numpy as np
import pytest
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

from src.data.loaders import DATA_DIR
from src.optimization.problem import (
    ScheduleRepair,
    TransportProblem,
    _normalise,
    evaluate_plan,
    load_problem_data,
)
from src.optimization.run_nsga2 import (
    run
)
pytestmark = pytest.mark.skipif(
    not DATA_DIR.exists(),
    reason="raw data files are not distributed with the repository",
)
def test_incumbent_is_the_on_time_corner():
    data = load_problem_data()
    assert evaluate_plan(data["demand"], data["demand"]) == {
        "trucks": 114, "early": 0, "late": 0}
    # The incumbent heuristic is exactly the weekly ceiling rule.
    weekly_ceil = np.ceil(data["demand"] / data["capacity"]).astype(int)
    assert (weekly_ceil == data["incumbent_trucks"]).all()
    assert int(np.ceil(data["demand"].sum() / data["capacity"])) == 97
def test_repair_normalises_any_candidate():
    rng = np.random.default_rng(0)
    for _ in range(100):
        fixed = _normalise(rng.uniform(0, 2100, 35), 20293, 2100)
        assert fixed.sum() == 20293
        assert fixed.min() >= 0 and fixed.max() <= 2100
def test_nsga2_smoke_beats_incumbent_on_trucks():
    data = load_problem_data()
    problem = TransportProblem(data["demand"])
    res = minimize(problem, NSGA2(pop_size=40, repair=ScheduleRepair()),
                   ("n_gen", 30), seed=1, verbose=False)
    X = np.rint(res.X).astype(int)
    assert (X.sum(axis=1) == problem.total).all()
    assert res.F[:, 0].min() >= 97          # never below the floor
    assert res.F[:, 0].min() < 114          # already beats the incumbent
def test_runner_writes_outputs(tmp_path):
    summary = run(pop_size=30, n_gen=20, seed=1, out_dir=tmp_path)
    assert (tmp_path / "pareto_front.parquet").exists()
    assert (tmp_path / "pareto_plans.parquet").exists()
    assert (tmp_path / "pareto.png").exists()
    assert summary["incumbent_trucks"] == 114
    assert 97 <= summary["trucks_min"] < 114