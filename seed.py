"""Populate MySQL (or the optional SQLite demo) with four exam scenarios."""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from app import create_app
from app.db_models import Demand, PriceTier, Retailer, Scenario, Supplier, SupplierQuote, SupplierServiceArea, User
from app.extensions import db


def seed_database(reset: bool = False) -> None:
    if reset:
        db.drop_all()
    db.create_all()
    if db.session.execute(db.select(Scenario)).first():
        print("Seed skipped: scenarios already exist. Use --reset to replace demo data.")
        return

    admin = User(name="ButcherBridge Administrator", email="admin@butcherbridge.local", role="admin")
    admin.set_password("butcherbridge")
    retailer_user = User(name="Retailer Demo", email="retailer@butcherbridge.local", role="retailer")
    retailer_user.set_password("retailer-demo")
    supplier_user = User(name="Supplier Demo", email="supplier@butcherbridge.local", role="supplier")
    supplier_user.set_password("supplier-demo")
    db.session.add_all([admin, retailer_user, supplier_user])

    today = date.today()
    scenarios = [
        Scenario(
            name="Scenario 1 — Successful aggregation",
            code="successful-aggregation",
            description="Five compatible retailer commitments reach a lower supplier price tier and reduce shared logistics cost.",
            expected_outcome="Accept aggregation",
            product="Beef mixed cuts",
            window_open=today,
            window_close=today + timedelta(days=3),
            commitment_deadline=today + timedelta(days=3),
            compatibility_days=3,
            minimum_fill_rate=0.95,
            minimum_on_time_rate=0.94,
        ),
        Scenario(
            name="Scenario 2 — Aggregation rejected",
            code="aggregation-rejected",
            description="A national group option carries a high fixed delivery charge; two local individual options provide an equal or lower total-cost outcome.",
            expected_outcome="Reject aggregation",
            product="Chicken portions",
            window_open=today,
            window_close=today + timedelta(days=2),
            commitment_deadline=today + timedelta(days=2),
            compatibility_days=2,
            minimum_fill_rate=0.95,
            minimum_on_time_rate=0.95,
        ),
        Scenario(
            name="Scenario 3 — Supplier-capacity conflict",
            code="capacity-conflict",
            description="The two lowest-cost suppliers cannot carry the full group alone. Exact allocation tests a coordinated capacity split against a feasible national quote.",
            expected_outcome="Coordinate capacity split",
            product="Beef forequarter",
            window_open=today,
            window_close=today + timedelta(days=3),
            commitment_deadline=today + timedelta(days=3),
            compatibility_days=2,
            minimum_fill_rate=0.94,
            minimum_on_time_rate=0.94,
        ),
        Scenario(
            name="Scenario 4 — Separate vs coordinated fulfilment",
            code="fulfilment-comparison",
            description="Area-limited suppliers are compared as separate retailer deliveries versus one coordinated allocation that shares fulfilment charges.",
            expected_outcome="Coordinate fulfilment",
            product="Pork braai packs",
            window_open=today,
            window_close=today + timedelta(days=3),
            commitment_deadline=today + timedelta(days=3),
            compatibility_days=3,
            minimum_fill_rate=0.95,
            minimum_on_time_rate=0.94,
        ),
    ]
    db.session.add_all(scenarios)
    db.session.flush()

    retailer_cache: dict[tuple[str, str], Retailer] = {}

    def add_demand(
        scenario: Scenario,
        retailer_name: str,
        area: str,
        quantity: float,
        due_offset: int,
        baseline_price: float,
        logistics: float,
        distance: float,
        trips: int = 1,
        fill: float = 0.93,
        on_time: float = 0.9,
        admin: float = 120,
        status: str = "committed",
    ) -> None:
        key = (retailer_name, area)
        retailer = retailer_cache.get(key)
        if retailer is None:
            retailer = Retailer(name=retailer_name, area=area)
            retailer_cache[key] = retailer
            db.session.add(retailer)
        db.session.add(
            Demand(
                scenario=scenario,
                retailer=retailer,
                product=scenario.product,
                quantity_kg=quantity,
                required_date=scenario.window_close + timedelta(days=due_offset),
                submitted_date=scenario.window_open,
                status=status,
                baseline_price_per_kg=baseline_price,
                baseline_logistics_cost=logistics,
                baseline_handling_cost=60,
                baseline_distance_km=distance,
                baseline_trips=trips,
                baseline_fill_rate=fill,
                baseline_on_time_rate=on_time,
                orders_per_month=4,
                individual_procurement_cost=admin,
            )
        )

    for values in [
        ("Mamelodi Market", "Mamelodi", 80, 5, 80, 460, 42),
        ("Atteridgeville Foods", "Atteridgeville", 65, 6, 81, 420, 36),
        ("Soshanguve Butchery", "Soshanguve", 60, 7, 79, 510, 48),
        ("Hammanskraal Foods", "Hammanskraal", 45, 7, 82, 620, 64),
        ("Eersterust Butchery", "Eersterust", 35, 6, 80, 360, 31),
    ]:
        add_demand(scenarios[0], *values)
    add_demand(scenarios[0], "Late Pending Shop", "Mamelodi", 25, 5, 80, 300, 25, status="pending")

    add_demand(scenarios[1], "Eastside Chicken", "Mamelodi", 40, 4, 77, 110, 18, admin=0)
    add_demand(scenarios[1], "Westside Chicken", "Atteridgeville", 35, 4, 76, 95, 16, admin=0)

    for name, area in [
        ("North Market", "Soshanguve"),
        ("Central Meats", "Mamelodi"),
        ("West Butchery", "Atteridgeville"),
        ("Township Foods", "Eersterust"),
    ]:
        add_demand(scenarios[2], name, area, 80, 5, 82, 360, 34, admin=140)

    add_demand(scenarios[3], "Mamelodi Pork", "Mamelodi", 60, 5, 80, 310, 28, admin=100)
    add_demand(scenarios[3], "Soshanguve Grill", "Soshanguve", 60, 6, 81, 330, 31, admin=100)
    add_demand(scenarios[3], "Hammanskraal Braai", "Hammanskraal", 60, 6, 82, 390, 43, admin=100)

    supplier_cache: dict[str, Supplier] = {}

    def add_quote(
        scenario: Scenario,
        name: str,
        capacity: float,
        lead: int,
        fixed: float,
        variable: float,
        handling: float,
        distance: float,
        areas: list[str],
        tiers: list[tuple[float, float]],
        fill: float = 0.98,
        on_time: float = 0.97,
    ) -> None:
        supplier = supplier_cache.get(name)
        if supplier is None:
            supplier = Supplier(name=name, verified=True)
            supplier_cache[name] = supplier
            db.session.add(supplier)
        quote = SupplierQuote(
            scenario=scenario,
            supplier=supplier,
            product=scenario.product,
            capacity_kg=capacity,
            lead_time_days=lead,
            fixed_fulfilment_cost=fixed,
            variable_fulfilment_per_kg=variable,
            handling_cost=handling,
            route_distance_km=distance,
            expected_fill_rate=fill,
            expected_on_time_rate=on_time,
            fulfilment_mode="delivery",
        )
        quote.service_areas = [SupplierServiceArea(area=area) for area in areas]
        quote.price_tiers = [PriceTier(minimum_kg=minimum, price_per_kg=price) for minimum, price in tiers]
        db.session.add(quote)

    add_quote(scenarios[0], "Mzansi Beef Co.", 400, 3, 520, 1.10, 120, 78, ["All"], [(0, 78), (150, 74), (280, 70)])
    add_quote(scenarios[0], "Ubuntu Fresh Meats", 250, 2, 380, 1.40, 100, 66, ["Mamelodi", "Atteridgeville", "Soshanguve", "Eersterust"], [(0, 77), (180, 72)])
    add_quote(scenarios[0], "City Abattoir", 350, 5, 450, 0.85, 160, 91, ["All"], [(0, 80), (200, 71.5), (300, 68)])

    add_quote(scenarios[1], "National Poultry Logistics", 300, 2, 1200, 0.50, 100, 92, ["All"], [(0, 69)])
    add_quote(scenarios[1], "Mamelodi Poultry", 60, 1, 50, 0.70, 20, 18, ["Mamelodi"], [(0, 72)])
    add_quote(scenarios[1], "Atteridgeville Chicken", 60, 1, 50, 0.70, 20, 16, ["Atteridgeville"], [(0, 71)])

    add_quote(scenarios[2], "Budget Beef North", 160, 2, 200, 0.80, 80, 44, ["All"], [(0, 73), (100, 68)])
    add_quote(scenarios[2], "Budget Beef South", 160, 3, 220, 0.75, 80, 48, ["All"], [(0, 74), (100, 69)])
    add_quote(scenarios[2], "National Beef Reserve", 500, 2, 300, 0.90, 100, 88, ["All"], [(0, 75), (300, 74)])

    add_quote(scenarios[3], "Northern Pork Hub", 120, 2, 260, 0.90, 60, 48, ["Mamelodi", "Soshanguve"], [(0, 75), (100, 70)])
    add_quote(scenarios[3], "Hammanskraal Pork Co.", 120, 2, 240, 0.90, 60, 43, ["Hammanskraal"], [(0, 71)])
    add_quote(scenarios[3], "Gauteng Pork Network", 300, 3, 250, 1.00, 90, 96, ["All"], [(0, 76), (150, 75)])

    db.session.commit()
    print("Seed complete: 4 scenarios, 3 demo users and realistic baseline/quotation data created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables before seeding.")
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        seed_database(reset=args.reset)

