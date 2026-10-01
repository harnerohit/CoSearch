import json
from unittest.mock import patch
from src.schemas import Listing, SpaceType, NoiseLevel, ResultItem, ParsedQuery
from src.explainer import explain_results
from src.llm import LLMError

def make_listing(id: str) -> Listing:
    return Listing(
        id=id, name="Test Space", space_type=SpaceType.HOT_DESK, area="Bandra",
        address="123 Test", lat=19.0596, lng=72.8295, capacity=2,
        price_per_hour=150, noise_level=NoiseLevel.QUIET, wifi_mbps=100,
        amenities=[], rating=4.5, review_count=10, availability=[]
    )

@patch("src.explainer.complete_json")
def test_explainer_valid(mock_complete):
    mock_complete.return_value = {"L001": "It costs 150."}
    item = ResultItem(rank=1, listing=make_listing("L001"), score=1.0)
    explain_results([item], ParsedQuery(), False)
    assert item.explanation == "It costs 150."
    assert item.explanation_source == "llm"

@patch("src.explainer.complete_json")
def test_explainer_invalid_falls_back(mock_complete):
    mock_complete.return_value = {"L001": "It costs 9999."}
    item = ResultItem(rank=1, listing=make_listing("L001"), score=1.0)
    explain_results([item], ParsedQuery(), False)
    assert item.explanation_source == "template"

@patch("src.explainer.complete_json")
def test_explainer_llmerror_falls_back(mock_complete):
    mock_complete.side_effect = LLMError("API down")
    item = ResultItem(rank=1, listing=make_listing("L001"), score=1.0)
    explain_results([item], ParsedQuery(), False)
    assert item.explanation_source == "template"

@patch("src.explainer.complete_json")
def test_missing_unknown_id_invalid(mock_complete):
    mock_complete.return_value = {"UNKNOWN": "It costs 150."}
    item = ResultItem(rank=1, listing=make_listing("L001"), score=1.0)
    explain_results([item], ParsedQuery(), False)
    assert item.explanation_source == "template"
