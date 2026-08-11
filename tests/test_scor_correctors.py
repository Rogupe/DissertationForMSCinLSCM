"""Verification of the synthetic SCOR correctors (Source, Make, Return).

These run on simulated scenarios (seed 42), so unlike the Deliver
tests they need no private data and run on any clone of the repo.
"""

import numpy as np
import pytest

from src.models import make_corrector, return_corrector, source_corrector


def test_source_scenario_is_deterministic_and_s05_critical():
    a = source_corrector.simulate_receipts()
    b = source_corrector.simulate_receipts()
    assert len(a) == 104 * 10
    assert np.allclose(a["actual_days"], b["actual_days"])
    crit = source_corrector.criticality_table(a)
    assert crit.loc[0, "supplier"] == "S05"


def test_source_corrector_learns(tmp_path):
    summary = source_corrector.run(epochs=120, out_dir=tmp_path)
    maes = summary["metrics"]
    assert (tmp_path / "metrics.parquet").exists()
    assert (tmp_path / "criticality.parquet").exists()
    assert summary["most_critical_supplier"] == "S05"
    assert maes["gru"] < maes["global_mean"]
    # Drift and seasonality are in the data by design, so the sequence
    # model should also beat the static per-supplier mean here.
    assert maes["gru"] < maes["lane_mean"]


def test_make_corrector_learns(tmp_path):
    overruns = make_corrector.simulate_overruns()
    assert len(overruns) == 730 * 3
    summary = make_corrector.run(epochs=120, out_dir=tmp_path)
    maes = summary["metrics"]
    assert (tmp_path / "corrections.parquet").exists()
    assert maes["gru"] < maes["global_mean"]
    assert maes["gru"] < maes["lane_mean"]


def test_return_scenario_properties(tmp_path):
    cycles = return_corrector.simulate_cycles()
    assert len(cycles) == 730 * 5
    share = return_corrector.dwell_variance_share(cycles)
    # Dwell dominates cycle variance, mirroring the prior-phase finding
    # of ~84%.
    assert 0.75 <= share <= 0.92
    fleet = return_corrector.fleet_sizing(cycles)
    assert fleet["fleet_at_p95"] > fleet["fleet_at_mean"]
    assert fleet["variability_cost_racks"] > 0


def test_return_corrector_learns(tmp_path):
    summary = return_corrector.run(epochs=120, out_dir=tmp_path)
    maes = summary["metrics"]
    assert (tmp_path / "metrics.parquet").exists()
    assert maes["gru"] < maes["global_mean"]
    assert maes["gru"] < maes["lane_mean"]
