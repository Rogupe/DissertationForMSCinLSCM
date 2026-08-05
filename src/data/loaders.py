"""Bespoke extractors for the anonymised supply-chain workbooks.

Each sheet needs its own loader: headers sit on different rows, several
sheets carry banner metadata, and some columns are corrupted at source.
A naive read_excel is wrong for most of them.
"""

from pathlib import Path
import pandas as pd
import datetime

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
def load_inventory(fert_only: bool = False) -> pd.DataFrame:
    """Lot-level warehouse stock (INV(WIP,FG) sheet, whole plant).

    Two tables sit side by side in this sheet: columns A-E are a helper
    pivot feeding the shipping views, so only the ERP lot extract
    (columns G onwards) is read - which also sidesteps the duplicated
    column names between the two blocks. Padding rows below the real lots 
    are dropped via the item number — 290 genuine stock rows carry no lot 
    number at source.

    fert_only=True keeps finished goods (Item Type FERT) - the stock
    that can actually ship. WIP (HALB) and raw (ROH) stay out.
    """
    df = pd.read_excel(OEM_A_DAILY, sheet_name="INV(WIP,FG)",
                       header=1, usecols="G:AG")
    # pandas mangles duplicate header names across the whole row BEFORE
    # usecols is applied, so the ERP block arrives with .1 suffixes.
    df.columns = [c[:-2] if c.endswith(".1") else c for c in df.columns]
    df = df.dropna(subset=["Item No."])

    if fert_only:
        df = df[df["Item Type"] == "FERT"]
    return df
def load_daily_order() -> pd.DataFrame:
    """OEM-A daily order netting (DAILY ORDER sheet).

    Banner sheet: rows 1-4 hold the title, snapshot timestamp and group
    labels. The real header is row 5, and the calendar dates for the
    14-day EDI call-off band live up in row 3 - all fourteen demand
    columns are just named 'EDI', so they are renamed to edi_<date>.
    The trailing coverage-summary block reuses the name 'Stock Lv.'
    and is prefixed cov_ to keep column names unique.

    In this snapshot BACKLOG and the D-DAY..D+5 production band are
    entirely zero; production inflow comes from PRODUCTION PLAN.
    """
    raw = pd.read_excel(OEM_A_DAILY, sheet_name="DAILY ORDER", header=None)
    header, dates = raw.iloc[4], raw.iloc[2]

    cols = []
    for i, name in enumerate(header):
        name = str(name).strip()
        if name == "EDI":
            name = f"edi_{pd.Timestamp(dates[i]).date()}"
        elif i >= 36:                     # trailing coverage-summary block
            name = f"cov_{name}"
        cols.append(name)

    df = raw.iloc[5:].copy()
    df.columns = cols
    df = df.loc[:, [c for c in df.columns if c not in ("nan", "cov_nan")]]
    df = df.dropna(subset=["Customer PN"])

    # Formula-error strings (#VALUE!, #N/A) and the literal 'check'
    # infest MOQ and Stock Lv. - coerce every non-text column.
    text_cols = ("BU", "Ship to name", "Ship to", "PO Number",
                 "Customer PN", "Tier1 PN", "Description", "Program")
    for c in df.columns:
        if c not in text_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df
def load_forecast() -> pd.DataFrame:
    """OEM-A daily demand forecast (FORECAST sheet, 124-day horizon).

    Banner sheet with the real header on row 5. Unlike DAILY ORDER, the
    date columns carry actual datetime objects as their header names
    (row 3 holds text look-alikes - decoys). Row 4 tags each date
    column FIRM (first 14 days, committed EDI orders) or FORECAST
    (revisable tail); the tag becomes the column prefix, firm_/fcst_.
    """
    raw = pd.read_excel(OEM_A_DAILY, sheet_name="FORECAST", header=None)
    header, tags = raw.iloc[4], raw.iloc[3]

    cols = []
    for i, name in enumerate(header):
        if isinstance(name, datetime.datetime):
            prefix = "firm" if str(tags[i]).strip().upper() == "FIRM" else "fcst"
            cols.append(f"{prefix}_{name.date()}")
        else:
            cols.append(str(name).strip())

    df = raw.iloc[5:].copy()
    df.columns = cols
    df = df.loc[:, [c for c in df.columns if c != "nan"]]
    df = df.dropna(subset=["Customer PN"])

    demand_cols = [c for c in df.columns
                   if c.startswith("firm_") or c.startswith("fcst_")]
    for c in demand_cols + ["MOQ"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df
def load_shipping_plan() -> pd.DataFrame:
    """OEM-A daily shipping plan (SHIPPING PLAN sheet).

    The hardest header in the workbook - three stacked rows: row 8
    carries the destination band for the truck slots ('OEM-A US' x5,
    'TEXAS_TX1' x2), row 9 the departure times (one stored as the
    string '11:00 PM' among real time objects), and row 10 the real
    column names - except the seven slot columns, which have no header
    at all and are named here from destination + time (slot_us_0900
    ... slot_tx1_2200_b; two Texas slots share 22:00).

    The D..D+4 band is a net-requirement formula renamed ship_<date>
    from the row-9 dates; in this snapshot it is entirely <= 0 (stock
    covered near-term demand) and every allocation column is zero, so
    the sheet's durable value is the slot timetable and the kg(PLT)
    pallet-weight factors, whose -1 sentinels become NaN.
    """
    raw = pd.read_excel(OEM_A_DAILY, sheet_name="SHIPPING PLAN", header=None)
    band, times, header = raw.iloc[7], raw.iloc[8], raw.iloc[9]

    def slot_time(value):
        if isinstance(value, datetime.time):
            return f"{value.hour:02d}{value.minute:02d}"
        t = pd.to_datetime(str(value)).time()   # the '11:00 PM' string
        return f"{t.hour:02d}{t.minute:02d}"

    cols, seen = [], {}
    for i in range(raw.shape[1]):
        h, b, t = header[i], band[i], times[i]
        if pd.notna(h) and str(h).strip() in ("D", "D+1", "D+2", "D+3", "D+4"):
            cols.append(f"ship_{pd.Timestamp(t).date()}")
        elif pd.notna(h):
            cols.append(" ".join(str(h).split()))   # collapses newlines too
        elif pd.notna(b) and pd.notna(t):
            dest = "us" if "US" in str(b) else "tx1"
            name = f"slot_{dest}_{slot_time(t)}"
            seen[name] = seen.get(name, 0)
            if seen[name]:
                name += "_" + chr(97 + seen[name])
            seen[f"slot_{dest}_{slot_time(t)}"] += 1
            cols.append(name)
        else:
            cols.append("nan")

    df = raw.iloc[10:].copy()
    df.columns = cols
    df = df.loc[:, [c for c in df.columns if c != "nan"]]
    df = df.dropna(subset=["Customer PN"])

    text_cols = ("BU", "Ship to name", "Ship to", "PO Number", "Customer PN",
                 "Tier1 PN", "Description", "Program", "S/O No")
    for c in df.columns:
        if c not in text_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df.loc[df["kg(PLT)"] == -1, "kg(PLT)"] = float("nan")
    return df
def load_shipping_management() -> pd.DataFrame:
    """OEM-A weekly demand-vs-supply reconciliation (SHIPPING MANAGEMENT).

    Banner sheet, real header on row 5, organised in blocks: stock
    buckets, six Day/Night production pairs labelled D-DAY..D+5 in
    row 4 (renamed prod_d0_day .. prod_d5_night), Shipped QTY and
    BACKLOG, then fourteen weekly (EDI, Shortage) pairs whose Wednesday
    dates sit in row 3 above each EDI column (renamed edi_<date> /
    short_<date>). Column A is a customer-DC group label, forward-
    filled. A handful of Shortage cells are #VALUE! at source -> NaN.

    Cross-sheet check: the weekly EDI total equals DAILY ORDER's daily
    EDI total (19,344 units) - the same order book, binned two ways.
    """
    raw = pd.read_excel(OEM_A_DAILY, sheet_name="SHIPPING MANAGEMENT",
                        header=None)
    labels, weeks, header = raw.iloc[3], raw.iloc[2], raw.iloc[4]

    cols, day_offset = [], None
    for i in range(raw.shape[1]):
        h = str(header[i]).strip() if pd.notna(header[i]) else None
        if h in ("Day", "Night"):
            if pd.notna(labels[i]):            # D-DAY / D+n sits on the Day column
                lab = str(labels[i]).strip()
                day_offset = 0 if lab == "D-DAY" else int(lab[2:])
            cols.append(f"prod_d{day_offset}_{h.lower()}")
        elif h == "EDI":
            cols.append(f"edi_{pd.Timestamp(weeks[i]).date()}")
        elif h == "Shortage":
            cols.append(f"short_{pd.Timestamp(weeks[i - 1]).date()}")
        elif h:
            cols.append(h)
        elif i == 0:
            cols.append("DC group")
        else:
            cols.append("nan")

    df = raw.iloc[5:].copy()
    df.columns = cols
    df = df.loc[:, [c for c in df.columns if c != "nan"]]
    df["DC group"] = df["DC group"].ffill()
    df = df.dropna(subset=["Customer PN"])

    text_cols = ("DC group", "BU", "Ship to name", "Ship to", "PO Number",
                 "Customer PN", "Tier1 PN", "Description", "Program")
    for c in df.columns:
        if c not in text_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df