"""Shared derived-field calculations used by entry and bulk upload flows."""

import math


def _number(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def compute_food_database_fields(record):
    """Return computed Food Database values for one record."""
    quantity_purchased = _number(record.get("Purchased_Quantity"))
    unit_cost = _number(record.get("Purchase_Unity_Cost"))
    quantity_used = _number(record.get("Quantity_Used"))

    total_cost = (
        round(quantity_purchased * unit_cost, 2)
        if quantity_purchased is not None and unit_cost is not None
        else None
    )

    food_item = str(record.get("Food_Item") or "").strip().casefold()
    meals_per_unit = {
        "rice": 5,
        "mixed porridge flour": 13,
    }.get(food_item)
    meals_served = (
        quantity_used * meals_per_unit
        if quantity_used is not None and meals_per_unit is not None
        else None
    )

    return {
        "Total_Cost": total_cost,
        "Meals_Served": meals_served,
    }
