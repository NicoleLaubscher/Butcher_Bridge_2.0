# Calculation and scenario validation report

## 1. Hand-calculated landed-cost test

Known inputs: 100 kg, product price R10/kg, fixed fulfilment R100, variable fulfilment R2/kg and handling R50.

```text
Total = (R10 × 100) + R100 + (R2 × 100) + R50 = R1 350
Landed cost/kg = R1 350 / 100 = R13.50/kg
```

`tests/test_decision_model.py::test_landed_cost_matches_hand_calculation` verifies exactly R13.50/kg and the proportional shared-cost allocation.

## 2. Seeded scenario results

| Scenario | Recorded decision | Recommended cost/kg | Individual cost/kg | Key evidence |
|---|---|---:|---:|---|
| Successful aggregation | `ACCEPT_AGGREGATION` | R73.3456 | R89.5982 | 285 kg qualifies for Mzansi’s 280 kg tier. |
| Aggregation rejected | `REJECT_AGGREGATION` | R74.1000 | R74.1000 | Coordinated/local outcome is not better than individual; national delivery is expensive. |
| Supplier-capacity conflict | `ACCEPT_COORDINATED_SPLIT` | R71.0875 | R79.0500 | Cheapest suppliers each fail the full-group capacity check; exact split is lower cost. |
| Separate vs coordinated fulfilment | `ACCEPT_COORDINATED_SPLIT` | R74.6778 | R81.4556 | Area-limited suppliers share charges across assigned retailers. |

The model uses full-precision values internally and rounds display fields only after calculation.

## 3. Automated coverage

The included suite contains 11 tests covering:

- price-tier boundaries;
- hand-calculated landed cost;
- committed/pending demand filtering;
- supplier-capacity failure;
- no-compatible-demand handling;
- authentication and HTML rendering;
- all four expected decisions;
- pagination and required-field validation;
- role-based quote control;
- post-deadline withdrawal locking; and
- actual fill rate, on-time status and actual cost/kg.

Run `python -m pytest`. The packaged run passed all 11 tests.

## 4. Primary-data limitation

The seed values validate program behaviour and decision branches; they are not presented as field-study results. For the final examination, replace them with observed retailer records, dated supplier quotations and completed-order evidence, retain source dates, and rerun the same four cases.

