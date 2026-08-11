"""Verification of the corrected-parameter integration."""

import numpy as np
import pytest

from src.data.loaders import DATA_DIR
from src.optimization.integrate import corrected_deviation, day_metrics
from src.optimization.problem import evaluate_plan, load_problem_data

pytestmark = pytest.mark.skipif(
    not DATA_DIR.exists(),
    reason="raw data files are not distributed with the repository",
)


def test_corrected_deviation_value():
    assert corrected_deviation() == pytest.approx(-0.7906, abs=1e-3)


def test_day_metrics_invariant_at_zero_deviation():
    data = load_problem_data()
    rng = np.random.default_rng(2)
    for _ in range(5):
        x = rng.multinomial(20293, np.ones(35) / 35)
        weekly = evaluate_plan(x, data["demand"])
        days = day_metrics(x, data["demand"], 0.0)
        assert days["early_days"] == 7 * weekly["early"]
        assert days["late_days"] == 7 * weekly["late"]

        
def test_incumbent_under_corrected_parameters():
    data = load_problem_data()
    corrected = day_metrics(data["demand"], data["demand"],
                            corrected_deviation())
    # The deterministic model scores the incumbent (0, 0); corrected
    # parameters reveal ~16,000 early pallet-days it cannot see.
    assert corrected["late_days"] == 0
    assert corrected["early_days"] == pytest.approx(16043, abs=5)