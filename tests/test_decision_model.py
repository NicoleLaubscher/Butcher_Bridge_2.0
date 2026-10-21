from datetime import date

import pytest

from models.decision_model import DecisionModelError, evaluate_scenario, qualifying_tier


def scenario():
    return {
        "product": "Beef",
        "window_close": "2026-10-24",
        "compatibility_days": 2,
        "minimum_fill_rate": 0.95,
        "minimum_on_time_rate": 0.95,
    }


def demand(name="Shop A", quantity=100, area="Mamelodi", status="committed"):
    return {
        "id": 1,
        "retailer_name": name,
        "product": "Beef",
        "quantity_kg": quantity,
        "area": area,
        "required_date": "2026-10-30",
        "submitted_date": "2026-10-22",
        "status": status,
        "baseline_price_per_kg": 16,
        "baseline_logistics_cost": 100,
        "baseline_handling_cost": 50,
        "baseline_distance_km": 30,
        "baseline_trips": 1,
        "baseline_fill_rate": 0.9,
        "baseline_on_time_rate": 0.88,
        "orders_per_month": 4,
        "individual_procurement_cost": 80,
    }


def quote(name="Supplier A", capacity=500, areas=None, fixed=100, price=10):
    return {
        "id": name,
        "supplier_id": 1,
        "supplier_name": name,
        "product": "Beef",
        "capacity_kg": capacity,
        "lead_time_days": 2,
        "fixed_fulfilment_cost": fixed,
        "variable_fulfilment_per_kg": 2,
        "handling_cost": 50,
        "route_distance_km": 20,
        "expected_fill_rate": 0.98,
        "expected_on_time_rate": 0.97,
        "service_areas": areas or ["All"],
        "price_tiers": [{"minimum_kg": 0, "price_per_kg": price}],
    }


def test_highest_qualified_price_tier_is_used():
    tiers = [
        {"minimum_kg": 0, "price_per_kg": 80},
        {"minimum_kg": 100, "price_per_kg": 74},
        {"minimum_kg": 250, "price_per_kg": 69},
    ]
    assert qualifying_tier(tiers, 249)["price_per_kg"] == 74
    assert qualifying_tier(tiers, 250)["price_per_kg"] == 69


def test_landed_cost_matches_hand_calculation():
    result = evaluate_scenario([demand()], [quote()], scenario())
    option = result["collective_options"][0]
    # (R10*100kg + R100 fixed + R2*100 variable + R50 handling) / 100kg
    assert option["landed_cost_per_kg"] == pytest.approx(13.5)
    assert option["retailer_allocations"][0]["allocated_shared_cost"] == pytest.approx(150)


def test_pending_demand_is_excluded_from_group_quantity():
    result = evaluate_scenario([demand(), demand("Shop B", 40, status="pending")], [quote()], scenario())
    assert result["compatible_demand"]["quantity_kg"] == 100
    assert result["compatible_demand"]["excluded"][0]["reason"] == "status is pending"


def test_supplier_capacity_failure_is_reported():
    result = evaluate_scenario([demand(quantity=100)], [quote(capacity=90)], scenario())
    assert result["decision"] == "NO_FEASIBLE_OPTION"
    assert "capacity shortfall" in result["supplier_feasibility"][0]["reasons"][0]


def test_empty_compatible_group_is_rejected():
    with pytest.raises(DecisionModelError, match="No committed compatible demand"):
        evaluate_scenario([demand(status="withdrawn")], [quote()], scenario())

