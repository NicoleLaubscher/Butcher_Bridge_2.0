# Lecturer feedback traceability

| Lecturer priority | Implemented evidence |
|---|---|
| Validate the logic using primary data | Primary-data fields are available in the retailer, quote and actual-performance forms. Demo values are explicitly labelled as non-primary data. |
| Establish actual retailer quantity and frequency | `quantity_kg` and `orders_per_month` are stored per demand. |
| Capture procurement and logistics cost/kg | Baseline product price, logistics and handling are stored separately and combined into baseline landed cost/kg. |
| Measure trips and distance | Baseline and actual trips/distance are stored and compared. |
| Capture tiers, lead time, fill and on-time rates | Normalised `price_tiers`, quote lead time/service estimates and actual fulfilment records are implemented. |
| Define compatible demand | Same product, committed status, submission deadline and configurable required-date window are enforced. |
| Define order window | Each scenario has open, close and commitment-deadline dates. |
| Define supplier-capacity allocation | Exact assignment keeps retailer orders whole and caps total assigned volume per supplier. |
| Define tier qualification | Highest minimum tier reached by confirmed assigned kilograms is used. |
| Define commitment/withdrawal | Pending/withdrawn demand is excluded; withdrawal locks after the commitment deadline. |
| Define shared logistics allocation | Fixed fulfilment and handling are allocated in proportion to retailer kilograms. |
| Reject poor aggregation | Scenario 2 returns `REJECT_AGGREGATION` because individual procurement is equal/lower cost. |
| Test realistic scenarios | Four seeded scenarios cover success, rejection, capacity conflict and coordinated fulfilment. |
| Compare baseline quantitatively | KPI cards and tables show baseline cost, logistics, trips, distance, fill and on-time versus recommendation and actuals. |
| Focus on defensible decisions | The recommendation includes rationale, constraint failures, rules, allocations and a saved input/result snapshot. |
| Improve numbering and conciseness | Documentation uses sequential figure/table labels and separates technical evidence into short focused files. |

