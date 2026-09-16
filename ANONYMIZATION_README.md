# Anonymised Supply Chain Dataset: Scheme Documentation

Research dataset for MSc dissertation: AI integration in supply chain digital twins
(SCOR Deliver function, automotive Tier 1 export supply chain). All identifying
information has been consistently pseudonymised across the five files; joins between
files remain valid.

## Files

| File | Content |
|---|---|
| `JUNE_2026_EXPORT_ANON.xlsx` | June 2026 export shipments (SAP extract): invoices, customs declarations, B/L, materials, quantities, scaled amounts |
| `OEM-A_AS_DAILY_SHIPPING_MGMT_20260225_ANON.xlsx` | Daily aftermarket shipping management for OEM-A: orders, shipping plan, inventory (WIP/FG), production plan, daily POs, forecast, cross-reference |
| `OEM-B_AS_WEEKLY_SHIPPING_MGMT_20260223_ANON.xlsx` | Weekly aftermarket shipping management for OEM-B: shipping, coverage, urgent orders, boxes, inventory, production plan, weekly POs, cross-reference |
| `PALLET_POOL_FORECAST_FROM_WK19_2026_ANON.xlsx` | Pallet pool forecast and scheduled trucks from week 19, 2026 |
| `PART_RELEASE_DATA_BULK_20260227_ANON.xlsx` | Customer part release data (EDI), Feb 2026 |

## Anonymisation scheme

- **Tier 1 supplier** → `Tier1 Automotive` / prefix `T1M_`; plants → `Tier1 <Function> Plant (<state>)`, Korean plants → `Plant A/B/C (KR)`
- **Customers** → `OEM-A` … `OEM-H`, `AFTMKT-A` (aftermarket), `LSP-A` (logistics provider), `Supplier-A`; customer plant cities → coarse region codes (`MI1`, `TX1`, `NL1` …)
- **Addresses** → `OEM-A DC, <region>, <country>` / `Customer DC n (<state>, US)`. Country and coarse region preserved for transit-time realism; street-level detail removed
- **People** → generic names (John Smith, Jane Doe, …); emails → `planner.x@oem-a.example`; employee/SAP IDs remapped
- **Part numbers** → consistently remapped, format-preserving: customer PNs `91xxxxx-NN-R` (revision suffix kept), Tier 1 PNs `SXnnnAnnnn`, 8-digit customer codes `9xxxxxxx`, `AAxA-9xxxx-XX`
- **Part descriptions** → functional content kept (e.g. damper, caliper, gear assembly); vehicle program codes replaced by `VPnn` tokens
- **Documents** → PO, invoice, B/L, customs declaration, delivery, SO numbers, and UUIDs remapped format-preserving and consistently across files
- **Monetary values** → multiplied by an undisclosed constant factor (ratios and structure preserved; absolute prices are not real)
- **Dates and quantities** → unmodified (time-series integrity)
- **Korean and Spanish text** → translated to English
- **Workbook metadata** → scrubbed; formulas flattened to values; autofilters removed

## Privacy notes for repository use

- `PRIVATE_mapping_key_DO_NOT_COMMIT.json` reverses every mapping and contains the money
  scale factor. **It must never be committed, shared, or uploaded.** Add it to `.gitignore`.
- The anonymised files are intended for research reproducibility. Absolute monetary values
  are deliberately not real; use them only for relative/structural analysis.
