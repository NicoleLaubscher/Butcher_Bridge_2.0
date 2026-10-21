# ButcherBridge — Flask/MySQL decision-support application

ButcherBridge is a private supply-chain decision-support prototype for independent township meat retailers. It aggregates only compatible, committed demand; tests supplier product, capacity, price-tier, lead-time, service-area and service-performance constraints; calculates total landed procurement cost per kilogram; and compares individual purchasing, one-supplier aggregation and coordinated multi-supplier fulfilment.

The interface keeps the green/cream ButcherBridge visual identity of the earlier prototype, but the calculations are now performed by a standalone, tested Python model behind a Flask REST API and a normalised MySQL database.

## Marking-guide stack

- Frontend: Jinja2 HTML, responsive CSS and vanilla JavaScript
- Backend/API: Python 3.12 and Flask blueprints
- Database: MySQL 8 through SQLAlchemy/PyMySQL, with Flask-Migrate/Alembic
- Authentication: Flask-Login sessions, roles and CSRF checks
- Testing: pytest unit and integration tests
- Operations: environment configurations, migrations, seed data, Gunicorn entrypoint and logging

SQLite is included **only as an offline classroom/demo fallback**. The assessed database configuration in `.env.example`, `schema.sql`, migrations and Docker Compose is MySQL.

## Fastest setup on Windows (no npm required)

1. Install [Python 3](https://www.python.org/downloads/) and select **Add Python to PATH** during installation.
2. Extract the ZIP.
3. Open the extracted `butcherbridge-flask` folder in VS Code.
4. Double-click `setup_demo_windows.bat` once.
5. Double-click `run_windows.bat`.
6. Open <http://127.0.0.1:5000>.

Demo administrator login:

```text
Email: admin@butcherbridge.local
Password: butcherbridge
```

This project does not use Node or npm. The earlier `npm is not recognized` error is therefore no longer relevant.

## Terminal setup on Windows

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.demo.example .env
python seed.py --reset
python run.py
```

If PowerShell blocks activation, run this once in the current terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Required MySQL setup

The simplest reproducible MySQL option is Docker Desktop:

```powershell
docker compose up -d mysql
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Then change the `DATABASE_URL` line in `.env` to:

```text
DATABASE_URL=mysql+pymysql://butcherbridge:butcherbridge-dev@127.0.0.1:3306/butcherbridge
```

Apply the migration and load the examination scenarios:

```powershell
$env:FLASK_APP="wsgi:app"
flask db upgrade
python seed.py
python run.py
```

For a separately installed MySQL 8 server, create a database/user, update `DATABASE_URL`, and run the same migration and seed commands. `schema.sql` is supplied as an inspectable schema deliverable; migrations are the preferred operational path.

## Test the application

```powershell
python -m pytest
```

The suite validates the formula with a hand-calculated known answer, tier qualification, commitment filtering, supplier capacity blocking, role control, pagination, withdrawal locking, post-order KPIs and all four lecturer-requested scenarios.

## Four examination scenarios

| No. | Scenario | Expected result |
|---:|---|---|
| 1 | Successful aggregation | Accept one-supplier aggregation |
| 2 | Aggregation rejected | Keep individual procurement |
| 3 | Supplier-capacity conflict | Accept a coordinated capacity split |
| 4 | Separate vs coordinated fulfilment | Accept coordinated multi-supplier fulfilment |

The values are realistic demonstrations, not claimed primary research. Replace them through the interface/API with verified retailer and supplier observations for the final examination.

## Explicit decision rules

1. Only `committed` demand submitted by the order-window close is counted.
2. Demand must use the same product and required dates must fall inside the scenario’s compatibility window.
3. A supplier assignment must cover each area, carry the assigned kilograms, meet each required date, provide a qualifying price tier and pass the fill/on-time thresholds.
4. The highest price tier whose minimum is reached by confirmed kilograms is used.
5. Capacity allocation keeps each retailer order whole; it never splits one retailer demand across suppliers.
6. Shared fixed logistics and handling cost is allocated by kilograms.
7. Aggregation is accepted only if it is feasible **and** cheaper than the best feasible individual option. An equal/worse group result is rejected.
8. Withdrawals after the commitment deadline are locked and require administrator exception handling.

## Repository structure

```text
app/                 Flask factory, blueprints, DB models, validation, services
models/              Framework-independent supply-chain decision model
templates/           Jinja2 pages
static/              CSS and JavaScript
migrations/          Alembic/Flask-Migrate migration history
tests/               Unit and integration tests
docs/                ERD, architecture, API, validation and evaluation documents
schema.sql            MySQL schema deliverable
seed.py               Realistic demo and examination scenarios
wsgi.py               Gunicorn production entrypoint
```

## REST endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/api/scenarios` | List or create scenarios |
| GET | `/api/scenarios/{id}` | Scenario inputs |
| POST | `/api/scenarios/{id}/evaluate` | Run and save a comparison |
| GET/POST | `/api/demands` | Filter/paginate or create demand |
| PATCH | `/api/demands/{id}/status` | Commit or withdraw demand |
| GET/POST | `/api/quotes` | Filter/paginate or create quotations |
| POST | `/api/performance` | Record actual completed-order results |
| GET | `/api/scenarios/{id}/performance` | Actual KPI summary |

See `docs/openapi.json` for the machine-readable contract.

## Production run

Set a strong `SECRET_KEY` and MySQL `DATABASE_URL`, run `flask db upgrade`, then start behind a reverse proxy:

```bash
gunicorn --workers 3 --bind 127.0.0.1:8000 wsgi:app
```

Do not commit `.env`, real participant names, contact details or commercial quotations. Keep the GitHub repository private unless every data owner has approved publication.

