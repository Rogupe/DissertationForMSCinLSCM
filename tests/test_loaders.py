"""Reconciliation suite for the workbook loaders.

Every expected value was independently derived during data profiling
(August 2026) and verified when each loader was written. A failure
means a loader's behaviour changed - or the underlying file did.
"""

import pytest
import pandas as pd
from src.data.loaders import (
    DATA_DIR,
    OEM_B_WEEKLY,
    load_daily_order,
    load_forecast,
    load_inventory,
    load_june_export,
    load_oem_a_daily_po,
    load_oem_a_xref,
    load_oem_b_production_plan,
    load_production_plan,
    load_shipping_management,
    load_shipping_plan,
    load_oem_b_xref,
    load_oem_b_weekly_po,
    load_oem_b_inventory,
    load_oem_b_shipping_mng,
    load_oem_b_coverage,
)
pytestmark = pytest.mark.skipif(
    not DATA_DIR.exists(),
    reason="raw data files are not distributed with the repository",
)
@pytest.fixture(scope="module")
def june():
    return load_june_export()
@pytest.fixture(scope="module")
def daily_order():
    return load_daily_order()
@pytest.fixture(scope="module")
def shipping_mgmt():
    return load_shipping_management()
def test_june_export(june):
    assert len(june) == 502
    dev = june["dep_deviation_days"].value_counts()
    assert dev[0] == 363 and dev[-1] == 126 and dev[-7] == 1
    assert june["dep_deviation_days"].isna().sum() == 12
    assert int(june["short_ship"].sum()) == 12
def test_xref_part_master():
    xref = load_oem_a_xref()
    assert len(xref) == 106
    assert xref["PART_NO"].is_unique
def test_daily_po_releases():
    po = load_oem_a_daily_po()
    assert len(po) == 501
    assert po["PO Number"].nunique() == 10
    assert po["Part Number"].nunique() == 48
    assert int(po["Open Quantity"].sum()) == 27491
    assert po["transit_days"].min() == 5
    assert po["transit_days"].max() == 70
    assert po["transit_days"].mean() == pytest.approx(13.4, abs=0.1)
def test_inventory():
    inv = load_inventory()
    assert len(inv) == 1836
    assert int(inv["SCL Quantity"].sum()) == 131887
    fert = load_inventory(fert_only=True)
    assert len(fert) == 1592
    assert int(fert["SCL Quantity"].sum()) == 107040
def test_daily_order(daily_order):
    assert daily_order.shape == (167, 40)
    edi = [c for c in daily_order.columns if c.startswith("edi_")]
    assert len(edi) == 14
    assert int(daily_order[edi].sum().sum()) == 19344
    buckets = ["07DK", "F", "17DK", "FR"]
    assert int(daily_order[buckets].sum().sum()) == 6319
    assert int(daily_order["MOQ"].isna().sum()) == 132
def test_forecast():
    fc = load_forecast()
    firm = [c for c in fc.columns if c.startswith("firm_")]
    fcst = [c for c in fc.columns if c.startswith("fcst_")]
    assert len(fc) == 167
    assert (len(firm), len(fcst)) == (14, 110)
    assert int(fc[firm].sum().sum()) == 3040
    assert int(fc[fcst].sum().sum()) == 26702
def test_shipping_plan():
    sp = load_shipping_plan()
    assert sp.shape == (167, 31)
    slots = [c for c in sp.columns if c.startswith("slot_")]
    assert slots == ["slot_us_0900", "slot_us_2300", "slot_us_1300",
                     "slot_us_1700", "slot_us_2000", "slot_tx1_2200",
                     "slot_tx1_2200_b"]
    ship = [c for c in sp.columns if c.startswith("ship_")]
    assert int(sp[ship].sum().sum()) == -9254
    assert int((sp[ship] < 0).sum().sum()) == 134
    assert int(sp["kg(PLT)"].notna().sum()) == 137
    allocations = sp[slots].sum().sum() + sp["TOTAL"].sum() + sp["Shipped QTY"].sum()
    assert int(allocations) == 0
def test_shipping_management(shipping_mgmt):
    assert shipping_mgmt.shape == (167, 56)
    edi = [c for c in shipping_mgmt.columns if c.startswith("edi_")]
    short = [c for c in shipping_mgmt.columns if c.startswith("short_")]
    prod = [c for c in shipping_mgmt.columns if c.startswith("prod_")]
    assert (len(edi), len(short), len(prod)) == (14, 14, 12)
    assert int(shipping_mgmt[edi].sum().sum()) == 19344
    assert int((shipping_mgmt[short] < 0).sum().sum()) == 1257
    assert int(shipping_mgmt[short].sum().sum()) == -127108
    assert int(shipping_mgmt[short].isna().sum().sum()) == 13
    groups = shipping_mgmt["DC group"].value_counts().to_dict()
    assert groups == {"Customer DC 1 (CA, US)": 109, "Customer DC 2 (TX, US)": 58}
def test_production_plan():
    pp = load_production_plan()
    prod = [c for c in pp.columns if c.startswith("prod_")]
    assert len(pp) == 383
    assert len(prod) == 42
    grand = int(pp[prod].sum().sum())
    assert grand == 722184
    assert grand == int(pp["Total"].sum())
    assert pp["W/C"].nunique() == 53
    assert pp["Item No."].nunique() == 349
    channels = pp["Sales Type"].value_counts().to_dict()
    assert channels == {"OEM": 124, "ITC": 86, "DEX": 36, "ASP": 4, "CKD": 3}
def test_oem_b_xref():
    xref = load_oem_b_xref()
    assert xref.shape == (932, 20)
    assert xref["Customer PN"].nunique() == 467
    assert len(xref.drop_duplicates(["Customer PN", "Ship to"])) == 930
    assert xref["Tier1 PN"].nunique() == 310
    # The extract carries no price VALUES - only this ERP flag. 843 of
    # 932 rows are 'Y': unit prices exist in the company's ERP but were
    # excluded from the anonymised extract, so the cost objective stays
    # resource-based and prices are a candidate data request.
    flags = xref["Has Unit Price"].value_counts()
    assert int(flags["Y"]) == 843
    assert int(flags["N"]) == 70
    assert int(xref["Has Unit Price"].isna().sum()) == 19
def test_cross_sheet_edi_reconciliation(daily_order, shipping_mgmt):
    """The daily and weekly views bin the same order book: their EDI
    totals must agree."""
    daily = [c for c in daily_order.columns if c.startswith("edi_")]
    weekly = [c for c in shipping_mgmt.columns if c.startswith("edi_")]
    assert int(daily_order[daily].sum().sum()) == int(shipping_mgmt[weekly].sum().sum()) == 19344
def test_oem_b_weekly_po():
    po = load_oem_b_weekly_po()
    weeks = [c for c in po.columns if str(c).startswith("Week ")]
    assert len(po) == 91
    assert len(weeks) == 52
    assert po.attrs["week_of"] == pd.Timestamp("2026-01-19")
    assert int(po[weeks].sum().sum()) == 11645
    assert int(po["Pieces Past Due"].sum()) == 0
    late = [c for c in weeks if int(str(c).split()[1]) > 8]
    assert int((po[late].fillna(0) != 0).sum().sum()) == 261
    assert po["Part Number"].nunique() == 75
    assert po["Ship To Location"].nunique() == 3
def test_oem_b_inventory():
    inv = load_oem_b_inventory()
    assert len(inv) == 2077
    assert int(inv["SCL Quantity"].sum()) == 179529
    assert inv["W/H"].nunique() == 6
    fert = load_oem_b_inventory(fert_only=True)
    assert len(fert) == 1788
    assert int(fert["SCL Quantity"].sum()) == 154921
    # The left summary block's own grand total (cell E1) disagrees with
    # the ERP block by 5,370 units - it is a stale '(Copy Values)'
    # paste. The ERP block is canonical; this documents the drift.
    raw = pd.read_excel(OEM_B_WEEKLY, sheet_name="INV(WIP,FG)",
                        header=None, nrows=1)
    assert int(raw.iloc[0, 4]) == 174159
def test_oem_b_production_plan():
    pp = load_oem_b_production_plan()
    prod = [c for c in pp.columns if c.startswith("prod_")]
    assert len(pp) == 403
    assert len(prod) == 42
    # Shift detail is canonical: one row's pasted Total drifted 1,700
    # units from its own shift cells (formulas flattened to values).
    assert int(pp[prod].sum().sum()) == 653335
    assert int(pp["Total"].sum()) == 655035
    mismatch = (pp["Total"] - pp[prod].sum(axis=1)).abs() > 0.5
    assert int(mismatch.sum()) == 1
    assert pp["W/C"].nunique() == 54
    assert pp["Item No."].nunique() == 386
@pytest.fixture(scope="module")
def oem_b_mng():
    return load_oem_b_shipping_mng()
@pytest.fixture(scope="module")
def oem_b_coverage():
    return load_oem_b_coverage()
def test_oem_b_shipping_mng():
    board = load_oem_b_shipping_mng()
    edi = [c for c in board.columns if c.startswith("edi_wk")]
    short = [c for c in board.columns if c.startswith("short_wk")]
    ship = [c for c in board.columns if c.startswith("ship_d")]
    assert len(board) == 91
    assert (len(edi), len(short), len(ship)) == (7, 7, 12)
    assert edi[0].endswith("2026-02-23") and edi[-1].endswith("2026-04-06")
    assert int(board[edi].sum().sum()) == 2188
    assert int(board[short].sum().sum()) == -8206
    assert int((board[short] < 0).sum().sum()) == 160
    # Snapshot state: shift plan, shipped and backorder columns are all
    # zero, as in every other board in this dataset.
    zeros = board[ship].sum().sum() + board["Shipped QTY"].sum() + board["B/ORDER"].sum()
    assert int(zeros) == 0
    assert int(board[["FR", "RK"]].sum().sum()) == 325
def test_oem_b_coverage(oem_b_coverage):
    cov = oem_b_coverage
    edi = [c for c in cov.columns if c.startswith("edi_wk")]
    short = [c for c in cov.columns if c.startswith("short_wk")]
    buckets = ["07DK", "07IC", "FR", "RK"]
    assert len(cov) == 91
    assert int(cov[buckets].sum().sum()) == 758
    per_row = (cov[buckets].sum(axis=1) - cov["TOTAL"]).abs()
    assert int((per_row > 0.5).sum()) == 0
    assert int(cov[edi].sum().sum()) == 2188
    assert int(cov[short].sum().sum()) == -10391
    assert int((cov[short] < 0).sum().sum()) == 179
    assert cov["Package"].value_counts().to_dict() == {"Bulk": 83, "Unitized": 8}
    assert cov["TYPE"].value_counts().to_dict() == {"STRUT": 48, "SHOCK": 33,
                                                    "UNI": 8, "RUBBER": 2}
def test_oem_b_boards_agree_on_demand(oem_b_mng, oem_b_coverage):
    """Both boards carry the same 7-week EDI band - but their Shortage
    columns net differently and legitimately disagree."""
    mng_edi = [c for c in oem_b_mng.columns if c.startswith("edi_wk")]
    cov_edi = [c for c in oem_b_coverage.columns if c.startswith("edi_wk")]
    assert int(oem_b_mng[mng_edi].sum().sum()) == int(oem_b_coverage[cov_edi].sum().sum()) == 2188