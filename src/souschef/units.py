"""Unit normalization and combination utilities for grocery aggregation."""

import re

UNIT_ALIASES = {
    # teaspoon
    "tsp": "teaspoon",
    "tsps": "teaspoon",
    "teaspoons": "teaspoon",
    # tablespoon
    "tbsp": "tablespoon",
    "tbsps": "tablespoon",
    "tablespoons": "tablespoon",
    "tbs": "tablespoon",
    # cup
    "cups": "cup",
    "c": "cup",
    # pint
    "pints": "pint",
    "pt": "pint",
    # quart
    "quarts": "quart",
    "qt": "quart",
    # gallon
    "gallons": "gallon",
    "gal": "gallon",
    # ounce (fluid or weight -- context will determine, treated as weight here)
    "oz": "ounce",
    "ozs": "ounce",
    "ounces": "ounce",
    "fl oz": "fluid_ounce",
    # pound
    "lb": "pound",
    "lbs": "pound",
    "pounds": "pound",
    # gram
    "g": "gram",
    "grams": "gram",
    "gr": "gram",
    # kilogram
    "kg": "kilogram",
    "kilograms": "kilogram",
    "kgs": "kilogram",
    # milligram
    "mg": "milligram",
    "milligrams": "milligram",
    # milliliter
    "ml": "milliliter",
    "milliliters": "milliliter",
    "mls": "milliliter",
    # liter
    "l": "liter",
    "liters": "liter",
    "litre": "liter",
    "litres": "liter",
}

# Volume in tablespoons
VOLUME_TO_TBSP = {
    "teaspoon": 1 / 3,
    "tablespoon": 1,
    "fluid_ounce": 2,
    "cup": 16,
    "pint": 32,
    "quart": 64,
    "gallon": 256,
    "milliliter": 1 / 14.7868,
    "liter": 1000 / 14.7868,
}

# Weight in ounces
WEIGHT_TO_OZ = {
    "ounce": 1,
    "pound": 16,
    "gram": 0.035274,
    "kilogram": 35.274,
    "milligram": 0.000035274,
}

_SECTION_KEYWORDS = {
    "meat": [
        "chicken", "beef", "pork", "turkey", "lamb", "salmon", "tuna", "shrimp",
        "bacon", "ham", "sausage", "steak", "ground beef", "ground turkey",
        "fish", "crab", "lobster", "scallop", "anchovy", "sardine",
    ],
    "produce": [
        "apple", "banana", "orange", "lemon", "lime", "grape", "berry",
        "strawberry", "blueberry", "raspberry", "peach", "pear", "mango",
        "pineapple", "watermelon", "melon", "avocado", "tomato", "potato",
        "onion", "garlic", "carrot", "celery", "broccoli", "spinach",
        "lettuce", "kale", "cucumber", "pepper", "zucchini", "squash",
        "mushroom", "asparagus", "corn", "bean", "pea", "cabbage",
        "cauliflower", "eggplant", "ginger", "herb", "cilantro", "parsley",
        "basil", "mint", "rosemary", "thyme", "dill", "chive",
    ],
    "dairy": [
        "milk", "cream", "butter", "cheese", "yogurt", "egg", "eggs",
        "sour cream", "cream cheese", "mozzarella", "cheddar", "parmesan",
        "brie", "feta", "ricotta", "half and half", "heavy cream",
        "whipped cream", "ice cream",
    ],
    "bakery": [
        "bread", "bun", "roll", "bagel", "muffin", "croissant", "tortilla",
        "pita", "naan", "baguette", "loaf", "cake", "cookie", "donut",
        "pastry", "pie crust",
    ],
    "frozen": [
        "frozen", "ice cream", "edamame", "frozen peas", "frozen corn",
        "frozen berry", "frozen pizza",
    ],
    "canned": [
        "canned", "can of", "tomato paste", "tomato sauce", "diced tomato",
        "crushed tomato", "coconut milk", "broth", "stock", "soup",
        "beans", "chickpea", "lentil", "black bean", "kidney bean",
    ],
    "pantry": [
        "oil", "olive oil", "vegetable oil", "canola oil", "sesame oil",
        "vinegar", "soy sauce", "salt", "pepper", "sugar", "flour",
        "baking", "spice", "sauce", "pasta", "rice", "noodle", "oat",
        "cereal", "cracker", "chip", "nut", "almond", "walnut", "peanut",
        "honey", "jam", "syrup", "ketchup", "mustard", "mayo", "mayonnaise",
        "hot sauce", "worcestershire", "fish sauce", "oyster sauce",
        "hoisin", "sriracha", "tahini", "peanut butter", "cocoa",
        "chocolate", "vanilla", "yeast", "baking powder", "baking soda",
        "cornstarch", "breadcrumb", "panko",
    ],
}

# Pre-compile regex patterns for store section inference (issue 12)
_COMPILED_SECTIONS = {
    section: [re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE) for kw in keywords]
    for section, keywords in _SECTION_KEYWORDS.items()
}


def normalize_unit(unit: str) -> str:
    """Lowercase, strip, look up in aliases, return canonical or original."""
    if not unit:
        return unit
    cleaned = unit.strip().lower()
    return UNIT_ALIASES.get(cleaned, cleaned)


def can_combine(unit1: str, unit2: str) -> bool:
    """True if same normalized unit, or both volume, or both weight."""
    u1 = normalize_unit(unit1)
    u2 = normalize_unit(unit2)
    if u1 == u2:
        return True
    both_volume = u1 in VOLUME_TO_TBSP and u2 in VOLUME_TO_TBSP
    both_weight = u1 in WEIGHT_TO_OZ and u2 in WEIGHT_TO_OZ
    return both_volume or both_weight


def combine_quantities(qty1: float, unit1: str, qty2: float, unit2: str):
    """Convert to base unit, sum, convert back to the larger unit.

    Returns (quantity, unit) tuple.
    """
    u1 = normalize_unit(unit1)
    u2 = normalize_unit(unit2)

    # Volume path
    if u1 in VOLUME_TO_TBSP and u2 in VOLUME_TO_TBSP:
        base1 = qty1 * VOLUME_TO_TBSP[u1]
        base2 = qty2 * VOLUME_TO_TBSP[u2]
        total_tbsp = base1 + base2
        # Pick the larger unit that fits evenly-ish (use whichever has larger factor)
        larger_unit = u1 if VOLUME_TO_TBSP[u1] >= VOLUME_TO_TBSP[u2] else u2
        result = total_tbsp / VOLUME_TO_TBSP[larger_unit]
        return (result, larger_unit)

    # Weight path
    if u1 in WEIGHT_TO_OZ and u2 in WEIGHT_TO_OZ:
        base1 = qty1 * WEIGHT_TO_OZ[u1]
        base2 = qty2 * WEIGHT_TO_OZ[u2]
        total_oz = base1 + base2
        larger_unit = u1 if WEIGHT_TO_OZ[u1] >= WEIGHT_TO_OZ[u2] else u2
        result = total_oz / WEIGHT_TO_OZ[larger_unit]
        return (result, larger_unit)

    raise ValueError(f"Cannot combine units {unit1!r} and {unit2!r}")


def infer_store_section(ingredient_name: str) -> str:
    """Keyword-based mapping of ingredient name to a store section.

    Returns one of: meat, produce, dairy, pantry, bakery, frozen, canned, other.
    """
    lower = ingredient_name.lower()
    for section, patterns in _COMPILED_SECTIONS.items():
        for pattern in patterns:
            if pattern.search(lower):
                return section
    return "other"
