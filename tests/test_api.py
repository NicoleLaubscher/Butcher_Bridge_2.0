from datetime import date, timedelta

from app.db_models import Scenario
from app.extensions import db


def test_login_and_dashboard_smoke(client, auth):
    response = auth.login()
    assert response.status_code == 302
    page = client.get("/")
    assert page.status_code == 200
    assert b"Test the decision" in page.data
    assert b"Supplier feasibility" in page.data


def test_all_four_exam_scenarios_make_expected_decisions(client, auth):
    auth.login()
    expected = {
        1: "ACCEPT_AGGREGATION",
        2: "REJECT_AGGREGATION",
        3: "ACCEPT_COORDINATED_SPLIT",
        4: "ACCEPT_COORDINATED_SPLIT",
    }
    for scenario_id, decision in expected.items():
        response = client.post(f"/api/scenarios/{scenario_id}/evaluate")
        assert response.status_code == 200
        assert response.get_json()["decision"] == decision


def test_demand_endpoint_validates_and_paginates(client, auth):
    auth.login()
    invalid = client.post("/api/demands", json={"scenario_id": 1})
    assert invalid.status_code == 400
    listing = client.get("/api/demands?scenario_id=1&page=1&per_page=2")
    payload = listing.get_json()
    assert listing.status_code == 200
    assert len(payload["items"]) == 2
    assert payload["pagination"]["total"] == 6


def test_retailer_cannot_create_supplier_quote(client, auth):
    auth.login("retailer@butcherbridge.local", "retailer-demo")
    response = client.post("/api/quotes", json={})
    assert response.status_code == 403


def test_withdrawal_is_locked_after_deadline(app, client, auth):
    auth.login()
    with app.app_context():
        scenario = db.session.get(Scenario, 1)
        scenario.commitment_deadline = date.today() - timedelta(days=1)
        demand_id = scenario.demands[0].id
        db.session.commit()
    response = client.patch(f"/api/demands/{demand_id}/status", json={"status": "withdrawn"})
    assert response.status_code == 409
    assert "locked" in response.get_json()["error"].lower()


def test_post_order_performance_calculation(client, auth):
    auth.login()
    payload = {
        "scenario_id": 1,
        "supplier_name": "Mzansi Beef Co.",
        "ordered_quantity_kg": 100,
        "delivered_quantity_kg": 95,
        "actual_total_cost": 7600,
        "due_date": "2026-11-01",
        "delivered_date": "2026-11-02",
        "actual_logistics_cost": 600,
        "actual_trips": 1,
        "actual_distance_km": 78,
    }
    response = client.post("/api/performance", json=payload)
    assert response.status_code == 201
    assert response.get_json()["fill_rate"] == 0.95
    assert response.get_json()["on_time"] is False
    summary = client.get("/api/scenarios/1/performance").get_json()
    assert summary["actual_cost_per_kg"] == 80

