# System design pack

## Figure 1. ButcherBridge application architecture

```mermaid
flowchart TD
    U["Retailer, supplier and admin"] --> FE["Jinja HTML + CSS + JavaScript"]
    FE --> API["Flask blueprints and JSON API"]
    API --> SVC["Scenario service"]
    SVC --> ENG["Standalone Python decision model"]
    API --> DB["MySQL via SQLAlchemy"]
    DB --> SVC
```

The decision model imports neither Flask nor database code. Routes validate requests, services adapt relational records into plain dictionaries, and the model returns a serialisable decision result.

## Figure 2. Normalised entity-relationship diagram

```mermaid
erDiagram
    USER ||--o{ EVALUATION_RUN : executes
    SCENARIO ||--o{ DEMAND : contains
    RETAILER ||--o{ DEMAND : submits
    SCENARIO ||--o{ SUPPLIER_QUOTE : compares
    SUPPLIER ||--o{ SUPPLIER_QUOTE : provides
    SUPPLIER_QUOTE ||--o{ PRICE_TIER : defines
    SUPPLIER_QUOTE ||--o{ SERVICE_AREA : covers
    SCENARIO ||--o{ EVALUATION_RUN : records
    SCENARIO ||--o{ FULFILMENT_RECORD : measures
```

## Main end-to-end flows

1. Retailer baseline and demand: authenticated user captures quantity, date, area and actual current KPIs; the API validates and persists a demand commitment.
2. Supplier quotation: authorised supplier/admin captures tiers, capacity, areas, lead time and fulfilment/service estimates; the API normalises tiers and areas into child tables.
3. Decision evaluation: scenario service loads inputs, the pure Python engine filters demand, screens constraints, allocates capacity, calculates alternatives and persists the result snapshot.
4. Performance feedback: completed quantities, dates, cost, logistics, trips and distance are recorded; actual cost/kg, fill rate and on-time performance are calculated.

