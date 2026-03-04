"""Tests for the recommendation engine."""

import pytest
from app.services.recommendation_engine import generate_recommendations


def test_on_track():
    recs = generate_recommendations(2000, 130, 2000, 130, [])
    assert any("on track" in r.lower() for r in recs)


def test_under_500_calories():
    recs = generate_recommendations(1200, 130, 2000, 130, [])
    assert any("800 cal under" in r for r in recs)


def test_small_deficit_is_on_track():
    # A 150-cal deficit is within normal range — no warning should fire
    recs = generate_recommendations(1850, 130, 2000, 130, [])
    assert any("on track" in r.lower() for r in recs)


def test_over_calories():
    recs = generate_recommendations(2400, 130, 2000, 130, [])
    assert any("exceeded" in r.lower() for r in recs)


def test_low_protein():
    recs = generate_recommendations(2000, 50, 2000, 130, [])
    assert any("protein" in r.lower() for r in recs)


def test_low_iron():
    recs = generate_recommendations(2000, 130, 2000, 130, ["Iron"])
    assert any("iron" in r.lower() for r in recs)


def test_low_calcium():
    recs = generate_recommendations(2000, 130, 2000, 130, ["Calcium"])
    assert any("calcium" in r.lower() for r in recs)


def test_multiple_low_nutrients():
    recs = generate_recommendations(2000, 130, 2000, 130, ["Iron", "Vitamin D", "Zinc"])
    assert len(recs) == 3  # One rec per nutrient


def test_unknown_nutrient_ignored():
    # Should not crash on unknown nutrient names
    recs = generate_recommendations(2000, 130, 2000, 130, ["XYZ_Nutrient"])
    assert isinstance(recs, list)
