"""ButcherBridge procurement decision model.

This module deliberately has no Flask or database imports. It accepts plain
dictionaries and returns a serialisable result so the formulas can be tested
before any route or persistence layer calls them.

Formula 1 — compatible group demand::

    Q_G = sum(q_i)

Formula 2 — supplier landed cost per kilogram::

    C_s = (P_s(Q) * Q + T_fixed + T_variable * Q + H_s) / Q

Formula 3 — saving versus recorded baseline::

    saving_pct = (C_baseline - C_option) / C_baseline * 100

Only committed demand submitted before the order-window close is included.
An option must satisfy product, area, capacity, price-tier, due-date and service
thresholds. Shared fixed logistics and handling costs are allocated in
proportion to each retailer's kilograms.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from itertools import product
from typing import Any, Iterable


EPSILON = 1e-9


class DecisionModelError(ValueError):
    """Raised when the calculation inputs are incomplete or inconsistent."""


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        raise DecisionModelError("A required date value is missing.")
    return date.fromisoformat(str(value)[:10])


def _number(value: Any, field: str, minimum: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise DecisionModelError(f"{field} must be numeric.") from exc
    if result < minimum:
        raise DecisionModelError(f"{field} must be at least {minimum}.")
    return result


def qualifying_tier(tiers: Iterable[dict[str, Any]], quantity_kg: float) -> dict[str, float] | None:
    """Return the highest minimum-quantity tier reached by ``quantity_kg``."""
    normalised = sorted(
        (
            {
                "minimum_kg": _number(tier.get("minimum_kg"), "tier minimum_kg"),
                "price_per_kg": _number(tier.get("price_per_kg"), "tier price_per_kg"),
            }
            for tier in tiers
        ),
        key=lambda tier: tier["minimum_kg"],
    )
    matches = [tier for tier in normalised if tier["minimum_kg"] <= quantity_kg + EPSILON]
    return matches[-1] if matches else None


def _quote_areas(quote: dict[str, Any]) -> set[str]:
    return {str(area).strip().lower() for area in quote.get("service_areas", []) if str(area).strip()}


def _covers_area(quote: dict[str, Any], area: str) -> bool:
    areas = _quote_areas(quote)
    return "all" in areas or area.strip().lower() in areas


def _supplier_reasons(
    quote: dict[str, Any],
    demands: list[dict[str, Any]],
    scenario: dict[str, Any],
    assigned_quantity: float | None = None,
    check_price_tier: bool = True,
) -> list[str]:
    """Return every failed feasibility check for a supplier assignment."""
    reasons: list[str] = []
    product_name = str(scenario["product"]).strip().lower()
    quantity = assigned_quantity if assigned_quantity is not None else sum(float(d["quantity_kg"]) for d in demands)
    if str(quote.get("product", "")).strip().lower() != product_name:
        reasons.append("product mismatch")
    if _number(quote.get("capacity_kg", 0), "capacity_kg") + EPSILON < quantity:
        reasons.append(f"capacity shortfall ({quote.get('capacity_kg', 0):g} kg available)")
    uncovered = sorted({str(d["area"]) for d in demands if not _covers_area(quote, str(d["area"]))})
    if uncovered:
        reasons.append("service area excludes " + ", ".join(uncovered))
    completion_date = _as_date(scenario["window_close"]) + timedelta(days=int(quote.get("lead_time_days", 0)))
    late = sorted({str(d["retailer_name"]) for d in demands if completion_date > _as_date(d["required_date"])})
    if late:
        reasons.append("lead time misses: " + ", ".join(late))
    if check_price_tier and qualifying_tier(quote.get("price_tiers", []), quantity) is None:
        reasons.append("no price tier qualifies")
    if _number(quote.get("expected_fill_rate", 0), "expected_fill_rate") + EPSILON < _number(
        scenario.get("minimum_fill_rate", 0), "minimum_fill_rate"
    ):
        reasons.append("fill-rate threshold not met")
    if _number(quote.get("expected_on_time_rate", 0), "expected_on_time_rate") + EPSILON < _number(
        scenario.get("minimum_on_time_rate", 0), "minimum_on_time_rate"
    ):
        reasons.append("on-time threshold not met")
    return reasons


def _cost_for_supplier(quote: dict[str, Any], quantity_kg: float) -> dict[str, float]:
    tier = qualifying_tier(quote.get("price_tiers", []), quantity_kg)
    if tier is None:
        raise DecisionModelError("No supplier price tier qualifies for the assigned quantity.")
    product_cost = tier["price_per_kg"] * quantity_kg
    fixed_logistics = _number(quote.get("fixed_fulfilment_cost", 0), "fixed_fulfilment_cost")
    variable_logistics = _number(quote.get("variable_fulfilment_per_kg", 0), "variable_fulfilment_per_kg") * quantity_kg
    handling_cost = _number(quote.get("handling_cost", 0), "handling_cost")
    total = product_cost + fixed_logistics + variable_logistics + handling_cost
    return {
        "unit_price": round(tier["price_per_kg"], 4),
        "tier_minimum_kg": round(tier["minimum_kg"], 4),
        "product_cost": round(product_cost, 2),
        "fixed_logistics": round(fixed_logistics, 2),
        "variable_logistics": round(variable_logistics, 2),
        "handling_cost": round(handling_cost, 2),
        "total_cost": round(total, 2),
        "landed_cost_per_kg": round(total / quantity_kg, 4),
    }


def _build_option(
    assignments: list[tuple[dict[str, Any], dict[str, Any]]],
    option_type: str,
    baseline: dict[str, float],
) -> dict[str, Any]:
    by_supplier: dict[Any, dict[str, Any]] = {}
    for demand, quote in assignments:
        key = quote.get("id", quote.get("supplier_name"))
        bucket = by_supplier.setdefault(key, {"quote": quote, "demands": [], "quantity_kg": 0.0})
        bucket["demands"].append(demand)
        bucket["quantity_kg"] += float(demand["quantity_kg"])

    supplier_parts: list[dict[str, Any]] = []
    retailer_allocations: list[dict[str, Any]] = []
    total_cost = 0.0
    total_logistics = 0.0
    total_quantity = sum(float(d["quantity_kg"]) for d, _ in assignments)
    weighted_fill = 0.0
    weighted_on_time = 0.0
    max_lead = 0
    route_distance = 0.0

    for bucket in by_supplier.values():
        quote = bucket["quote"]
        quantity = bucket["quantity_kg"]
        cost = _cost_for_supplier(quote, quantity)
        total_cost += cost["total_cost"]
        total_logistics += cost["fixed_logistics"] + cost["variable_logistics"]
        weighted_fill += float(quote["expected_fill_rate"]) * quantity
        weighted_on_time += float(quote["expected_on_time_rate"]) * quantity
        max_lead = max(max_lead, int(quote["lead_time_days"]))
        route_distance += float(quote.get("route_distance_km", 0))
        supplier_parts.append(
            {
                "supplier_id": quote.get("supplier_id"),
                "supplier_name": quote["supplier_name"],
                "quantity_kg": round(quantity, 2),
                **cost,
            }
        )
        shared_cost = cost["fixed_logistics"] + cost["handling_cost"]
        for demand in bucket["demands"]:
            demand_quantity = float(demand["quantity_kg"])
            allocated_shared = shared_cost * (demand_quantity / quantity)
            allocated_variable = float(quote.get("variable_fulfilment_per_kg", 0)) * demand_quantity
            retailer_total = cost["unit_price"] * demand_quantity + allocated_shared + allocated_variable
            retailer_allocations.append(
                {
                    "demand_id": demand.get("id"),
                    "retailer_name": demand["retailer_name"],
                    "supplier_name": quote["supplier_name"],
                    "quantity_kg": round(demand_quantity, 2),
                    "shared_cost_rule": "kilograms proportional",
                    "allocated_shared_cost": round(allocated_shared, 2),
                    "allocated_logistics_cost": round(
                        allocated_shared + allocated_variable - cost["handling_cost"] * (demand_quantity / quantity), 2
                    ),
                    "total_cost": round(retailer_total, 2),
                    "landed_cost_per_kg": round(retailer_total / demand_quantity, 4),
                }
            )

    landed = total_cost / total_quantity
    return {
        "type": option_type,
        "label": {
            "collective_single_supplier": "Collective purchase — one supplier",
            "coordinated_split": "Coordinated fulfilment — capacity split",
            "individual": "Individual procurement",
        }[option_type],
        "supplier_count": len(by_supplier),
        "quantity_kg": round(total_quantity, 2),
        "total_cost": round(total_cost, 2),
        "landed_cost_per_kg": round(landed, 4),
        "logistics_cost": round(total_logistics, 2),
        "logistics_cost_per_kg": round(total_logistics / total_quantity, 4),
        "lead_time_days": max_lead,
        "expected_fill_rate": round(weighted_fill / total_quantity, 4),
        "expected_on_time_rate": round(weighted_on_time / total_quantity, 4),
        "route_distance_km": round(route_distance, 2),
        "trip_count": len(by_supplier) if option_type != "individual" else len(assignments),
        "saving_vs_baseline_pct": round((baseline["cost_per_kg"] - landed) / baseline["cost_per_kg"] * 100, 2),
        "suppliers": sorted(supplier_parts, key=lambda item: item["supplier_name"]),
        "retailer_allocations": sorted(retailer_allocations, key=lambda item: item["retailer_name"]),
    }


def _baseline(demands: list[dict[str, Any]]) -> dict[str, float]:
    quantity = sum(float(d["quantity_kg"]) for d in demands)
    purchase = sum(float(d["baseline_price_per_kg"]) * float(d["quantity_kg"]) for d in demands)
    logistics = sum(float(d.get("baseline_logistics_cost", 0)) for d in demands)
    handling = sum(float(d.get("baseline_handling_cost", 0)) for d in demands)
    total = purchase + logistics + handling
    return {
        "quantity_kg": round(quantity, 2),
        "total_cost": round(total, 2),
        "cost_per_kg": round(total / quantity, 4),
        "logistics_cost": round(logistics, 2),
        "logistics_cost_per_kg": round(logistics / quantity, 4),
        "trips": round(sum(float(d.get("baseline_trips", 0)) for d in demands), 2),
        "route_distance_km": round(sum(float(d.get("baseline_distance_km", 0)) for d in demands), 2),
        "fill_rate": round(sum(float(d.get("baseline_fill_rate", 0)) * float(d["quantity_kg"]) for d in demands) / quantity, 4),
        "on_time_rate": round(sum(float(d.get("baseline_on_time_rate", 0)) * float(d["quantity_kg"]) for d in demands) / quantity, 4),
        "orders_per_month": round(sum(float(d.get("orders_per_month", 0)) for d in demands), 2),
    }


def _compatible_demands(demands: list[dict[str, Any]], scenario: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    product_name = str(scenario["product"]).strip().lower()
    close_date = _as_date(scenario["window_close"])
    for demand in demands:
        reason = None
        if str(demand.get("status", "")).lower() != "committed":
            reason = f"status is {demand.get('status', 'unknown')}"
        elif str(demand.get("product", "")).strip().lower() != product_name:
            reason = "product mismatch"
        elif _as_date(demand.get("submitted_date")) > close_date:
            reason = "submitted after order-window close"
        elif _number(demand.get("quantity_kg"), "quantity_kg", 0.01) <= 0:
            reason = "quantity must be positive"
        if reason:
            excluded.append({"retailer_name": str(demand.get("retailer_name", "Unknown")), "reason": reason})
        else:
            included.append(demand)

    if included:
        dates = [_as_date(d["required_date"]) for d in included]
        if (max(dates) - min(dates)).days > int(scenario.get("compatibility_days", 0)):
            anchor = min(dates)
            still_included = []
            for demand in included:
                if (_as_date(demand["required_date"]) - anchor).days <= int(scenario.get("compatibility_days", 0)):
                    still_included.append(demand)
                else:
                    excluded.append({"retailer_name": demand["retailer_name"], "reason": "required date outside compatibility window"})
            included = still_included
    return included, excluded


def _individual_option(
    demands: list[dict[str, Any]], quotes: list[dict[str, Any]], scenario: dict[str, Any], baseline: dict[str, float]
) -> dict[str, Any] | None:
    assignments: list[tuple[dict[str, Any], dict[str, Any], dict[str, float]]] = []
    for demand in demands:
        candidates = []
        for quote in quotes:
            if _supplier_reasons(quote, [demand], scenario, float(demand["quantity_kg"])):
                continue
            candidate_cost = _cost_for_supplier(quote, float(demand["quantity_kg"]))["total_cost"]
            candidates.append((candidate_cost, quote))
        if not candidates:
            return None
        _, chosen = min(candidates, key=lambda item: item[0])
        assignments.append((demand, chosen, _cost_for_supplier(chosen, float(demand["quantity_kg"]))))

    total_quantity = sum(float(demand["quantity_kg"]) for demand, _, _ in assignments)
    procurement_admin = sum(float(demand.get("individual_procurement_cost", 0)) for demand, _, _ in assignments)
    supplier_parts = []
    retailer_allocations = []
    total_cost = procurement_admin
    total_logistics = 0.0
    weighted_fill = 0.0
    weighted_on_time = 0.0
    route_distance = 0.0
    max_lead = 0
    for demand, chosen, cost in assignments:
        quantity = float(demand["quantity_kg"])
        admin_cost = float(demand.get("individual_procurement_cost", 0))
        order_total = cost["total_cost"] + admin_cost
        total_cost += cost["total_cost"]
        total_logistics += cost["fixed_logistics"] + cost["variable_logistics"]
        weighted_fill += float(chosen["expected_fill_rate"]) * quantity
        weighted_on_time += float(chosen["expected_on_time_rate"]) * quantity
        route_distance += float(chosen.get("route_distance_km", 0))
        max_lead = max(max_lead, int(chosen["lead_time_days"]))
        supplier_parts.append(
            {
                "supplier_id": chosen.get("supplier_id"),
                "supplier_name": chosen["supplier_name"],
                "retailer_name": demand["retailer_name"],
                "quantity_kg": round(quantity, 2),
                **cost,
            }
        )
        retailer_allocations.append(
            {
                "demand_id": demand.get("id"),
                "retailer_name": demand["retailer_name"],
                "supplier_name": chosen["supplier_name"],
                "quantity_kg": round(quantity, 2),
                "shared_cost_rule": "separate order — no shared fixed cost",
                "allocated_shared_cost": round(cost["fixed_logistics"] + cost["handling_cost"], 2),
                "allocated_logistics_cost": round(cost["fixed_logistics"] + cost["variable_logistics"], 2),
                "individual_procurement_cost": round(admin_cost, 2),
                "total_cost": round(order_total, 2),
                "landed_cost_per_kg": round(order_total / quantity, 4),
            }
        )
    landed = total_cost / total_quantity
    option = {
        "type": "individual",
        "label": "Individual procurement",
        "supplier_count": len({quote.get("id", quote["supplier_name"]) for _, quote, _ in assignments}),
        "quantity_kg": round(total_quantity, 2),
        "total_cost": round(total_cost, 2),
        "landed_cost_per_kg": round(landed, 4),
        "logistics_cost": round(total_logistics, 2),
        "logistics_cost_per_kg": round(total_logistics / total_quantity, 4),
        "lead_time_days": max_lead,
        "expected_fill_rate": round(weighted_fill / total_quantity, 4),
        "expected_on_time_rate": round(weighted_on_time / total_quantity, 4),
        "route_distance_km": round(route_distance, 2),
        "trip_count": len(assignments),
        "individual_procurement_cost": round(procurement_admin, 2),
        "suppliers": supplier_parts,
        "retailer_allocations": retailer_allocations,
    }
    option["saving_vs_baseline_pct"] = round(
        (baseline["cost_per_kg"] - option["landed_cost_per_kg"]) / baseline["cost_per_kg"] * 100, 2
    )
    return option


def _split_option(
    demands: list[dict[str, Any]], quotes: list[dict[str, Any]], scenario: dict[str, Any], baseline: dict[str, float]
) -> dict[str, Any] | None:
    candidate_lists: list[list[dict[str, Any]]] = []
    for demand in demands:
        candidates = [
            quote
            for quote in quotes
            if not _supplier_reasons(
                quote,
                [demand],
                scenario,
                float(demand["quantity_kg"]),
                check_price_tier=False,
            )
        ]
        if not candidates:
            return None
        candidate_lists.append(candidates)
    combination_count = 1
    for candidates in candidate_lists:
        combination_count *= len(candidates)
    if combination_count > 100_000:
        raise DecisionModelError("Scenario is too large for exact capacity allocation; reduce active demands or suppliers.")

    best: dict[str, Any] | None = None
    for chosen_quotes in product(*candidate_lists):
        if len({quote.get("id", quote["supplier_name"]) for quote in chosen_quotes}) < 2:
            continue
        assigned: dict[Any, float] = {}
        valid = True
        for demand, quote in zip(demands, chosen_quotes):
            key = quote.get("id", quote["supplier_name"])
            assigned[key] = assigned.get(key, 0.0) + float(demand["quantity_kg"])
            if assigned[key] > float(quote["capacity_kg"]) + EPSILON:
                valid = False
                break
        if not valid:
            continue
        if any(qualifying_tier(quote["price_tiers"], assigned[quote.get("id", quote["supplier_name"])]) is None for quote in chosen_quotes):
            continue
        option = _build_option(list(zip(demands, chosen_quotes)), "coordinated_split", baseline)
        if best is None or option["total_cost"] < best["total_cost"] - EPSILON:
            best = option
    return best


def evaluate_scenario(
    demands: list[dict[str, Any]], quotes: list[dict[str, Any]], scenario: dict[str, Any]
) -> dict[str, Any]:
    """Evaluate individual, collective and coordinated procurement alternatives.

    The selected recommendation is never forced to be an aggregated option. If
    individual procurement is cheaper or all group options fail a constraint,
    the function explicitly returns ``REJECT_AGGREGATION``.
    """
    if not scenario.get("product"):
        raise DecisionModelError("Scenario product is required.")
    compatible, excluded = _compatible_demands(demands, scenario)
    if not compatible:
        raise DecisionModelError("No committed compatible demand falls inside the order window.")
    baseline = _baseline(compatible)
    total_quantity = baseline["quantity_kg"]

    feasibility = []
    collective_options = []
    for quote in quotes:
        reasons = _supplier_reasons(quote, compatible, scenario, total_quantity)
        feasibility.append(
            {
                "supplier_id": quote.get("supplier_id"),
                "supplier_name": quote["supplier_name"],
                "feasible": not reasons,
                "reasons": reasons,
            }
        )
        if not reasons:
            collective_options.append(
                _build_option([(demand, quote) for demand in compatible], "collective_single_supplier", baseline)
            )

    split = _split_option(compatible, quotes, scenario, baseline)
    individual = _individual_option(compatible, quotes, scenario, baseline)
    proposed_options = collective_options + ([split] if split else [])
    proposed_options.sort(key=lambda option: (option["landed_cost_per_kg"], option["lead_time_days"]))
    best_proposed = proposed_options[0] if proposed_options else None

    if best_proposed is None and individual is None:
        decision = "NO_FEASIBLE_OPTION"
        recommendation = None
        rationale = "Neither an individual nor coordinated option meets all feasibility and service rules."
    elif best_proposed is None:
        decision = "REJECT_AGGREGATION"
        recommendation = individual
        rationale = "Aggregation is rejected because no collective or coordinated option meets all constraints."
    elif individual is None or best_proposed["landed_cost_per_kg"] < individual["landed_cost_per_kg"] - EPSILON:
        decision = "ACCEPT_AGGREGATION" if best_proposed["type"] == "collective_single_supplier" else "ACCEPT_COORDINATED_SPLIT"
        recommendation = best_proposed
        comparator = "the feasible individual alternative" if individual else "an unavailable individual alternative"
        rationale = f"{best_proposed['label']} is recommended because it meets every rule and has a lower total landed cost than {comparator}."
    else:
        decision = "REJECT_AGGREGATION"
        recommendation = individual
        rationale = "Aggregation is rejected because individual procurement provides an equal or lower total landed cost while meeting service requirements."

    all_options = proposed_options + ([individual] if individual else [])
    cost_responsiveness = [
        {
            "label": option["label"],
            "type": option["type"],
            "landed_cost_per_kg": option["landed_cost_per_kg"],
            "lead_time_days": option["lead_time_days"],
            "expected_on_time_rate": option["expected_on_time_rate"],
            "recommended": bool(recommendation and option is recommendation),
        }
        for option in sorted(all_options, key=lambda item: (item["lead_time_days"], item["landed_cost_per_kg"]))
    ]

    recommended_kpis = None
    if recommendation:
        recommended_kpis = {
            "landed_cost_per_kg": recommendation["landed_cost_per_kg"],
            "logistics_cost_per_kg": recommendation["logistics_cost_per_kg"],
            "expected_fill_rate": recommendation["expected_fill_rate"],
            "expected_on_time_rate": recommendation["expected_on_time_rate"],
            "trips": recommendation["trip_count"],
            "trips_avoided": round(baseline["trips"] - recommendation["trip_count"], 2),
            "route_distance_km": recommendation["route_distance_km"],
            "distance_change_km": round(recommendation["route_distance_km"] - baseline["route_distance_km"], 2),
            "saving_vs_baseline_pct": recommendation["saving_vs_baseline_pct"],
        }

    return {
        "decision": decision,
        "rationale": rationale,
        "rules_applied": [
            "Only committed demand submitted by the order-window close is included.",
            f"Demand is compatible when product matches and required dates fall within {scenario.get('compatibility_days', 0)} day(s).",
            "Each supplier must cover every assigned area, have sufficient capacity, meet every due date and pass service thresholds.",
            "The highest price tier whose minimum quantity is reached is applied to confirmed kilograms only.",
            "Supplier capacity is allocated in whole retailer orders; a retailer order is never split.",
            "Shared fixed logistics and handling costs are allocated in proportion to retailer kilograms.",
            "Aggregation is recommended only when feasible and cheaper than the best feasible individual alternative.",
        ],
        "compatible_demand": {
            "quantity_kg": total_quantity,
            "retailer_count": len(compatible),
            "included": [d["retailer_name"] for d in compatible],
            "excluded": excluded,
        },
        "baseline": baseline,
        "supplier_feasibility": feasibility,
        "collective_options": collective_options,
        "coordinated_split_option": split,
        "individual_option": individual,
        "recommendation": recommendation,
        "recommended_kpis": recommended_kpis,
        "cost_responsiveness_tradeoff": cost_responsiveness,
    }

