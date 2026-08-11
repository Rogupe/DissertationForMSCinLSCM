"""Verification of the experiment suite (tiny budgets)."""

import pytest

from src.data.loaders import DATA_DIR
from src.optimization.experiments import (
    capacity_sensitivity,
    deviation_sensitivity,
    seed_robustness,
)
from src.optimization.problem import load_problem_data

pytestmark = pytest.mark.skipif(
    not DATA_DIR.exists(),
    reason="raw data files are not distributed with the repository",
)


@pytest.fixture(scope="module")
def demand():
    return load_problem_data()["demand"]


def test_seed_robustness_smoke(demand):
    seeds_df, merged = seed_robustness(demand, seeds=(1, 2),
                                       pop_size=40, n_gen=30)
    assert len(seeds_df) == 2
    assert (seeds_df["trucks_min"] >= 97).all()
    assert (merged["trucks"] >= 97).all()


def test_capacity_heuristic_and_floor_exact(demand):
    cap_df = capacity_sensitivity(demand, capacities=(180, 210, 240),
                                  pop_size=30, n_gen=20)
    assert cap_df["heuristic_trucks"].tolist() == [134, 114, 104]
    assert cap_df["floor"].tolist() == [113, 97, 85]
    assert (cap_df["optimised_zero_backlog"]
            < cap_df["heuristic_trucks"]).all()


def test_deviation_asymmetry(demand):
    dev_df = deviation_sensitivity(demand, devs=(-0.7906, 0.0, 0.7906))
    assert dev_df.loc[1, "early_days"] == 0 and dev_df.loc[1, "late_days"] == 0
    assert dev_df.loc[0, "early_days"] == pytest.approx(16043, abs=2)
    assert dev_df.loc[0, "late_days"] == 0
    assert dev_df.loc[2, "late_days"] == pytest.approx(16043, abs=2)
    assert dev_df.loc[2, "early_days"] == 0