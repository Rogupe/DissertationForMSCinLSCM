"""Dimension tables: the hand-curated lane dictionary and helpers.

Every distinct location string across the five workbooks (harvested
August 2026, post-anonymisation-scrub) resolves here to a canonical
lane_id. Curation decisions that merge divergent spellings are
recorded in the notes column - most importantly the Northern
California and Texas naming divergences between the BULK and PALLET
releases, treated as single lanes pending confirmation from the
company.
"""

import pandas as pd
import numpy as np

from src.data import loaders


def _lane(lane_id, kind, customer=None, country=None, mode=None,
          t_min=None, t_max=None, scope="context", notes=""):
    return {"lane_id": lane_id, "kind": kind, "customer": customer,
            "country": country, "mode": mode, "transit_min": t_min,
            "transit_max": t_max, "scope": scope, "notes": notes}


_LANES = [
    # -- OEM-A outbound DC lanes: the optimisation decision space -----
    _lane("oem_a_ca_n", "oem_a_dc", "OEM-A", "US", "truck", 8, 9, "core",
          "PALLET 'Northern California' (8d) + BULK 'Northern California 2' "
          "(9d) merged; open question with the company"),
    _lane("oem_a_tx", "oem_a_dc", "OEM-A", "US", "truck", 4, 5, "core",
          "PALLET 'Central Texas' (4d) + BULK 'North Texas' (5d) merged; "
          "open question with the company"),
    _lane("oem_a_ca_s", "oem_a_dc", "OEM-A", "US", "truck", 9, 12, "extension"),
    _lane("oem_a_ny", "oem_a_dc", "OEM-A", "US", "truck", 13, 14, "extension"),
    _lane("oem_a_wa", "oem_a_dc", "OEM-A", "US", "truck", 12, 12, "extension"),
    _lane("oem_a_il", "oem_a_dc", "OEM-A", "US", "truck", 9, 12, "extension"),
    _lane("oem_a_fl", "oem_a_dc", "OEM-A", "US", "truck", 12, 12, "extension"),
    _lane("oem_a_sc", "oem_a_dc", "OEM-A", "US", "truck", 9, 9, "extension"),
    _lane("oem_a_nl", "oem_a_dc", "OEM-A", "NL", "sea", 70, 70, "extension"),
    _lane("oem_a_cn", "oem_a_dc", "OEM-A", "CN", "sea", 45, 45, "extension"),
    _lane("oem_a_sp", "channel", "OEM-A", "US", "truck", notes=
          "Service-parts channel code, sole ship-to name on the OEM-A "
          "boards; geography lives in the DC-group column"),
    # -- Customer sites (context for JUNE / inventory) ----------------
    _lane("oem_b_mi2", "customer_site", "OEM-B", "US"),
    _lane("oem_b_mi3", "customer_site", "OEM-B", "US"),
    _lane("oem_b_mi4", "customer_site", "OEM-B", "US"),
    _lane("oem_b_mi5", "customer_site", "OEM-B", "US"),
    _lane("oem_b_tn1", "customer_site", "OEM-B", "US"),
    _lane("oem_b_tn2", "customer_site", "OEM-B", "US"),
    _lane("oem_b_can1", "customer_site", "OEM-B", "CA"),
    _lane("oem_b_mx2", "customer_site", "OEM-B", "MX"),
    _lane("oem_b_mx3", "customer_site", "OEM-B", "MX"),
    _lane("oem_b_mx4", "customer_site", "OEM-B", "MX"),
    _lane("oem_b_brazil", "customer_site", "OEM-B", "BR"),
    _lane("oem_b_ar", "customer_site", "OEM-B", "AR"),
    _lane("oem_c_mi1", "customer_site", "OEM-C", "US"),
    _lane("oem_c_ky1", "customer_site", "OEM-C", "US"),
    _lane("oem_c_de1", "customer_site", "OEM-C", "DE"),
    _lane("oem_c_sp", "channel", "OEM-C", "US"),
    _lane("oem_c_mx6", "customer_site", "OEM-C", "MX"),
    _lane("oem_c_mex", "customer_site", "OEM-C", "MX"),
    _lane("oem_d_al", "customer_site", "OEM-D", "US"),
    _lane("oem_d_ga", "customer_site", "OEM-D", "US"),
    _lane("oem_d_rnd", "customer_site", "OEM-D", "US"),
    _lane("oem_e_ga", "customer_site", "OEM-E", "US"),
    _lane("oem_e_mx", "customer_site", "OEM-E", "MX"),
    _lane("oem_f_na", "customer_site", "OEM-F", "US"),
    _lane("oem_g_ca1", "customer_site", "OEM-G", "US"),
    _lane("oem_h_mx1", "customer_site", "OEM-H", "MX"),
    _lane("aftmkt_a_al", "customer_site", "AFTMKT-A", "US"),
    _lane("lsp_a", "lsp", "LSP-A", "KR"),
    _lane("lsp_a_br", "lsp", "LSP-A", "BR", "sea"),
    # -- Own network --------------------------------------------------
    _lane("t1_susp_al", "own_plant", "Tier1", "US"),
    _lane("t1_steer_ga", "own_plant", "Tier1", "US"),
    _lane("t1_brake_al", "own_plant", "Tier1", "US"),
    _lane("t1_plant_b_kr", "own_plant", "Tier1", "KR"),
    _lane("t1mb", "own_plant", "Tier1", "MX", notes="Sister Mexico plant"),
    _lane("t1_trading", "own_network", "Tier1", notes="Trading/logistics arm"),
    # -- Non-physical -------------------------------------------------
    _lane("forecast_bucket", "bucket", notes="CISCO 17798: forecast rows, "
          "not a shippable destination"),
]

LANE_MAP = {
    # BULK / PALLET / DAILY PO release locations
    "OEM-A DC, Northern California, US": "oem_a_ca_n",
    "OEM-A DC, Northern California 2, US": "oem_a_ca_n",
    "OEM-A DC, Southern California, US": "oem_a_ca_s",
    "OEM-A DC, Central Texas, US": "oem_a_tx",
    "OEM-A DC, North Texas, US": "oem_a_tx",
    "OEM-A DC, New York, US": "oem_a_ny",
    "OEM-A DC, Washington, US": "oem_a_wa",
    "OEM-A DC, Illinois, US": "oem_a_il",
    "OEM-A DC, Florida, US": "oem_a_fl",
    "OEM-A DC, South Carolina, US": "oem_a_sc",
    "OEM-A DC, Netherlands, NL": "oem_a_nl",
    "OEM-A Bonded Warehouse (CN)": "oem_a_cn",
    # OEM-A board DC groups
    "Customer DC 1 (CA, US)": "oem_a_ca_n",
    "Customer DC 2 (TX, US)": "oem_a_tx",
    # JUNE register / inventory ship-to codes
    "T1M_OEM-A US_DE": "oem_a_ca_n",
    "T1M_OEM-A TX1_DE": "oem_a_tx",
    "T1M_OEM-A NL1_AS": "oem_a_nl",
    "T1M_OEM-A_DE(SP)": "oem_a_sp",
    "T1M_OEM-B_LLC(MI2)_DE(SP)": "oem_b_mi2",
    "T1M_OEM-B_LLC(MI2)_AS": "oem_b_mi2",
    "T1M_OEM-B_LLC(MI3)_DE(SP)": "oem_b_mi3",
    "T1M_OEM-B_LLC(MI3)_AS": "oem_b_mi3",
    "T1M_OEM-B_LLC(MI4)_DE(SP)": "oem_b_mi4",
    "T1M_OEM-B_LLC(MI4)_DE(SP": "oem_b_mi4",   # truncated at source
    "T1M_OEM-B_LLC(MI5 RDC)_DE(SP)": "oem_b_mi5",
    "T1M_OEM-B_LLC(TN2 PDC)_DE(SP)": "oem_b_tn2",
    "T1M_OEM-B_TN1_DE": "oem_b_tn1",
    "T1M_OEM-B_CAN1_DE": "oem_b_can1",
    "T1M_OEM-B_MX2_MX_AS": "oem_b_mx2",
    "T1M_OEM-B_MX3_OEM": "oem_b_mx3",
    "T1M_OEM-B_MX4_OEM": "oem_b_mx4",
    "T1M_OEM-B_BRAZIL_DE(SP)": "oem_b_brazil",
    "T1M_OEM-C_MI1_DE": "oem_c_mi1",
    "T1M_OEM-C_KY1_DE": "oem_c_ky1",
    "T1M_OEM-C DE1_DE(SP)": "oem_c_de1",
    "T1M_OEM-C_DE(SP)": "oem_c_sp",
    "T1M_OEM-C_MX6_MX": "oem_c_mx6",
    "T1M_OEM-C_MEX_OEM": "oem_c_mex",
    "T1M_OEM-D-AL_DE": "oem_d_al",
    "T1M_OEM-D-GA_DE": "oem_d_ga",
    "T1M_OEM-D-RND_OEM": "oem_d_rnd",
    "T1M_OEM-E-GA_DE": "oem_e_ga",
    "T1M_OEM-E-MX_OEM": "oem_e_mx",
    "T1M_OEM-F NA_DE": "oem_f_na",
    "T1M_OEM-G CA1_USA_OEM": "oem_g_ca1",
    "T1M_OEM-H_MX1_OEM": "oem_h_mx1",
    "T1M_OEM-H_MX1_OEM(USD)": "oem_h_mx1",
    "T1M_OEM-H_MX1_AS": "oem_h_mx1",
    "T1M_OEM-H_MX1_AS (USD)": "oem_h_mx1",
    "T1M_OEM-H_MX1_CKD(USD)": "oem_h_mx1",
    "T1M_AFTMKT-A AL_DE (SP)": "aftmkt_a_al",
    "T1M_LSP-A_CKD": "lsp_a",
    "T1M_LSP-A BR_CKD": "lsp_a_br",
    "T1M_T1MB_AS": "t1mb",
    "T1M_T1MB_OEM": "t1mb",
    "T1M_TIER1 TRADING_AM": "t1_trading",
    "Tier1 Suspension Plant (AL, US)": "t1_susp_al",
    "Tier1 Steering Plant (GA, US)": "t1_steer_ga",
    "Tier1 Brake Plant (AL, US)": "t1_brake_al",
    "Tier1 Automotive Plant B (KR)": "t1_plant_b_kr",
    # OEM-B dock codes (CISCO), verified site codes, SO block labels
    "17177": "oem_b_mi2",
    "17576": "oem_b_mi3",
    "17798": "forecast_bucket",
    "Forecast": "forecast_bucket",
    "S900000007": "oem_b_mi2",
    "S900000011": "oem_b_mi3",
    "MI2": "oem_b_mi2",
    "MI3": "oem_b_mi3",
    "MI4": "oem_b_mi4",
    "MI5": "oem_b_mi5",
    "Brazil": "oem_b_brazil",
    "Argentina": "oem_b_ar",
}

# Truck departure slots (SHIPPING PLAN column prefixes) -> lanes.
SLOT_LANES = {"us": "oem_a_ca_n", "tx1": "oem_a_tx"}


def _norm(value) -> str:
    return " ".join(str(value).split())


def build_dim_lane() -> pd.DataFrame:
    return pd.DataFrame(_LANES)


def resolve_lanes(series: pd.Series) -> pd.Series:
    """Map raw location strings to lane_id (NaN where unknown)."""
    return series.map(lambda v: LANE_MAP.get(_norm(v)) if pd.notna(v) else None)


def unresolved(series: pd.Series) -> set:
    """Distinct non-null values that do not resolve to a lane."""
    values = series.dropna().map(_norm)
    return set(values[~values.isin(LANE_MAP)])

def build_dim_part() -> pd.DataFrame:
    """One row per (customer_pn, tier1_pn) pair, merged from the three
    part masters: OEM-A X-REF, OEM-B Cross Reference and the June
    register's material pairs. The grain is the PAIR, not the part -
    eight customer PNs carry multiple internal revisions, and one
    OEM-A part ships in June under a different revision than X-REF
    records. Attributes: X-REF price and pallet quantity (OEM-A only),
    PALLET Std Pack (28 parts), and the unitized-packaging flag.
    """
    xa = loaders.load_oem_a_xref()
    pn = next(c for c in xa.columns if c.startswith("PART_NO"))
    item = next(c for c in xa.columns if c.startswith("ITEM_NO"))
    qpp = next(c for c in xa.columns if c.startswith("QUANTITY_PER_PALLE"))
    a = xa[[pn, item, "PRICE", qpp]].dropna(subset=[pn, item]).copy()
    a.columns = ["customer_pn", "tier1_pn", "price", "qty_per_pallet"]
    for c in ("customer_pn", "tier1_pn"):
        a[c] = a[c].astype(str).str.strip()
    a = a.drop_duplicates(["customer_pn", "tier1_pn"])
    a["in_oem_a_xref"] = True

    xb = loaders.load_oem_b_xref()
    b = xb[["Customer PN", "Tier1 PN"]].dropna().copy()
    b.columns = ["customer_pn", "tier1_pn"]
    for c in b.columns:
        b[c] = b[c].astype(str).str.strip()
    b = b.drop_duplicates()
    b["in_oem_b_xref"] = True

    june = loaders.load_june_export()
    j = june[["Cust. Material", "Material", "Customer Desc."]].dropna(
        subset=["Cust. Material", "Material"]).copy()
    j.columns = ["customer_pn", "tier1_pn", "june_customer"]
    for c in ("customer_pn", "tier1_pn"):
        j[c] = j[c].astype(str).str.strip()
    j["june_customer"] = j["june_customer"].astype(str).str.split().str[0]
    j = (j.groupby(["customer_pn", "tier1_pn"], as_index=False)
          .agg(june_customer=("june_customer", lambda s: s.mode().iat[0])))
    j["in_june"] = True

    parts = (a.merge(b, on=["customer_pn", "tier1_pn"], how="outer")
              .merge(j, on=["customer_pn", "tier1_pn"], how="outer"))
    for c in ("in_oem_a_xref", "in_oem_b_xref", "in_june"):
        parts[c] = parts[c].fillna(False).astype(bool)

    parts["customer"] = np.select(
        [parts["in_oem_a_xref"], parts["in_oem_b_xref"]],
        ["OEM-A", "OEM-B"],
        default=parts["june_customer"],
    )
    parts = parts.drop(columns=["june_customer"])

    pal = loaders.load_pallet_release()
    std_pack = pal.groupby(pal["Part Number"].str.strip())["Std Pack"].first()
    parts["std_pack"] = parts["customer_pn"].map(std_pack)
    parts["unitized"] = parts["customer_pn"].isin(
        set(loaders.load_unitized_parts()))

    return parts.sort_values(["customer", "customer_pn"]).reset_index(drop=True)