"""Small explicit request schemas and validation helpers.

Keeping validation functions visible makes the API contract straightforward to
mark and avoids letting unvalidated request dictionaries reach the database.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .errors import APIError


def required_text(data: dict[str, Any], field: str, max_length: int = 190) -> str:
    value = str(data.get(field, "")).strip()
    if not value:
        raise APIError(f"{field} is required.", details={field: "required"})
    if len(value) > max_length:
        raise APIError(f"{field} is too long.", details={field: f"maximum {max_length} characters"})
    return value


def number(data: dict[str, Any], field: str, minimum: float = 0.0, maximum: float | None = None) -> float:
    try:
        value = float(data.get(field))
    except (TypeError, ValueError) as exc:
        raise APIError(f"{field} must be numeric.", details={field: "invalid number"}) from exc
    if value < minimum or (maximum is not None and value > maximum):
        limit = f"between {minimum} and {maximum}" if maximum is not None else f"at least {minimum}"
        raise APIError(f"{field} must be {limit}.", details={field: limit})
    return value


def integer(data: dict[str, Any], field: str, minimum: int = 0) -> int:
    try:
        value = int(data.get(field))
    except (TypeError, ValueError) as exc:
        raise APIError(f"{field} must be a whole number.", details={field: "invalid integer"}) from exc
    if value < minimum:
        raise APIError(f"{field} must be at least {minimum}.", details={field: f"minimum {minimum}"})
    return value


def iso_date(data: dict[str, Any], field: str) -> date:
    try:
        return date.fromisoformat(str(data.get(field, ""))[:10])
    except ValueError as exc:
        raise APIError(f"{field} must be a valid ISO date.", details={field: "use YYYY-MM-DD"}) from exc


def string_list(data: dict[str, Any], field: str) -> list[str]:
    value = data.get(field)
    if isinstance(value, str):
        result = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, list):
        result = [str(part).strip() for part in value if str(part).strip()]
    else:
        result = []
    if not result:
        raise APIError(f"{field} requires at least one value.", details={field: "required list"})
    return sorted(set(result))


def price_tiers(data: dict[str, Any]) -> list[dict[str, float]]:
    raw = data.get("price_tiers")
    parsed: list[dict[str, float]] = []
    if isinstance(raw, str):
        try:
            for part in raw.split(";"):
                minimum, price = part.split(":", 1)
                parsed.append({"minimum_kg": float(minimum.strip()), "price_per_kg": float(price.strip())})
        except (ValueError, TypeError) as exc:
            raise APIError("price_tiers must use minimum:price pairs separated by semicolons.") from exc
    elif isinstance(raw, list):
        for tier in raw:
            if not isinstance(tier, dict):
                raise APIError("Each price tier must be an object.")
            parsed.append(
                {
                    "minimum_kg": number(tier, "minimum_kg", 0),
                    "price_per_kg": number(tier, "price_per_kg", 0),
                }
            )
    if not parsed:
        raise APIError("At least one price tier is required.")
    minimums = [tier["minimum_kg"] for tier in parsed]
    if len(minimums) != len(set(minimums)):
        raise APIError("Price-tier minimum quantities must be unique.")
    return sorted(parsed, key=lambda tier: tier["minimum_kg"])

