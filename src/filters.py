"""Hard-constraint filtering with per-constraint violation sizes (AGENTS.md Section 4).

Budget conversion and availability overlap exist only in this module.
"""

import datetime

from src import config
from src.geo import area_center, haversine_km
from src.schemas import (
    BudgetBasis,
    Listing,
    ParsedQuery,
    TimeWindow,
    Violations,
    hhmm_to_minutes,
)


def budget_price(listing: Listing, party_size: int, basis: BudgetBasis) -> float:
    """Convert a listing's hourly price to the user's budget basis (the only conversion)."""
    if basis is BudgetBasis.TOTAL_PER_HOUR:
        return float(listing.price_per_hour)
    return listing.price_per_hour / party_size


def availability_shortfall(
    listing: Listing,
    date: datetime.date | None,
    window: TimeWindow | None,
) -> float:
    """Hours short of the requested slot; 0 when satisfied or when no date was given."""
    if date is None:
        return 0.0
    windows = [w for w in listing.availability if w.weekday == date.weekday()]
    if window is None:
        return 0.0 if windows else float(config.MIN_BOOKING_HOURS)
    duration = (hhmm_to_minutes(window.end) - hhmm_to_minutes(window.start)) / 60
    required = min(float(config.MIN_BOOKING_HOURS), duration)
    overlaps = []
    for w in windows:
        start = max(hhmm_to_minutes(w.start), hhmm_to_minutes(window.start))
        end = min(hhmm_to_minutes(w.end), hhmm_to_minutes(window.end))
        overlaps.append(max(0.0, (end - start) / 60))
    return max(0.0, required - max(overlaps, default=0.0))


def check_listing(listing: Listing, parsed: ParsedQuery) -> Violations:
    """Violation size per hard constraint for one listing; zero/False means satisfied."""
    location_km = 0.0
    if parsed.location is not None and listing.area != parsed.location:
        centre_lat, centre_lng = area_center(parsed.location)
        location_km = haversine_km(listing.lat, listing.lng, centre_lat, centre_lng)

    capacity_short = 0
    if parsed.party_size is not None:
        capacity_short = max(0, parsed.party_size - listing.capacity)

    budget_over_pct = 0.0
    if parsed.budget is not None:
        party = (
            parsed.party_size
            if parsed.party_size is not None
            else config.DEFAULT_PARTY_SIZE
        )
        price = budget_price(listing, party, parsed.budget.basis)
        if price > parsed.budget.amount:
            budget_over_pct = (price - parsed.budget.amount) / parsed.budget.amount * 100

    hours_short = availability_shortfall(listing, parsed.date, parsed.time_window)

    space_type_mismatch = (
        parsed.space_type is not None and listing.space_type != parsed.space_type
    )
    return Violations(
        location_km=location_km,
        capacity_short=capacity_short,
        budget_over_pct=budget_over_pct,
        hours_short=hours_short,
        space_type_mismatch=space_type_mismatch,
    )


def count(violations: Violations) -> int:
    """Number of hard constraints violated (size > 0 or mismatch set)."""
    return sum(
        (
            violations.location_km > 0,
            violations.capacity_short > 0,
            violations.budget_over_pct > 0,
            violations.hours_short > 0,
            violations.space_type_mismatch,
        )
    )


def passes(violations: Violations) -> bool:
    """True when the listing satisfies every hard constraint."""
    return count(violations) == 0
