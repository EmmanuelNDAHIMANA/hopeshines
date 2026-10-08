"""Allowed Food Database item, purchase-unit and category combinations."""

FOOD_CATALOG = [
    ("Rice", "Kg", "Lunch"),
    ("Macaroni", "Pcs", "Lunch"),
    ("Beans", "Kg", "Lunch"),
    ("Salt", "Kg", "Lunch"),
    ("Oil", "Ltr", "Lunch"),
    ("Chalcoal", "Bag", "Lunch"),
    ("Salsa", "Pcs", "Lunch"),
    ("Maggie", "Pcs", "Lunch"),
    ("Sweet Potatoes", "Kg", "Lunch"),
    ("Onion,pavron,selelli,puallo", "Kg", "Lunch"),
    ("Gallic", "kg", "Lunch"),
    ("Irish Potatoes", "Kg", "Lunch"),
    ("Green Banana", "Kg", "Lunch"),
    ("Green Vegetable", "Pcs", "Lunch"),
    ("Groundnut Flour", "Bag", "Lunch"),
    ("small Fish (Indagara)", "Kg", "Lunch"),
    ("Garden Eggs (Intoryi)", "Basin", "Lunch"),
    ("Cabbage", "pcs", "Lunch"),
    ("Tomatoes", "kg", "Lunch"),
    ("Pepper", "Bag", "Lunch"),
    ("Green Beans (Imiteja)", "kg", "Lunch"),
    ("Carrots", "kg", "Lunch"),
    ("Ticket", "Each", "Lunch"),
    ("Choufrere", "Pcs", "Lunch"),
    ("Isombe", "Pcs", "Lunch"),
    ("Imifupa", "Kg", "Lunch"),
    ("Leek", "Pcs", "Lunch"),
    ("Celery", "Each", "Lunch"),
    ("Mixed Porridge Flour", "kg", "Breakfast"),
    ("Sugar", "kg", "Breakfast"),
    ("Donut", "pcs", "Breakfast"),
    ("Banana", "pcs", "Breakfast"),
    ("Chalcoal", "Bag", "Breakfast"),
]

FOOD_ITEMS = list(dict.fromkeys(item for item, _, _ in FOOD_CATALOG))
PURCHASE_UNITS = list(dict.fromkeys(unit for _, unit, _ in FOOD_CATALOG))
FOOD_CATEGORIES = list(dict.fromkeys(category for _, _, category in FOOD_CATALOG))


def units_for_item(item):
    return list(dict.fromkeys(unit for name, unit, _ in FOOD_CATALOG if name == item))


def categories_for_item_and_unit(item, unit):
    return list(dict.fromkeys(
        category
        for name, item_unit, category in FOOD_CATALOG
        if name == item and item_unit == unit
    ))
