"""Tests for unit normalization utilities."""
import pytest

from grecipe.units import (
    normalize_unit,
    can_combine,
    combine_quantities,
    infer_store_section,
)


def test_normalize_unit():
    assert normalize_unit("tbsp") == "tablespoon"
    assert normalize_unit("Cups") == "cup"
    assert normalize_unit("oz") == "ounce"
    assert normalize_unit("lbs") == "pound"
    assert normalize_unit("tsp") == "teaspoon"
    # Already canonical
    assert normalize_unit("tablespoon") == "tablespoon"
    # Unknown unit passes through lowercased
    assert normalize_unit("pinch") == "pinch"


def test_can_combine():
    # Same normalized unit
    assert can_combine("cup", "cup") is True
    # Both volume
    assert can_combine("cup", "tablespoon") is True
    assert can_combine("tbsp", "teaspoon") is True
    # Both weight
    assert can_combine("lb", "pound") is True
    assert can_combine("ounce", "gram") is True
    # Volume vs weight — incompatible
    assert can_combine("cup", "ounce") is False
    assert can_combine("tablespoon", "gram") is False


def test_combine_tablespoons_into_cups():
    qty, unit = combine_quantities(0.5, "cup", 4, "tbsp")
    assert unit == "cup"
    assert abs(qty - 0.75) < 1e-9


def test_infer_store_section():
    assert infer_store_section("chicken breast") == "meat"
    assert infer_store_section("whole milk") == "dairy"
    assert infer_store_section("banana") == "produce"
    assert infer_store_section("olive oil") == "pantry"
    # Unknown ingredient
    assert infer_store_section("unicorn tears") == "other"
