"""Fact-table builders: loaders + dimensions -> model-ready tables.

Facts are tidy, lane-resolved and typed. write_processed() persists
them together with the dimension tables as parquet under
data/processed - gitignored, like everything derived from the dataset.
"""

from pathlib import Path

import pandas as pd

from src.data import loaders
from src.data.dimensions import build_dim_lane, build_dim_part, resolve_lanes

PROCESSED = loaders.DATA_DIR.parent / "processed"


def fact_release() -> pd.DataFrame:
    """Open release lines from both snapshots, lane-resolved: BULK
    (February, ten lanes) and PALLET (April, two lanes, with pallet
    quantities). DAILY PO is deliberately absent - it is the same
    extract as BULK (verified), and including it would double demand.
    """
    bulk = loaders.load_bulk_release().assign(source="bulk_2026_02")
    pallet = loaders.load_pallet_release().assign(source="pallet_2026_04")
    df = pd.concat([bulk, pallet], ignore_index=True)
    return pd.DataFrame({
        "source": df["source"],
        "customer_pn": df["Part Number"].astype(str).str.strip(),
        "lane_id": resolve_lanes(df["Ship To Location"]),
        "po_number": df["PO Number"].astype(str),
        "po_line": df["PO Line #"],
        "release_date": df["Release Date"],
        "ship_date": df["Ship Date"],
        "receipt_date": df["Receipt Date"],
        "qty": df["Open Quantity"],
        "std_pack": df["Std Pack"],
        "pallets": df["# Pallets"],
    })


def fact_shipments() -> pd.DataFrame:
    """The June register as the pipeline's plan-vs-actual fact: one row
    per shipment with lane, value and the three deviation signals."""
    june = loaders.load_june_export()
    return pd.DataFrame({
        "shipment_doc": june["Shipment Doc."],
        "lane_id": resolve_lanes(june["Ship To"]),
        "customer": june["Customer Desc."].astype(str).str.split().str[0],
        "transport": june["Transport"],
        "country": june["Country"],
        "customer_pn": june["Cust. Material"].astype(str).str.strip(),
        "tier1_pn": june["Material"].astype(str).str.strip(),
        "qty": june["Qty"],
        "amount": june["Amount"],
        "created_ts": june["created_ts"],
        "etd": june["E.T.D Port"],
        "gi_date": june["G/I Date"],
        "dep_deviation_days": june["dep_deviation_days"],
        "customs_lag_days": june["customs_lag_days"],
        "short_ship": june["short_ship"],
        "cleared": june["cleared"],
    })


def fact_inventory() -> pd.DataFrame:
    """Both plants' lot-level stock stacked, lane-resolved. 93 lots
    (21,758 units) carry no ship-to at source - unallocated stock, a
    legitimate NaN lane the optimiser is free to assign."""
    inv_a = loaders.load_inventory().assign(source="oem_a_2026_02_25")
    inv_b = loaders.load_oem_b_inventory().assign(source="oem_b_2026_02_23")
    df = pd.concat([inv_a, inv_b], ignore_index=True)
    return pd.DataFrame({
        "source": df["source"],
        "tier1_item": df["Item No."].astype(str).str.strip(),
        "customer_item": df["Customer Item No."],
        "lane_id": resolve_lanes(df["Ship To Name"]),
        "warehouse": df["W/H"].astype(str).str.split(" :").str[0],
        "qty": df["SCL Quantity"],
        "item_type": df["Item Type"],
        "shippable": df["Item Type"] == "FERT",
        "mfg_date": df["MFG Date"],
        "receiving_date": df["Receiving Date"],
    })


def write_processed(root: Path = PROCESSED) -> dict:
    """Persist dimensions and facts as parquet; returns row counts."""
    root.mkdir(parents=True, exist_ok=True)
    tables = {
        "dim_lane": build_dim_lane(),
        "dim_part": build_dim_part(),
        "fact_release": fact_release(),
        "fact_shipments": fact_shipments(),
        "fact_inventory": fact_inventory(),
    }
    written = {}
    for name, df in tables.items():
        df.to_parquet(root / f"{name}.parquet", index=False)
        written[name] = len(df)
    return written