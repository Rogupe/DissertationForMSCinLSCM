"""Bespoke extractors for the anonymised supply-chain workbooks.

Each sheet needs its own loader: headers sit on different rows, several
sheets carry banner metadata, and some columns are corrupted at source.
A naive read_excel is wrong for most of them.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

JUNE_EXPORT = DATA_DIR / "JUNE_2026_EXPORT_ANON.xlsx"


def load_june_export() -> pd.DataFrame:
    """June 2026 export shipment register (SAP extract), one row per delivery.

    Single flat header on row 1. Three header names are duplicated at
    source (C/D, Gap, B/L); the first occurrences are entirely empty and
    disappear with the other all-empty columns.
    """
    df = pd.read_excel(JUNE_EXPORT, sheet_name="Sheet1")
    df = df.dropna(axis=1, how="all")

    # Arrival Date is an auto-copy of E.T.D Port at source, and the price
    # columns are zero throughout - none carry information.
    df = df.drop(columns=["Arrival Date", "Price", "Per", "Declared Amount"],
                 errors="ignore")

    # One sales-order-only row has no delivery document.
    df = df[df["Subs"] != "SO"].copy()

    df["created_ts"] = pd.to_datetime(
        df["Created On"].dt.strftime("%Y-%m-%d") + " " + df["Time"].astype(str)
    )

    # The planned-vs-actual signals the GRU corrector trains on.
    df["dep_deviation_days"] = (df["G/I Date"] - df["E.T.D Port"]).dt.days
    df["customs_lag_days"] = (df["Decl. Date"] - df["I/V Date"]).dt.days
    df["short_ship"] = df["B/L. Qty"] < df["Qty"]
    df["cleared"] = df["Cls. Qty"] == df["Qty"]

    return df