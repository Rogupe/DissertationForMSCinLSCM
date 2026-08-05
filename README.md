# sc-transport-optimization

Multi-objective transport optimisation for the SCOR "Deliver" function of an automotive Tier 1 export supply chain. Developed as the practical component of an MSc dissertation in Logistics and Supply Chain Management at the University of Hull, investigating AI integration in supply chain digital twins.

## Approach

The pipeline combines two complementary components with a deliberate division of labour — the optimiser makes decisions, while the neural network improves the data those decisions consume:

- **NSGA-II** (via [pymoo](https://pymoo.org/)) — multi-objective evolutionary optimisation searching trade-offs between cost, time and service level in outbound transport decisions.
- **GRU corrector** — a recurrent neural network that learns the gap between deterministic model assumptions and real operational data (e.g. transit-time deviations), improving the inputs supplied to the optimiser.

The work is framed within the SCOR model and grounded in the digital twin and human-in-the-loop governance literature.

## Data

Experiments use an anonymised June 2026 export dataset from an automotive Tier 1 supply chain, obtained through industry practitioners. The dataset is **not** included in this repository and is excluded via `.gitignore`; only synthetic samples or schema documentation may be committed. Nothing identifying the company, plants, customers, lanes or practitioners appears in this repository.

## Status

The pipeline is under active development. Full experiments, results analysis and the dissertation write-up are forthcoming (completion: December 2026).

## Context

MSc in Logistics and Supply Chain Management, University of Hull, undertaken as a dual degree alongside Ingeniería Mecatrónica at Tecnológico de Monterrey.
