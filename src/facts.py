"""Structured per-result facts: matched, missed, tradeoffs (plain tokens, never prose)."""

from src import config
from src.filters import budget_price, party_size_for
from src.schemas import Listing, NoiseLevel, ParsedQuery, Violations

FactDict = dict[str, list[str]]


def hard_facts(
    listing: Listing, parsed: ParsedQuery, violations: Violations
) -> FactDict:
    """Satisfied hard constraints, every miss (with its size), and the near-budget tradeoff."""
    matched: list[str] = []
    missed: list[str] = []
    tradeoffs: list[str] = []

    if parsed.location is not None:
        if violations.location_km == 0:
            matched.append(f"area={listing.area}")
        else:
            token = f"location_km={violations.location_km:.1f}"
            missed.append(token)
            tradeoffs.append(token)
    if parsed.party_size is not None:
        if violations.capacity_short == 0:
            matched.append(f"capacity={listing.capacity}>={parsed.party_size}")
        else:
            token = f"capacity_short={violations.capacity_short}"
            missed.append(token)
            tradeoffs.append(token)
    if parsed.budget is not None:
        limit = parsed.budget.amount
        price = budget_price(listing, party_size_for(parsed), parsed.budget.basis)
        if violations.budget_over_pct == 0:
            matched.append(f"budget={price:g}<={limit}")
        else:
            token = f"budget_over={violations.budget_over_pct:.1f}%"
            missed.append(token)
            tradeoffs.append(token)
        if price >= limit * (1 - config.NEAR_BUDGET_MARGIN_PCT / 100):
            tradeoffs.append(f"price_near_budget={price:g}/{limit}")
    if parsed.date is not None:
        if violations.hours_short == 0:
            when = parsed.date.isoformat()
            if parsed.time_window is not None:
                when += f" {parsed.time_window.start}-{parsed.time_window.end}"
            matched.append(f"availability={when}")
        else:
            token = f"availability_short={violations.hours_short:g}h"
            missed.append(token)
            tradeoffs.append(token)
    if parsed.space_type is not None:
        if violations.space_type_mismatch:
            token = f"space_type_mismatch={listing.space_type.value}"
            missed.append(token)
            tradeoffs.append(token)
        else:
            matched.append(f"space_type={listing.space_type.value}")
    return {"matched": matched, "missed": missed, "tradeoffs": tradeoffs}


def soft_facts(listing: Listing, parsed: ParsedQuery) -> FactDict:
    """Stated soft preferences: each one matched, or missed (and listed as a tradeoff)."""
    matched: list[str] = []
    missed: list[str] = []

    if parsed.soft.quiet:
        token = f"noise={listing.noise_level.value}"
        if listing.noise_level == NoiseLevel.QUIET:
            matched.append(token)
        else:
            missed.append(token)
    if parsed.soft.min_wifi == "fast":
        if listing.wifi_mbps >= config.FAST_WIFI_MBPS:
            matched.append(f"wifi={listing.wifi_mbps}>={config.FAST_WIFI_MBPS}")
        else:
            missed.append(f"wifi={listing.wifi_mbps}<{config.FAST_WIFI_MBPS}")
    for amenity in parsed.soft.amenities:
        token = f"amenity={amenity.value}"
        if amenity in listing.amenities:
            matched.append(token)
        else:
            missed.append(token)
    return {"matched": matched, "missed": missed, "tradeoffs": list(missed)}


def compute_facts(
    listing: Listing, parsed: ParsedQuery, violations: Violations
) -> FactDict:
    """Combine hard and soft facts and add the low-review tradeoff."""
    facts: FactDict = {"matched": [], "missed": [], "tradeoffs": []}
    for part in (hard_facts(listing, parsed, violations), soft_facts(listing, parsed)):
        for key, tokens in part.items():
            facts[key].extend(tokens)
    if listing.review_count < config.LOW_REVIEW_LIMIT:
        facts["tradeoffs"].append(f"low_reviews={listing.review_count}")
    return facts
