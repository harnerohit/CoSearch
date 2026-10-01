"""Deterministic ranking over hard-filtered candidates: fit, trust, price (Section 7)."""

from src import config
from src.filters import budget_price, party_size_for
from src.schemas import Listing, ParsedQuery

# A ranked entry: (listing, score, score_breakdown).
Ranked = tuple[Listing, float, dict[str, float]]


def mean_rating(listings: list[Listing]) -> float:
    """Mean of non-null ratings over the dataset (Bayesian prior m; never hardcoded)."""
    ratings = [item.rating for item in listings if item.rating is not None]
    return sum(ratings) / len(ratings) if ratings else 0.0


def trust(listing: Listing, dataset_mean: float) -> float:
    """Bayesian average (C*m + n*r)/(C+n) divided by 5; zero reviews falls back to m."""
    n = listing.review_count
    rating = listing.rating if listing.rating is not None else dataset_mean
    return (
        (config.TRUST_C * dataset_mean + n * rating) / (config.TRUST_C + n)
    ) / config.RATING_MAX


def soft_match(listing: Listing, parsed: ParsedQuery) -> float | None:
    """Average over the user's stated soft preferences; None when none were stated."""
    scores: list[float] = []
    if parsed.soft.quiet:
        scores.append(config.NOISE_SCORES[listing.noise_level.value])
    if parsed.soft.min_wifi == "fast":
        scores.append(min(listing.wifi_mbps / config.FAST_WIFI_MBPS, 1.0))
    for amenity in parsed.soft.amenities:
        scores.append(1.0 if amenity in listing.amenities else 0.0)
    return None if not scores else sum(scores) / len(scores)


def price_fit(listing: Listing, parsed: ParsedQuery) -> float | None:
    """1 - price/budget clipped to [0, 1]; None when no budget was stated."""
    if parsed.budget is None:
        return None
    price = budget_price(listing, party_size_for(parsed), parsed.budget.basis)
    return max(0.0, min(1.0, 1.0 - price / parsed.budget.amount))


def score(
    listing: Listing, parsed: ParsedQuery, dataset_mean: float
) -> tuple[float, dict[str, float]]:
    """Weighted score over active terms only; absent terms drop out and weights renormalize."""
    values: dict[str, float] = {"trust": trust(listing, dataset_mean)}
    weights: dict[str, float] = {"trust": config.W_TRUST}
    match = soft_match(listing, parsed)
    if match is not None:
        values["soft_match"] = match
        weights["soft_match"] = config.W_FIT
    fit = price_fit(listing, parsed)
    if fit is not None:
        values["price_fit"] = fit
        weights["price_fit"] = config.W_PRICE
    total_weight = sum(weights.values())
    breakdown = dict(values)
    breakdown.update(
        {f"weight_{key}": weight / total_weight for key, weight in weights.items()}
    )
    total = sum(weights[key] / total_weight * values[key] for key in weights)
    return total, breakdown


def rank(
    listings: list[Listing], parsed: ParsedQuery, dataset_mean: float
) -> list[Ranked]:
    """Score every candidate; order by score desc, then trust desc, then id asc."""
    scored: list[Ranked] = []
    for item in listings:
        total, breakdown = score(item, parsed, dataset_mean)
        scored.append((item, total, breakdown))
    scored.sort(key=lambda entry: (-entry[1], -entry[2]["trust"], entry[0].id))
    return scored
