"""Version-one REST API for the three assessed end-to-end flows.

Flows:
1. Retailer demand capture and commitment/withdrawal.
2. Supplier quotation, tier, capacity and service-area maintenance.
3. Scenario evaluation, recommendation and actual-performance recording.
"""

from __future__ import annotations

from datetime import date, datetime
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from models.decision_model import DecisionModelError
from ..db_models import (
    Demand,
    FulfilmentRecord,
    PriceTier,
    Retailer,
    Scenario,
    Supplier,
    SupplierQuote,
    SupplierServiceArea,
)
from ..errors import APIError
from ..extensions import db
from ..schemas import integer, iso_date, number, price_tiers, required_text, string_list
from ..services.scenario_service import demand_dict, full_scenario, quote_dict, run_evaluation, scenario_dict


api_bp = Blueprint("api", __name__)


def roles_required(*roles: str):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                raise APIError("Your role is not allowed to perform this action.", 403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _json() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError("A JSON object is required.")
    return data


def _pagination_args() -> tuple[int, int]:
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", current_app.config["ITEMS_PER_PAGE"]))))
    except ValueError as exc:
        raise APIError("page and per_page must be whole numbers.") from exc
    return page, per_page


@api_bp.get("/scenarios")
@login_required
def list_scenarios():
    scenarios = db.session.execute(db.select(Scenario).order_by(Scenario.id)).scalars().all()
    return jsonify({"items": [scenario_dict(item) for item in scenarios], "count": len(scenarios)})


@api_bp.post("/scenarios")
@roles_required("admin")
def create_scenario():
    data = _json()
    scenario = Scenario(
        name=required_text(data, "name", 160),
        code=required_text(data, "code", 60).lower().replace(" ", "-"),
        description=required_text(data, "description", 3000),
        expected_outcome=required_text(data, "expected_outcome", 80),
        product=required_text(data, "product", 120),
        window_open=iso_date(data, "window_open"),
        window_close=iso_date(data, "window_close"),
        commitment_deadline=iso_date(data, "commitment_deadline"),
        compatibility_days=integer(data, "compatibility_days", 0),
        minimum_fill_rate=number(data, "minimum_fill_rate", 0, 1),
        minimum_on_time_rate=number(data, "minimum_on_time_rate", 0, 1),
        status=str(data.get("status", "open")),
    )
    if scenario.window_open > scenario.window_close:
        raise APIError("window_open cannot be after window_close.")
    db.session.add(scenario)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise APIError("Scenario code already exists.", 409) from exc
    return jsonify(scenario_dict(scenario)), 201


@api_bp.get("/scenarios/<int:scenario_id>")
@login_required
def get_scenario(scenario_id: int):
    scenario = db.get_or_404(Scenario, scenario_id)
    return jsonify(full_scenario(scenario))


@api_bp.post("/scenarios/<int:scenario_id>/evaluate")
@login_required
def evaluate(scenario_id: int):
    scenario = db.get_or_404(Scenario, scenario_id)
    try:
        result = run_evaluation(scenario, save=True)
    except DecisionModelError as exc:
        raise APIError(str(exc), 422) from exc
    return jsonify(result)


@api_bp.get("/demands")
@login_required
def list_demands():
    page, per_page = _pagination_args()
    query = db.select(Demand).order_by(Demand.id)
    if request.args.get("scenario_id"):
        query = query.where(Demand.scenario_id == int(request.args["scenario_id"]))
    if request.args.get("status"):
        query = query.where(Demand.status == request.args["status"])
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "items": [demand_dict(item) for item in pagination.items],
            "pagination": {"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages},
        }
    )


@api_bp.post("/demands")
@roles_required("admin", "retailer")
def create_demand():
    data = _json()
    scenario = db.session.get(Scenario, integer(data, "scenario_id", 1))
    if not scenario:
        raise APIError("Scenario not found.", 404)
    retailer_name = required_text(data, "retailer_name", 160)
    area = required_text(data, "area", 120)
    retailer = db.session.execute(
        db.select(Retailer).where(Retailer.name == retailer_name, Retailer.area == area)
    ).scalar_one_or_none()
    if retailer is None:
        retailer = Retailer(name=retailer_name, area=area, contact_email=data.get("contact_email"))
        db.session.add(retailer)
    demand = Demand(
        scenario=scenario,
        retailer=retailer,
        product=required_text(data, "product", 120),
        quantity_kg=number(data, "quantity_kg", 0.01),
        required_date=iso_date(data, "required_date"),
        submitted_date=iso_date(data, "submitted_date") if data.get("submitted_date") else date.today(),
        status=str(data.get("status", "committed")).lower(),
        baseline_price_per_kg=number(data, "baseline_price_per_kg", 0),
        baseline_logistics_cost=number(data, "baseline_logistics_cost", 0),
        baseline_handling_cost=number(data, "baseline_handling_cost", 0),
        baseline_distance_km=number(data, "baseline_distance_km", 0),
        baseline_trips=number(data, "baseline_trips", 0),
        baseline_fill_rate=number(data, "baseline_fill_rate", 0, 1),
        baseline_on_time_rate=number(data, "baseline_on_time_rate", 0, 1),
        orders_per_month=number(data, "orders_per_month", 0),
        individual_procurement_cost=number(data, "individual_procurement_cost", 0),
    )
    if demand.status not in {"pending", "committed", "withdrawn"}:
        raise APIError("status must be pending, committed or withdrawn.")
    db.session.add(demand)
    db.session.commit()
    return jsonify(demand_dict(demand)), 201


@api_bp.patch("/demands/<int:demand_id>/status")
@roles_required("admin", "retailer")
def change_demand_status(demand_id: int):
    data = _json()
    demand = db.get_or_404(Demand, demand_id)
    new_status = required_text(data, "status", 30).lower()
    if new_status not in {"pending", "committed", "withdrawn"}:
        raise APIError("status must be pending, committed or withdrawn.")
    if new_status == "withdrawn" and date.today() > demand.scenario.commitment_deadline:
        raise APIError("Withdrawal is locked after the commitment deadline.", 409)
    demand.status = new_status
    demand.withdrawn_at = datetime.utcnow() if new_status == "withdrawn" else None
    db.session.commit()
    return jsonify(demand_dict(demand))


@api_bp.get("/quotes")
@login_required
def list_quotes():
    page, per_page = _pagination_args()
    query = db.select(SupplierQuote).order_by(SupplierQuote.id)
    if request.args.get("scenario_id"):
        query = query.where(SupplierQuote.scenario_id == int(request.args["scenario_id"]))
    if request.args.get("product"):
        query = query.where(SupplierQuote.product == request.args["product"])
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "items": [quote_dict(item) for item in pagination.items],
            "pagination": {"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages},
        }
    )


@api_bp.post("/quotes")
@roles_required("admin", "supplier")
def create_quote():
    data = _json()
    scenario = db.session.get(Scenario, integer(data, "scenario_id", 1))
    if not scenario:
        raise APIError("Scenario not found.", 404)
    supplier_name = required_text(data, "supplier_name", 160)
    supplier = db.session.execute(db.select(Supplier).where(Supplier.name == supplier_name)).scalar_one_or_none()
    if supplier is None:
        supplier = Supplier(name=supplier_name, verified=bool(data.get("verified", False)))
        db.session.add(supplier)
    quote = SupplierQuote(
        scenario=scenario,
        supplier=supplier,
        product=required_text(data, "product", 120),
        capacity_kg=number(data, "capacity_kg", 0.01),
        lead_time_days=integer(data, "lead_time_days", 0),
        fixed_fulfilment_cost=number(data, "fixed_fulfilment_cost", 0),
        variable_fulfilment_per_kg=number(data, "variable_fulfilment_per_kg", 0),
        handling_cost=number(data, "handling_cost", 0),
        route_distance_km=number(data, "route_distance_km", 0),
        expected_fill_rate=number(data, "expected_fill_rate", 0, 1),
        expected_on_time_rate=number(data, "expected_on_time_rate", 0, 1),
        fulfilment_mode=str(data.get("fulfilment_mode", "delivery")),
    )
    quote.price_tiers = [PriceTier(**tier) for tier in price_tiers(data)]
    quote.service_areas = [SupplierServiceArea(area=area) for area in string_list(data, "service_areas")]
    db.session.add(quote)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise APIError("This supplier already has a quote for the scenario and product.", 409) from exc
    return jsonify(quote_dict(quote)), 201


@api_bp.post("/performance")
@roles_required("admin", "supplier")
def record_performance():
    data = _json()
    scenario = db.session.get(Scenario, integer(data, "scenario_id", 1))
    if not scenario:
        raise APIError("Scenario not found.", 404)
    record = FulfilmentRecord(
        scenario=scenario,
        supplier_name=required_text(data, "supplier_name", 160),
        ordered_quantity_kg=number(data, "ordered_quantity_kg", 0.01),
        delivered_quantity_kg=number(data, "delivered_quantity_kg", 0),
        actual_total_cost=number(data, "actual_total_cost", 0),
        due_date=iso_date(data, "due_date"),
        delivered_date=iso_date(data, "delivered_date"),
        actual_logistics_cost=number(data, "actual_logistics_cost", 0),
        actual_trips=integer(data, "actual_trips", 0),
        actual_distance_km=number(data, "actual_distance_km", 0),
        exception_notes=str(data.get("exception_notes", "")).strip() or None,
    )
    db.session.add(record)
    db.session.commit()
    fill_rate = min(1, record.delivered_quantity_kg / record.ordered_quantity_kg)
    return jsonify(
        {
            "id": record.id,
            "actual_cost_per_kg": round(record.actual_total_cost / record.delivered_quantity_kg, 4)
            if record.delivered_quantity_kg
            else None,
            "fill_rate": round(fill_rate, 4),
            "on_time": record.delivered_date <= record.due_date,
        }
    ), 201


@api_bp.get("/scenarios/<int:scenario_id>/performance")
@login_required
def performance_summary(scenario_id: int):
    scenario = db.get_or_404(Scenario, scenario_id)
    records = scenario.fulfilment_records
    ordered = sum(item.ordered_quantity_kg for item in records)
    delivered = sum(item.delivered_quantity_kg for item in records)
    return jsonify(
        {
            "record_count": len(records),
            "fill_rate": round(delivered / ordered, 4) if ordered else None,
            "on_time_rate": round(sum(item.delivered_date <= item.due_date for item in records) / len(records), 4)
            if records
            else None,
            "actual_cost_per_kg": round(sum(item.actual_total_cost for item in records) / delivered, 4)
            if delivered
            else None,
            "actual_logistics_cost_per_kg": round(sum(item.actual_logistics_cost for item in records) / delivered, 4)
            if delivered
            else None,
            "trips": sum(item.actual_trips for item in records),
            "route_distance_km": round(sum(item.actual_distance_km for item in records), 2),
        }
    )

