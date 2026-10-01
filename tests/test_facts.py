import pytest
from src.schemas import Listing, SpaceType, NoiseLevel, ParsedQuery, Budget, BudgetBasis, Violations
from src.facts import hard_facts, build_display_data

def test_over_budget_alternative_has_no_price_near_budget(make_listing):
    base_listing = make_listing()
    parsed = ParsedQuery(
        budget=Budget(amount=100, basis=BudgetBasis.TOTAL_PER_HOUR)
    )
    base_listing.price_per_hour = 350
    violations = Violations(budget_over_pct=250.0)
    
    facts = hard_facts(base_listing, parsed, violations)
    assert "budget_over=250.0%" in facts["missed"]
    assert "budget_over=250.0%" in facts["tradeoffs"]
    assert not any(t.startswith("price_near_budget") for t in facts["tradeoffs"])

def test_listing_at_90_percent_of_limit_has_near_budget(make_listing):
    base_listing = make_listing()
    parsed = ParsedQuery(
        budget=Budget(amount=100, basis=BudgetBasis.TOTAL_PER_HOUR)
    )
    base_listing.price_per_hour = 90
    violations = Violations(budget_over_pct=0.0)
    
    facts = hard_facts(base_listing, parsed, violations)
    assert not any(t.startswith("budget_over") for t in facts["missed"])
    assert "budget=90<=100" in facts["matched"]
    assert "price_near_budget=90/100" in facts["tradeoffs"]

def test_budget_over_in_facts_equals_violations(make_listing):
    base_listing = make_listing()
    parsed = ParsedQuery(
        budget=Budget(amount=100, basis=BudgetBasis.TOTAL_PER_HOUR)
    )
    base_listing.price_per_hour = 125
    violations = Violations(budget_over_pct=25.0)
    facts = hard_facts(base_listing, parsed, violations)
    assert "budget_over=25.0%" in facts["missed"]
    
def test_template_wording_alternative(make_listing):
    base_listing = make_listing()
    parsed = ParsedQuery()
    facts = {
        "matched": [],
        "missed": ["budget_over=250.0%", "location_km=4.0"],
        "tradeoffs": ["budget_over=250.0%", "location_km=4.0"]
    }
    data = build_display_data(base_listing, parsed, facts, 1, is_alternative=True)
    assert data["template_string"] == "Closest option, but it is 250% over budget and 4.0 km away."

def test_template_wording_result(make_listing):
    base_listing = make_listing()
    parsed = ParsedQuery(party_size=4)
    facts = {
        "matched": ["area=Bandra", "capacity=4>=4", "budget=100<=100"],
        "missed": ["amenity=whiteboard"],
        "tradeoffs": ["amenity=whiteboard"]
    }
    data = build_display_data(base_listing, parsed, facts, 1, is_alternative=False)
    assert data["template_string"] == "Fits your area, capacity and within budget; trade-off: it has no whiteboard."
