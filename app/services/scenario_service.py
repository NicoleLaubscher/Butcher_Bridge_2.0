"""Database-to-decision-model adapters."""

from __future__ import annotations

import json

from flask_login import current_user

from models.decision_model import evaluate_scenario
from ..db_models import Demand, EvaluationRun, Scenario, SupplierQuote
from ..extensions import db


def scenario_dict(scenario: Scenario) -> dict:
    return {
        "id": scenario.id,
        "name": scenario.name,
        "code": scenario.code,
        "description": scenario.description,
        "expected_outcome": scenario.expected_outcome,
        "product": scenario.product,
        "window_open": scenario.window_open.isoformat(),
        "window_close": scenario.window_close.isoformat(),
        "commitment_deadline": scenario.commitment_deadline.isoformat(),
        "compatibility_days": scenario.compatibility_days,
        "minimum_fill_rate": scenario.minimum_fill_rate,
        "minimum_on_time_rate": scenario.minimum_on_time_rate,
        "status": scenario.status,
    }


def demand_dict(demand: Demand) -> dict:
    return {
        "id": demand.id,
        "scenario_id": demand.scenario_id,
        "retailer_id": demand.retailer_id,
        "retailer_name": demand.retailer.name,
        "area": demand.retailer.area,
        "product": demand.product,
        "quantity_kg": demand.quantity_kg,
        "required_date": demand.required_date.isoformat(),
        "submitted_date": demand.submitted_date.isoformat(),
        "status": demand.status,
        "baseline_price_per_kg": demand.baseline_price_per_kg,
        "baseline_logistics_cost": demand.baseline_logistics_cost,
        "baseline_handling_cost": demand.baseline_handling_cost,
        "baseline_distance_km": demand.baseline_distance_km,
        "baseline_trips": demand.baseline_trips,
        "baseline_fill_rate": demand.baseline_fill_rate,
        "baseline_on_time_rate": demand.baseline_on_time_rate,
        "orders_per_month": demand.orders_per_month,
        "individual_procurement_cost": demand.individual_procurement_cost,
    }


def quote_dict(quote: SupplierQuote) -> dict:
    return {
        "id": quote.id,
        "scenario_id": quote.scenario_id,
        "supplier_id": quote.supplier_id,
        "supplier_name": quote.supplier.name,
        "verified": quote.supplier.verified,
        "product": quote.product,
        "capacity_kg": quote.capacity_kg,
        "lead_time_days": quote.lead_time_days,
        "fixed_fulfilment_cost": quote.fixed_fulfilment_cost,
        "variable_fulfilment_per_kg": quote.variable_fulfilment_per_kg,
        "handling_cost": quote.handling_cost,
        "route_distance_km": quote.route_distance_km,
        "expected_fill_rate": quote.expected_fill_rate,
        "expected_on_time_rate": quote.expected_on_time_rate,
        "fulfilment_mode": quote.fulfilment_mode,
        "service_areas": [area.area for area in quote.service_areas],
        "price_tiers": [
            {"minimum_kg": tier.minimum_kg, "price_per_kg": tier.price_per_kg}
            for tier in quote.price_tiers
        ],
    }


def full_scenario(scenario: Scenario) -> dict:
    return {
        "scenario": scenario_dict(scenario),
        "demands": [demand_dict(demand) for demand in scenario.demands],
        "quotes": [quote_dict(quote) for quote in scenario.quotes],
    }


def run_evaluation(scenario: Scenario, save: bool = True) -> dict:
    payload = full_scenario(scenario)
    result = evaluate_scenario(payload["demands"], payload["quotes"], payload["scenario"])
    if save:
        run = EvaluationRun(
            scenario_id=scenario.id,
            run_by_user_id=current_user.id if getattr(current_user, "is_authenticated", False) else None,
            decision=result["decision"],
            input_snapshot=json.dumps(payload, sort_keys=True),
            result_snapshot=json.dumps(result, sort_keys=True),
        )
        db.session.add(run)
        db.session.commit()
        result["evaluation_run_id"] = run.id
    return result

