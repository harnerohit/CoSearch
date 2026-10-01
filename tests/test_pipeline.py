"""Step 8: pipeline outcomes against the real listings.json (fake parse, no network)."""

import datetime
from types import SimpleNamespace

import pytest

import src.pipeline as pipeline
from src import config
from src.filters import check_listing, passes
from src.llm import LLMError
from src.parser import ParseError
from src.schemas import Outcome, ParsedQuery

FRIDAY = datetime.date(2026, 10, 2)  # a date the headline query matches on real data
COVERED = ", ".join(config.AREAS)


@pytest.fixture(autouse=True)
def no_llm_calls(monkeypatch):
    """Ensure no real network calls are made by the explainer during pipeline tests."""
    from src.llm import LLMError
    def raise_err(*args, **kwargs):
        raise LLMError("Unmocked LLM call in tests!")
    monkeypatch.setattr("src.explainer.complete_json", raise_err)


@pytest.fixture
def fake_parse(monkeypatch):
    """Replace parse with a canned recorder (stands in for the one LLM call)."""
    state = SimpleNamespace(calls=[], answer=None, error=None)

    def fake(query: str):
        state.calls.append(query)
        if state.error is not None:
            raise state.error
        return state.answer

    monkeypatch.setattr(pipeline, "parse", fake)
    return state


def test_headline_query_returns_results(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate(
        {
            "location": "Bandra",
            "party_size": 4,
            "budget": {"amount": 600, "basis": "per_person_per_hour"},
            "date": FRIDAY,
            "time_window": {"start": "12:00", "end": "17:00"},
            "soft": {"quiet": True, "min_wifi": "fast", "amenities": ["whiteboard"]},
        }
    )
    response = pipeline.search(
        "Quiet place for 4 people in Bandra tomorrow afternoon, fast wifi, "
        "under 600 per person per hour, ideally with a whiteboard."
    )
    assert response.outcome is Outcome.RESULTS
    assert 0 < len(response.results) <= config.TOP_N
    assert response.parsed_query is not None


def test_results_have_zero_hard_constraint_violations(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate({"location": "Powai"})
    response = pipeline.search("somewhere in Powai")
    assert response.outcome is Outcome.RESULTS
    assert response.parsed_query is not None
    for item in response.results:
        assert passes(check_listing(item.listing, response.parsed_query))


def test_vague_query_clarifies(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate({})
    response = pipeline.search("somewhere nice to work")
    assert response.outcome is Outcome.CLARIFY
    assert response.results == []
    assert response.parsed_query is not None
    assert response.message is not None
    assert "We cover these Mumbai areas" in response.message


def test_bare_mumbai_asks_for_an_area(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate({"unrecognized_location": "Mumbai"})
    response = pipeline.search("Mumbai")
    assert response.outcome is Outcome.CLARIFY
    assert response.message == config.MSG_CITY_NO_AREA.format(areas=COVERED)
    assert "Which area of Mumbai?" in response.message


def test_pune_gets_coverage_message(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate({"unrecognized_location": "Pune"})
    response = pipeline.search("Pune")
    assert response.outcome is Outcome.CLARIFY
    assert response.message == config.MSG_COVERAGE.format(area="Pune", areas=COVERED)
    assert "Lower Parel" in response.message


def test_navi_mumbai_gets_coverage_not_the_area_question(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate(
        {"unrecognized_location": "Navi Mumbai"}
    )
    response = pipeline.search("Navi Mumbai")
    assert response.outcome is Outcome.CLARIFY
    assert response.message == config.MSG_COVERAGE.format(
        area="Navi Mumbai", areas=COVERED
    )
    assert "Which area of Mumbai?" not in response.message
    assert "Lower Parel" in response.message


def test_parel_gets_coverage_message(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate({"unrecognized_location": "Parel"})
    response = pipeline.search("Parel")
    assert response.outcome is Outcome.CLARIFY
    assert response.message == config.MSG_COVERAGE.format(area="Parel", areas=COVERED)
    assert "Which area of Mumbai?" not in response.message
    assert "Lower Parel" in response.message


def test_large_group_tiny_budget_is_not_results(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate(
        {
            "location": "Bandra",
            "party_size": 15,
            "budget": {"amount": 50, "basis": "total_per_hour"},
            "date": FRIDAY,
        }
    )
    response = pipeline.search("15 people in Bandra, 50 rupees total per hour tomorrow")
    assert response.outcome is not Outcome.RESULTS
    assert all(item.listing.capacity >= 15 for item in response.results)


def test_impossible_group_is_no_match(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate({"party_size": 500})
    response = pipeline.search("500 people")
    assert response.outcome is Outcome.NO_MATCH
    assert response.results == []
    assert response.message is not None
    assert "capacity" in response.message


def test_hot_desk_for_four_never_matches_smaller_listings(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate(
        {"party_size": 4, "space_type": "hot_desk"}
    )
    response = pipeline.search("hot desk for 4 people")
    assert response.outcome is not Outcome.RESULTS
    assert all(item.listing.capacity >= 4 for item in response.results)


def test_llm_error_returns_friendly_clarify(fake_parse):
    fake_parse.error = LLMError("provider unavailable")
    response = pipeline.search("quiet desk in Bandra")
    assert response.outcome is Outcome.CLARIFY
    assert response.parsed_query is None
    assert response.message is not None
    assert "something went wrong" in response.message.lower()
    assert "try again" in response.message.lower()
    assert "Traceback" not in response.message
    assert not any(
        word in response.message.lower()
        for word in ("area", "budget", "location", "group size")
    )


def test_parse_error_returns_friendly_clarify(fake_parse):
    fake_parse.error = ParseError("invalid JSON after retry")
    response = pipeline.search("quiet desk in Bandra")
    assert response.outcome is Outcome.CLARIFY
    assert response.parsed_query is None
    assert response.message is not None
    assert "something went wrong" in response.message.lower()
    assert "try again" in response.message.lower()
    assert "Traceback" not in response.message
    assert not any(
        word in response.message.lower()
        for word in ("area", "budget", "location", "group size")
    )


def test_empty_input_skips_the_llm(fake_parse):
    fake_parse.answer = ParsedQuery.model_validate({})
    for query in ("", "   "):
        response = pipeline.search(query)
        assert response.outcome is Outcome.CLARIFY
        assert response.message == config.MSG_EMPTY_QUERY
        assert response.parsed_query is None
    assert fake_parse.calls == []
