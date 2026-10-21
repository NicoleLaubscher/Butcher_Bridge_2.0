# Impact, sustainability and scalability

## Table 1. Before/after KPI framework

| Dimension | Baseline input | Proposed/actual output | Interpretation |
|---|---|---|---|
| Cost efficiency | Current product, logistics and handling cost/kg | Recommended and actual landed cost/kg | A positive saving is useful only when service constraints are met. |
| Distribution efficiency | Separate logistics cost/kg and route distance | Coordinated logistics cost/kg and route distance | Reveals whether transport offsets a price-tier benefit. |
| Resource utilisation | Procurement/fulfilment trips | Recommended and actual trips | Measures duplicated activity avoided. |
| Visibility | Separate retailer records | Committed visible kg, tier progress and screened alternatives | Demonstrates integrated information even when aggregation is rejected. |
| Service | Baseline fill and on-time rates | Expected and actual fill/on-time rates | Prevents lower price from masking poorer responsiveness. |

The dashboard calculates baseline versus recommendation from current records and then compares those estimates with post-order actuals. Seed values demonstrate the mechanism; field data is required before claiming real impact.

## Sustainability

- Commercial: platform fees must be included as handling cost and must not eliminate realised savings.
- Operational: explicit windows, commitment deadlines, capacity allocation and exception records support repeatable coordination.
- Technical: blueprints, independent model functions, normalised tables and migrations allow new products, areas and participants without redesigning the decision engine.
- Continuous improvement: immutable evaluation snapshots and actual fulfilment records make estimate-versus-actual review possible.
- Food-chain responsibility: the software supports traceability of decisions but does not replace supplier verification, food-safety or cold-chain controls.

## Scalability boundaries

The exact capacity allocator enumerates feasible whole-order assignments and stops above 100,000 combinations. This is transparent and appropriate for the initial retailer cluster. A future multi-region rollout should replace enumeration with a documented mixed-integer optimisation model while keeping the same API contract and validation tests.

## Professional checks before submission

Confirm figure/table numbering in the final report, proofread names and units, verify every demo screenshot against the current build, and run the institution’s similarity report. Do not state that the Turnitin threshold has been met until the actual report confirms it.

