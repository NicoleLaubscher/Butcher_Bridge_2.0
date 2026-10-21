# BFB 321 development-guide compliance matrix

| Guide deliverable | ButcherBridge evidence |
|---|---|
| Responsive HTML/CSS frontend | Jinja templates, responsive custom CSS, accessible labels/tables, empty/error/loading states and client validation. |
| Reusable components | `base.html`, shared navigation, cards, tables, statuses and form styles. |
| Standalone Python supply-chain model | `models/decision_model.py` has no Flask/database imports and documents formulas/assumptions. |
| Known-answer unit tests | `tests/test_decision_model.py` validates R13.50/kg by hand calculation plus tiers and constraints. |
| Normalised MySQL data model | `schema.sql`, SQLAlchemy models and Figure 2 ERD; price tiers and areas are child tables. |
| Constraints, audit fields and indexes | Primary/foreign/unique/check constraints, `created_at`/`updated_at`, and scenario/product/status indexes. |
| Migration and realistic seed | Flask-Migrate/Alembic initial migration and `seed.py` with four evaluation scenarios. |
| REST endpoints and JSON schemas | Flask API blueprint, `app/schemas.py`, `docs/openapi.json` and README endpoint table. |
| Authentication and roles | Flask-Login sessions, admin/retailer/supplier roles, password hashes and mutation authorisation. |
| Pagination, filtering and validation | Demand/quote pagination and filters; central request validation and JSON errors. |
| Central logging/error handling | `app/errors.py` and configured Python logging. |
| At least three end-to-end flows | Demand/commitment; supplier quote; evaluation; actual-performance recording. |
| KPIs on frontend | Cost/kg, logistics/kg, trips, distance, fill, on-time, savings, visibility and alternatives. |
| Deployment artefacts | `.env.example`, Docker MySQL, Gunicorn entrypoint, migrations, Windows scripts and deployment runbook. |
| Impact/scalability documentation | `IMPACT_AND_SUSTAINABILITY.md` plus before/after KPI framework. |
| Professional system design pack | Architecture diagram, ERD, OpenAPI contract, validation report and traceability matrix. |

