# Project Plan — Transport Optimisation Pipeline (NSGA-II + GRU Corrector)

Practical component of the MSc dissertation *AI Integration in Supply Chain Digital
Twins* (SCOR Deliver function, automotive Tier 1 export supply chain). The optimiser
makes decisions; the neural network improves the data those decisions consume.

## 1. Scope

- **Core experiment**: the OEM-A outbound pallet scope (two US lanes, CA/TX), where the
  company's incumbent heuristic plan (`SCHEDULED TRUCKS`) exists as a benchmark.
- **Extension study**: the ten-lane bulk-release scope (five US regions, CN, NL).
- **Out of scope**: mode and forwarder selection (empirically degenerate in the data);
  monetary freight rates (absent — stated as exogenous assumptions).

## 2. Architecture

```mermaid
flowchart LR
    A[Raw workbooks<br/>data/raw] --> B[Loaders and<br/>reconciliation]
    B --> C[Model-ready tables<br/>data/processed]
    C --> D[GRU corrector<br/>departure and customs<br/>deviation forecasts]
    C --> E[NSGA-II problem<br/>pymoo]
    D -->|corrected lane<br/>parameters| E
    E --> F[Pareto front vs<br/>incumbent baseline]
```

## 3. Optimisation problem

| Element | Definition | Data source |
|---|---|---|
| Objective: cost | Trucks dispatched per lane-week (rate-weighted) | Pallet pool forecast; Std Pack conversions |
| Objective: time | Weighted earliness against planned receipt dates | Bulk release lane transit times |
| Objective: service | Projected shortage / backorder exposure | Shipping management shortage columns; urgent lists |
| Decision variables | Trucks per lane-week; ship-date shifts (pallet-integral); consolidation; expedite binaries | Release lines; slot timetable |
| Constraints | Truck capacity; pack integrality; inventory balance; production inflow; customs lag; due dates | Inventory, production plan, packaging parameters |

The incumbent `SCHEDULED TRUCKS` plan is evaluated under identical objectives as the
baseline solution every Pareto front is compared against.

## 4. GRU corrector

Trained on the June 2026 export register (the only plan-plus-execution source):
lane-day sequences → forecasts of departure deviation and customs lag, which replace
the deterministic zero-deviation assumptions in the optimiser's parameters.
Honest limits, stated in the dissertation: one month of actuals; the departure signal
is low-variance; a per-lane-mean naïve baseline is part of the evaluation so the
network's added value is measurable. Transit-time (arrival-side) deviation is not
constructible from the available data.

## 5. Repository layout

```
src/data/loaders.py        # bespoke per-sheet extractors
src/data/dimensions.py     # dim_part, dim_lane (hand-curated), dim_calendar
src/data/build.py          # fact tables → data/processed (parquet, gitignored)
src/models/gru_corrector.py
src/optimization/problem.py     # pymoo Problem definition
src/optimization/run_nsga2.py
src/evaluation/baselines.py     # incumbent plan, naïve per-lane mean
tests/                     # reconciliation suite (totals, joins, pack integrality)
notebooks/                 # exploration and figures
data/raw | data/processed  # gitignored
```

## 6. Build phases

1. **Environment** — venv, requirements (pandas, openpyxl, pymoo; DL framework TBD).
2. **Loaders + reconciliation tests** — the hardest data engineering; fail loudly.
3. **Dimensions and facts** — including the manual lane dictionary (documented).
4. **NSGA-II core** — two-lane scope, three objectives, incumbent benchmark.
5. **GRU corrector** — training set, naïve baseline, deviation forecasts.
6. **Integration** — corrected parameters → re-optimise → compare Pareto fronts.
7. **Experiments and write-up assets.**

## 7. Open items for the company

- Actual arrival / receipt (ASN) data — would restore arrival-side correction.
- Additional monthly export registers and planning-workbook snapshots.
- Confirmation of the 210-pallet truck capacity constant (physically implausible
  for a single trailer; possibly pooled weekly capacity).