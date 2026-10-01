"""Step 5: scoring, weight renormalization, deterministic order, tie-breaks, facts."""

import datetime
from collections.abc import Callable

import pytest

from src import config
from src.data_loader import load_listings
from src.facts import compute_facts
from src.filters import check_listing, passes
from src.ranker import mean_rating, rank, score, trust
from src.schemas import Budget, BudgetBasis, Listing, ParsedQuery, TimeWindow


def test_trust_does_not_overreward_a_tiny_sample(make_listing: Callable[..., Listing]) -> None:
    """A 5.0 from 2 reviews must not beat 4.7 from 200 (Section 7)."""
    hero = make_listing(id="L001", rating=5.0, review_count=2)
    steady = make_listing(id="L002", rating=4.7, review_count=200)
    filler = [
        make_listing(id="L003", rating=4.0, review_count=100),
        make_listing(id="L004", rating=3.9, review_count=80),
    ]
    dataset = [hero, steady, *filler]
    dataset_mean = mean_rating(dataset)
    parsed = ParsedQuery(party_size=2)  # no budget, no soft preferences: score = trust
    scores = {item.id: score(item, parsed, dataset_mean)[0] for item in dataset}
    assert scores["L002"] > scores["L001"]
    assert trust(steady, dataset_mean) > trust(hero, dataset_mean)


def test_zero_reviews_falls_back_to_dataset_mean(make_listing: Callable[..., Listing]) -> None:
    """Zero reviews yields exactly the prior (mean / 5), never a free boost or a zero."""
    zero = make_listing(rating=None, review_count=0)
    dataset_mean = 4.4
    assert trust(zero, dataset_mean) == pytest.approx(dataset_mean / config.RATING_MAX)


def test_weights_renormalize_without_budget(make_listing: Callable[..., Listing]) -> None:
    """No budget: the price term drops and fit/trust weights renormalize to 1."""
    listing = make_listing()
    parsed = ParsedQuery(soft={"quiet": True})
    _, breakdown = score(listing, parsed, 4.4)
    assert "price_fit" not in breakdown
    total_weight = config.W_FIT + config.W_TRUST
    assert breakdown["weight_soft_match"] == pytest.approx(config.W_FIT / total_weight)
    assert breakdown["weight_trust"] == pytest.approx(config.W_TRUST / total_weight)
    assert breakdown["weight_soft_match"] + breakdown["weight_trust"] == pytest.approx(1.0)


def test_weights_renormalize_without_soft_preferences(make_listing: Callable[..., Listing]) -> None:
    """No soft preferences: the fit term drops and trust/price weights renormalize."""
    listing = make_listing()
    parsed = ParsedQuery(budget=Budget(amount=3000, basis=BudgetBasis.TOTAL_PER_HOUR))
    _, breakdown = score(listing, parsed, 4.4)
    assert "soft_match" not in breakdown
    total_weight = config.W_TRUST + config.W_PRICE
    assert breakdown["weight_trust"] == pytest.approx(config.W_TRUST / total_weight)
    assert breakdown["weight_price_fit"] == pytest.approx(config.W_PRICE / total_weight)


def test_only_trust_active_when_nothing_stated(make_listing: Callable[..., Listing]) -> None:
    """Neither budget nor soft preferences: trust alone carries the score at weight 1."""
    listing = make_listing()
    total, breakdown = score(listing, ParsedQuery(), 4.4)
    assert list(breakdown) == ["trust", "weight_trust"]
    assert breakdown["weight_trust"] == 1.0
    assert total == pytest.approx(trust(listing, 4.4))


def test_full_weights_applied_and_score_reconstructs(make_listing: Callable[..., Listing]) -> None:
    """With both terms active the configured weights apply and the score is their sum."""
    listing = make_listing()
    parsed = ParsedQuery(
        party_size=2,
        budget=Budget(amount=3000, basis=BudgetBasis.TOTAL_PER_HOUR),
        soft={"quiet": True},
    )
    total, breakdown = score(listing, parsed, 4.4)
    assert breakdown["weight_soft_match"] == pytest.approx(config.W_FIT)
    assert breakdown["weight_trust"] == pytest.approx(config.W_TRUST)
    assert breakdown["weight_price_fit"] == pytest.approx(config.W_PRICE)
    reconstructed = (
        breakdown["weight_soft_match"] * breakdown["soft_match"]
        + breakdown["weight_trust"] * breakdown["trust"]
        + breakdown["weight_price_fit"] * breakdown["price_fit"]
    )
    assert total == pytest.approx(reconstructed)


def test_rank_is_deterministic_and_ties_break_by_lower_id(make_listing: Callable[..., Listing]) -> None:
    """Identical listings tie on score and trust, so the lower id wins in any input order."""
    first = make_listing(id="L001")
    second = make_listing(id="L002")
    parsed = ParsedQuery(party_size=2)
    dataset_mean = mean_rating([first, second])
    forward = rank([first, second], parsed, dataset_mean)
    backward = rank([second, first], parsed, dataset_mean)
    assert [item.id for item, _, _ in forward] == ["L001", "L002"]
    assert [item.id for item, _, _ in backward] == ["L001", "L002"]
    assert forward[0][1] == pytest.approx(forward[1][1])  # a pure tie


def test_rank_orders_highest_score_first(make_listing: Callable[..., Listing]) -> None:
    """Order is score descending with no dependence on input order."""
    low = make_listing(id="L003", rating=3.5, review_count=120)
    high = make_listing(id="L004", rating=4.9, review_count=150)
    mid = make_listing(id="L005", rating=4.2, review_count=60)
    dataset_mean = mean_rating([low, high, mid])
    ranked = rank([low, high, mid], ParsedQuery(), dataset_mean)
    scores = [entry for _, entry, _ in ranked]
    assert scores == sorted(scores, reverse=True)
    assert [item.id for item, _, _ in ranked] == ["L004", "L005", "L003"]


def test_facts_for_known_real_listing() -> None:
    """L001 (Marigold Loft) against a query it satisfies: facts must match the data exactly."""
    listing = next(item for item in load_listings() if item.id == "L001")
    parsed = ParsedQuery(
        location="Bandra",
        party_size=4,
        budget=Budget(amount=650, basis=BudgetBasis.PER_PERSON_PER_HOUR),
        date=datetime.date(2026, 10, 5),
        time_window=TimeWindow(start="12:00", end="17:00"),
        soft={"quiet": True, "min_wifi": "fast", "amenities": ["whiteboard", "printer"]},
    )
    violations = check_listing(listing, parsed)
    assert passes(violations)
    facts = compute_facts(listing, parsed, violations)
    assert facts["matched"] == [
        "area=Bandra",
        "capacity=4>=4",
        "budget=625<=650",
        "availability=2026-10-05 12:00-17:00",
        "noise=quiet",
        "wifi=150>=100",
        "amenity=whiteboard",
    ]
    assert facts["missed"] == ["amenity=printer"]
    assert facts["tradeoffs"] == ["price_near_budget=625/650", "amenity=printer"]


def test_facts_include_violation_sizes_for_real_listing() -> None:
    """Violated hard constraints reuse filters.Violations and carry their sizes."""
    listing = next(item for item in load_listings() if item.id == "L001")
    parsed = ParsedQuery(
        location="Bandra",
        party_size=6,
        budget=Budget(amount=400, basis=BudgetBasis.PER_PERSON_PER_HOUR),
    )
    violations = check_listing(listing, parsed)
    assert not passes(violations)
    facts = compute_facts(listing, parsed, violations)
    assert "capacity_short=2" in facts["missed"]
    assert "budget_over=4.2%" in facts["missed"]
    assert "capacity_short=2" in facts["tradeoffs"]
    assert "budget_over=4.2%" in facts["tradeoffs"]
    assert "price_near_budget=416.667/400" not in facts["tradeoffs"]
