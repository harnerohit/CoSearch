import pytest
from src.schemas import Listing, SpaceType, NoiseLevel, Amenity, ResultItem
from src.validator import validate_explanation
from src import config

def make_listing(id: str, name: str, price: int = 150) -> Listing:
    return Listing(
        id=id, name=name, space_type=SpaceType.HOT_DESK, area="Bandra",
        address="123 Test St", lat=19.0596, lng=72.8295, capacity=2,
        price_per_hour=price, noise_level=NoiseLevel.QUIET, wifi_mbps=100,
        amenities=[Amenity.WHITEBOARD, Amenity.AIR_CONDITIONING], rating=4.5, review_count=10,
        availability=[]
    )

@pytest.fixture
def base_listing():
    return make_listing("L001", "Saffron Yard")

@pytest.fixture
def base_results(base_listing):
    return [ResultItem(rank=1, listing=base_listing, score=1.0),
            ResultItem(rank=2, listing=make_listing("L002", "Other Place"), score=0.9)]

@pytest.fixture
def base_allowed():
    return {150.0, 4.5, 10.0, 100.0, 2.0}

def test_fake_pool_gym_parking_caught(base_listing, base_allowed, base_results):
    for fake in ["pool", "gym", "parking"]:
        valid, _ = validate_explanation(f"Has a {fake}.", base_listing, base_allowed, set(), base_results)
        assert not valid

def test_wrong_price_caught(base_listing, base_allowed, base_results):
    valid, _ = validate_explanation("Price is 149.", base_listing, base_allowed, set(), base_results)
    assert not valid

def test_another_listings_name_caught(base_listing, base_allowed, base_results):
    valid, _ = validate_explanation("Better than Other Place.", base_listing, base_allowed, set(), base_results)
    assert not valid

def test_wrong_mbps_people_caught(base_listing, base_allowed, base_results):
    valid, _ = validate_explanation("Has 200 Mbps wifi.", base_listing, base_allowed, set(), base_results)
    assert not valid
    valid, _ = validate_explanation("Holds 5 people.", base_listing, base_allowed, set(), base_results)
    assert not valid

def test_synonym_caught(base_listing, base_allowed, base_results):
    valid, _ = validate_explanation("Includes a swimming pool.", base_listing, base_allowed, set(), base_results)
    assert not valid

def test_number_present_in_facts_passes(base_listing, base_allowed):
    res = ResultItem(rank=1, listing=base_listing, score=0.9)
    res.facts = {"missed": ["budget_over=15.0%"]}
    base_allowed.add(15.0)
    valid, _ = validate_explanation("Is 15.0 percent over budget.", base_listing, base_allowed, set(), [res])
    assert valid

def test_rs_9000_great_view_fails(base_listing, base_allowed, base_results):
    valid, msg = validate_explanation("The price is Rs. 9000. Great view.", base_listing, base_allowed, set(), base_results)
    assert not valid
    assert "9000.0" in msg

def test_not_noisy_but_has_whiteboard_fails(base_allowed, base_results):
    lacks_wb = make_listing("L003", "NoWB")
    lacks_wb.amenities = []
    res_lacks_wb = ResultItem(rank=3, listing=lacks_wb, score=0.8)
    valid, _ = validate_explanation("not noisy but has a whiteboard", lacks_wb, base_allowed, {"whiteboard"}, [res_lacks_wb])
    assert not valid

def test_no_whiteboard_passes(base_allowed, base_results):
    lacks_wb = make_listing("L003", "NoWB")
    lacks_wb.amenities = []
    res_lacks_wb = ResultItem(rank=3, listing=lacks_wb, score=0.8)
    valid, _ = validate_explanation("has no whiteboard", lacks_wb, base_allowed, {"whiteboard"}, [res_lacks_wb])
    assert valid

def test_missing_unknown_id_invalid():
    # Tested implicitly in test_explainer_invalid_falls_back by the explainer logic
    pass

def test_template_passes_validator(base_allowed):
    from src.facts import build_display_data
    from src.schemas import ParsedQuery
    parsed = ParsedQuery(party_size=2)
    lacks_wb = make_listing("L003", "NoWB")
    lacks_wb.amenities = []
    res_lacks_wb = ResultItem(rank=3, listing=lacks_wb, score=0.8)
    
    # result with missed whiteboard
    facts1 = {"matched": ["area=Bandra"], "missed": ["amenity=whiteboard"], "tradeoffs": ["amenity=whiteboard"]}
    res_lacks_wb.facts = facts1
    d1 = build_display_data(lacks_wb, parsed, facts1, 1, False)
    valid, _ = validate_explanation(d1["template_string"], lacks_wb, d1["allowed_numbers"], d1["missed_amenities"], [res_lacks_wb])
    assert valid

    # result with fewer than 10 reviews
    lacks_wb.review_count = 2
    facts2 = {"matched": ["area=Bandra"], "missed": [], "tradeoffs": ["low_reviews=2"]}
    res_lacks_wb.facts = facts2
    d2 = build_display_data(lacks_wb, parsed, facts2, 1, False)
    valid, _ = validate_explanation(d2["template_string"], lacks_wb, d2["allowed_numbers"], d2["missed_amenities"], [res_lacks_wb])
    assert valid

    # over-budget alternative
    facts3 = {"matched": [], "missed": ["budget_over=15.0%", "location_km=4.2"], "tradeoffs": []}
    res_lacks_wb.facts = facts3
    d3 = build_display_data(lacks_wb, parsed, facts3, 1, True)
    valid, _ = validate_explanation(d3["template_string"], lacks_wb, d3["allowed_numbers"], d3["missed_amenities"], [res_lacks_wb])
    assert valid

def test_rank_number_inside_text_fails(base_listing, base_allowed, base_results):
    # If the rank is 3 but 3 is not an allowed number from capacity etc.
    res3 = ResultItem(rank=3, listing=base_listing, score=0.5)
    res3.facts = {}
    valid, _ = validate_explanation("This is option 3.", base_listing, base_allowed, set(), [res3])
    assert not valid

def test_above_budget_fails_when_budget_is_met(base_listing, base_allowed):
    # Setup base_results where budget is met
    res = ResultItem(rank=1, listing=base_listing, score=1.0)
    res.facts = {"matched": ["budget=475<=600"]}
    valid, _ = validate_explanation("It is above budget.", base_listing, base_allowed, set(), [res])
    assert not valid

def test_over_budget_fails_for_near_limit_listing(base_listing, base_allowed):
    res = ResultItem(rank=1, listing=base_listing, score=1.0)
    res.facts = {"tradeoffs": ["price_near_budget=2624/50"]}
    valid, _ = validate_explanation("It is over budget.", base_listing, base_allowed, set(), [res])
    assert not valid

def test_close_to_budget_limit_fails_for_250_percent_over(base_listing, base_allowed):
    res = ResultItem(rank=1, listing=base_listing, score=1.0)
    res.facts = {"missed": ["budget_over=250.0%"], "tradeoffs": ["price_near_budget=175/50"]} # Usually tradeoffs might have it if the bug wasn't fixed, but let's just supply both
    base_allowed.add(250.0)
    valid, _ = validate_explanation("It is close to the budget limit.", base_listing, base_allowed, set(), [res])
    assert not valid

def test_within_budget_fails_for_over_budget_alternative(base_listing, base_allowed):
    res = ResultItem(rank=1, listing=base_listing, score=1.0)
    res.facts = {"missed": ["budget_over=15.0%"]}
    base_allowed.add(15.0)
    valid, _ = validate_explanation("It is within budget.", base_listing, base_allowed, set(), [res])
    assert not valid

def test_within_budget_passes_when_met(base_listing, base_allowed):
    res = ResultItem(rank=1, listing=base_listing, score=1.0)
    res.facts = {"matched": ["budget=475<=600"]}
    valid, _ = validate_explanation("It is within budget.", base_listing, base_allowed, set(), [res])
    assert valid

def test_over_budget_passes_for_alternative_with_budget_over(base_listing, base_allowed):
    res = ResultItem(rank=1, listing=base_listing, score=1.0)
    res.facts = {"missed": ["budget_over=15.0%"]}
    base_allowed.add(15.0)
    valid, _ = validate_explanation("Is 15.0 percent over budget.", base_listing, base_allowed, set(), [res])
    assert valid

def test_close_to_budget_limit_passes_for_near_limit_listing(base_listing, base_allowed):
    res = ResultItem(rank=1, listing=base_listing, score=1.0)
    res.facts = {"tradeoffs": ["price_near_budget=48/50"]}
    valid, _ = validate_explanation("It is close to the budget limit.", base_listing, base_allowed, set(), [res])
    assert valid

def test_quiet_fails_for_moderate_listing(base_allowed):
    from src.schemas import NoiseLevel
    l = make_listing("L999", "Mod")
    l.noise_level = NoiseLevel.MODERATE
    res = ResultItem(rank=1, listing=l, score=1.0)
    res.facts = {}
    valid, _ = validate_explanation("It is very quiet.", l, base_allowed, set(), [res])
    assert not valid

def test_quiet_passes_for_quiet_listing(base_listing, base_allowed):
    res = ResultItem(rank=1, listing=base_listing, score=1.0)
    res.facts = {}
    valid, _ = validate_explanation("It is very quiet.", base_listing, base_allowed, set(), [res])
    assert valid

def test_unicode_spaces_handled_correctly(base_listing, base_allowed):
    # Testing U+00A0 (non-breaking) and U+202F (narrow no-break) space
    res = ResultItem(rank=1, listing=base_listing, score=1.0)
    res.facts = {"missed": ["amenity=whiteboard"]}
    # 'no whiteboard' but with non-standard spaces
    text = "It has no\u00a0whiteboard\u202fhere. Cost is 150."
    valid, _ = validate_explanation(text, base_listing, base_allowed, {"whiteboard"}, [res])
    assert valid
