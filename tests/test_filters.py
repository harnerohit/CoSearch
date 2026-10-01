"""Step 4: hard-constraint boundaries (capacity, budget, availability, area, space type)."""

import datetime
from collections.abc import Callable

import pytest

from src import config
from src.filters import (
    availability_shortfall,
    budget_price,
    check_listing,
    count,
    passes,
)
from src.schemas import Budget, BudgetBasis, Listing, ParsedQuery, SpaceType, TimeWindow

MONDAY = datetime.date(2026, 10, 5)  # a real Monday: 2026-10-01 is a Thursday
SUNDAY = datetime.date(2026, 10, 4)  # a real Sunday


def test_capacity_exact_boundary(make_listing: Callable[..., Listing]) -> None:
    """Party equal to capacity passes; one extra person is short by exactly one."""
    listing = make_listing(capacity=4)
    exact = check_listing(listing, ParsedQuery(party_size=4))
    assert exact.capacity_short == 0
    assert passes(exact)
    over = check_listing(listing, ParsedQuery(party_size=5))
    assert over.capacity_short == 1
    assert not passes(over)


def test_budget_exact_boundary_total_basis(make_listing: Callable[..., Listing]) -> None:
    """Exactly at budget passes; one rupee over is a positive overage."""
    listing = make_listing(price_per_hour=2400)
    exact = check_listing(
        listing,
        ParsedQuery(budget=Budget(amount=2400, basis=BudgetBasis.TOTAL_PER_HOUR)),
    )
    assert exact.budget_over_pct == 0.0
    over = check_listing(
        listing,
        ParsedQuery(budget=Budget(amount=2399, basis=BudgetBasis.TOTAL_PER_HOUR)),
    )
    assert over.budget_over_pct == pytest.approx(100 / 2399)


def test_budget_per_person_versus_total_basis(make_listing: Callable[..., Listing]) -> None:
    """Per person divides by party size; total compares the unit price directly."""
    listing = make_listing(price_per_hour=2400)
    assert budget_price(listing, 4, BudgetBasis.PER_PERSON_PER_HOUR) == 600
    assert budget_price(listing, 4, BudgetBasis.TOTAL_PER_HOUR) == 2400
    per_person_ok = check_listing(
        listing,
        ParsedQuery(
            party_size=4,
            budget=Budget(amount=600, basis=BudgetBasis.PER_PERSON_PER_HOUR),
        ),
    )
    assert per_person_ok.budget_over_pct == 0.0
    same_amount_as_total = check_listing(
        listing,
        ParsedQuery(
            party_size=4,
            budget=Budget(amount=600, basis=BudgetBasis.TOTAL_PER_HOUR),
        ),
    )
    assert same_amount_as_total.budget_over_pct == pytest.approx(300.0)


def test_budget_without_party_size_defaults_to_one(make_listing: Callable[..., Listing]) -> None:
    """Missing party size means per-person pricing counts a single person."""
    listing = make_listing(price_per_hour=2400)
    assert (
        budget_price(listing, config.DEFAULT_PARTY_SIZE, BudgetBasis.PER_PERSON_PER_HOUR)
        == 2400
    )
    parsed = ParsedQuery(budget=Budget(amount=600, basis=BudgetBasis.PER_PERSON_PER_HOUR))
    assert check_listing(listing, parsed).budget_over_pct == pytest.approx(300.0)


def test_availability_full_afternoon_covers_request(make_listing: Callable[..., Listing]) -> None:
    """A 09:00-18:00 window fully covers the 12:00-17:00 afternoon."""
    listing = make_listing()
    assert (
        availability_shortfall(listing, MONDAY, TimeWindow(start="12:00", end="17:00"))
        == 0.0
    )


def test_availability_exact_two_hour_overlap_boundary(make_listing: Callable[..., Listing]) -> None:
    """Overlap of exactly min(MIN_BOOKING_HOURS, duration) passes; less shortfalls."""
    listing = make_listing()
    exact = TimeWindow(start="16:00", end="18:00")  # overlaps 16:00-18:00 = 2.0h
    assert availability_shortfall(listing, MONDAY, exact) == 0.0
    short = TimeWindow(start="16:30", end="18:30")  # overlaps 16:30-18:00 = 1.5h
    assert availability_shortfall(listing, MONDAY, short) == 0.5


def test_availability_request_shorter_than_min_booking(make_listing: Callable[..., Listing]) -> None:
    """A request under 2 hours is held to its own duration, not MIN_BOOKING_HOURS."""
    listing = make_listing()
    one_hour_exact = TimeWindow(start="17:00", end="18:00")  # overlap = 1.0h
    assert availability_shortfall(listing, MONDAY, one_hour_exact) == 0.0
    one_hour_short = TimeWindow(start="17:30", end="18:30")  # overlap = 0.5h
    assert availability_shortfall(listing, MONDAY, one_hour_short) == 0.5


def test_availability_no_date_skips_filter(make_listing: Callable[..., Listing]) -> None:
    """No date in the query means the availability filter never runs."""
    closed = make_listing(availability=[])
    assert availability_shortfall(closed, None, None) == 0.0
    assert check_listing(closed, ParsedQuery(party_size=4)).hours_short == 0.0


def test_availability_date_without_time(make_listing: Callable[..., Listing]) -> None:
    """Any window on the requested weekday passes; a closed weekday does not."""
    listing = make_listing()
    assert availability_shortfall(listing, MONDAY, None) == 0.0
    monday_only = make_listing(
        availability=[{"weekday": 0, "start": "09:00", "end": "18:00"}]
    )
    assert (
        availability_shortfall(monday_only, SUNDAY, None)
        == float(config.MIN_BOOKING_HOURS)
    )


def test_availability_closed_weekday_with_time_shortfalls_required_hours(
    make_listing: Callable[..., Listing],
) -> None:
    """Closed on the requested day: shortfall equals min(MIN_BOOKING_HOURS, duration)."""
    monday_only = make_listing(
        availability=[{"weekday": 0, "start": "09:00", "end": "18:00"}]
    )
    afternoon = TimeWindow(start="12:00", end="17:00")  # duration 5h -> required 2h
    assert availability_shortfall(monday_only, SUNDAY, afternoon) == 2.0


def test_location_same_area_and_unconstrained_are_zero(make_listing: Callable[..., Listing]) -> None:
    """Same area or no stated location: no location violation."""
    listing = make_listing(area="Bandra")
    assert check_listing(listing, ParsedQuery(location="Bandra")).location_km == 0.0
    assert check_listing(listing, ParsedQuery()).location_km == 0.0


def test_location_other_area_costs_real_distance(make_listing: Callable[..., Listing]) -> None:
    """A Bandra listing requested in Andheri is violated by the few km between them."""
    listing = make_listing(area="Bandra")
    other = check_listing(listing, ParsedQuery(location="Andheri"))
    assert 5.0 < other.location_km < 9.0
    assert not passes(other)


def test_space_type_filtered_only_when_stated(make_listing: Callable[..., Listing]) -> None:
    """No stated space type means no check; a stated one filters exactly."""
    listing = make_listing(space_type="meeting_room")
    assert not check_listing(listing, ParsedQuery()).space_type_mismatch
    assert check_listing(
        listing, ParsedQuery(space_type=SpaceType.HOT_DESK)
    ).space_type_mismatch
    assert not check_listing(
        listing, ParsedQuery(space_type=SpaceType.MEETING_ROOM)
    ).space_type_mismatch


def test_count_and_passes_agree_with_violation_sizes(make_listing: Callable[..., Listing]) -> None:
    """count() numbers the violated constraints; passes() is exactly count == 0."""
    listing = make_listing(capacity=4, price_per_hour=2400)
    bad = ParsedQuery(
        location="Andheri",
        party_size=6,
        budget=Budget(amount=100, basis=BudgetBasis.TOTAL_PER_HOUR),
        space_type=SpaceType.HOT_DESK,
    )
    violations = check_listing(listing, bad)
    assert count(violations) == 4  # location, capacity, budget, space type (no date)
    assert not passes(violations)
    assert count(check_listing(listing, ParsedQuery())) == 0
