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
OEM_A_DAILY = DATA_DIR / "OEM-A_AS_DAILY_SHIPPING_MGMT_20260225_ANON.xlsx"
def _col(df: pd.DataFrame, prefix: str) -> str:
    """First column starting with prefix - several X-REF headers are
    truncated in the source cells (e.g. QUANTITY_PER_PALLE~)."""
    return next(c for c in df.columns if c.startswith(prefix))

def load_oem_a_xref(dedupe: bool = True) -> pd.DataFrame:
    """OEM-A part master / cross-reference (X-REF sheet).

    Header on Excel row 2, ~129 records, then blank formatted rows.
    The sheet carries 24 duplicate part rows at source - trailing-space
    variants and superseded revisions - so by default only the
    highest-rank revision of each stripped part number is kept.
    """
    df = pd.read_excel(OEM_A_DAILY, sheet_name="X-REF", header=1)
    df = df.dropna(how="all")
    df["PART_NO"] = df["PART_NO"].str.strip()

    # 18 unpriced rows carry the literal string 'NO' in PRICE.
    df["PRICE"] = pd.to_numeric(df["PRICE"], errors="coerce")

    if dedupe:
        df = df[df[_col(df, "HIGHEST_RANK")] == "Y"]
        df = df.drop_duplicates("PART_NO")
    return df

def load_oem_a_daily_po() -> pd.DataFrame:
    """OEM-A open PO release lines (DAILY PO sheet, EDI extract).

    Header on Excel row 2; ~501 real lines, then ~4,000 empty formatted
    ghost rows that inflate the sheet. Dates are MM/DD/YYYY text, and
    the receipt-date header has leading spaces in the source cell.

    Verified to be the SAME extract as PART_RELEASE_DATA_BULK's Raw
    sheet: use one or the other as demand, never both.
    """
    df = pd.read_excel(OEM_A_DAILY, sheet_name="DAILY PO", header=1)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=["PO Number"])

    for col in ("Ship Date", "Receipt Date"):
        df[col] = pd.to_datetime(df[col], format="%m/%d/%Y")

    df["transit_days"] = (df["Receipt Date"] - df["Ship Date"]).dt.days
    return df