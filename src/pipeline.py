"""Pipeline: parse -> clarify -> filter -> rank -> outcome; every message is a config template (Section 4)."""

from src import config
from src.data_loader import load_listings
from src.facts import compute_facts
from src.filters import check_listing, count, passes
from src.llm import LLMError
from src.parser import ParseError, parse
from src.ranker import mean_rating, rank
from src.schemas import (
    BudgetBasis,
    Outcome,
    ParsedQuery,
    ResultItem,
    SearchResponse,
    Violations,
)

# The dataset is loaded and validated once (Section 2); no other module re-reads the file.
_LISTINGS = load_listings()

# Single rendering of the covered-area list for every coverage-style message.
_COVERED_AREAS = ", ".join(config.AREAS)


def _response(
    outcome: Outcome,
    message: str | None = None,
    parsed: ParsedQuery | None = None,
    notes: list[str] | None = None,
    results: list[ResultItem] | None = None,
) -> SearchResponse:
    """Assemble the only object the UI consumes (Section 6)."""
    return SearchResponse(
        outcome=outcome,
        parsed_query=parsed,
        results=results or [],
        message=message,
        notes=notes or [],
    )


def _clarify_message(parsed: ParsedQuery) -> str | None:
    """The CLARIFY template that applies, in fixed precedence; None when the query is specific enough."""
    if parsed.unrecognized_location is not None:
        # Exact whole-string match, never a substring: "Navi Mumbai" gets the coverage message.
        if parsed.unrecognized_location.strip().casefold() in config.CITY_NAMES:
            return config.MSG_CITY_NO_AREA.format(areas=_COVERED_AREAS)
        return config.MSG_COVERAGE.format(
            area=parsed.unrecognized_location, areas=_COVERED_AREAS
        )
    if parsed.unsupported_budget_basis:
        return config.MSG_UNSUPPORTED_BUDGET
    if (
        parsed.location is None
        and parsed.party_size is None
        and parsed.budget is None
        and parsed.date is None
        and parsed.time_window is None
    ):
        return config.MSG_MISSING_INFO.format(areas=_COVERED_AREAS)
    return None


def _normalized(violations: Violations) -> float:
    """Violation sizes summed in comparable units for alternative ordering (Section 4)."""
    return (
        violations.location_km / config.ALT_MAX_DISTANCE_KM
        + violations.budget_over_pct / config.PERCENT_SCALE
        + violations.hours_short
    )


def _alternatives(
    parsed: ParsedQuery, violations: dict[str, Violations]
) -> list[ResultItem]:
    """Closest options when nothing passes: capacity and space_type are never relaxed."""
    eligible = [
        (item, violations[item.id])
        for item in _LISTINGS
        if violations[item.id].capacity_short == 0
        and not violations[item.id].space_type_mismatch  # deliberate: beyond Section 4
        and violations[item.id].location_km <= config.ALT_MAX_DISTANCE_KM
    ]
    eligible.sort(key=lambda entry: (count(entry[1]), _normalized(entry[1])))
    return [
        ResultItem(
            rank=position,
            listing=item,
            score=0.0,  # not an eligible match; its "why" is facts["violations"]
            facts={**compute_facts(item, parsed, v), "violations": v.model_dump()},
        )
        for position, (item, v) in enumerate(eligible[: config.ALT_MAX], start=1)
    ]


def _no_match_message(violations: dict[str, Violations]) -> str:
    """Name the most restrictive constraints with counts and the configured way to loosen them."""
    total = len(_LISTINGS)
    counts = {
        "location": sum(v.location_km > 0 for v in violations.values()),
        "capacity": sum(v.capacity_short > 0 for v in violations.values()),
        "budget": sum(v.budget_over_pct > 0 for v in violations.values()),
        "time": sum(v.hours_short > 0 for v in violations.values()),
        "space_type": sum(v.space_type_mismatch for v in violations.values()),
    }
    ordered = sorted(
        (key for key, value in counts.items() if value > 0),
        key=lambda key: counts[key],
        reverse=True,  # most restrictive first; equal counts keep declaration order
    )
    reasons = "; ".join(
        f"{key.replace('_', ' ')}: {counts[key]}/{total} spaces "
        f"({config.NO_MATCH_LOOSEN[key]})"
        for key in ordered
    )
    return config.MSG_NO_MATCH.format(reasons=reasons)


def search(query: str) -> SearchResponse:
    """Run one search end to end; parse is the only LLM call and every decision is code."""
    if not query.strip():
        return _response(Outcome.CLARIFY, message=config.MSG_EMPTY_QUERY)
    try:
        parsed = parse(query)
    except LLMError:
        return _response(Outcome.CLARIFY, message=config.MSG_LLM_ERROR)
    except ParseError:
        return _response(Outcome.CLARIFY, message=config.MSG_PARSE_ERROR)
    clarify = _clarify_message(parsed)
    if clarify is not None:
        return _response(Outcome.CLARIFY, message=clarify, parsed=parsed)
    notes = (
        [config.NOTE_DEFAULT_PARTY_SIZE]
        if parsed.budget is not None
        and parsed.budget.basis is BudgetBasis.PER_PERSON_PER_HOUR
        and parsed.party_size is None
        else []
    )
    violations = {item.id: check_listing(item, parsed) for item in _LISTINGS}
    passing = [item for item in _LISTINGS if passes(violations[item.id])]
    if passing:
        ranked = rank(passing, parsed, mean_rating(_LISTINGS))
        results = [
            ResultItem(
                rank=position,
                listing=listing,
                score=score,
                score_breakdown=breakdown,
                facts=compute_facts(listing, parsed, violations[listing.id]),
            )
            for position, (listing, score, breakdown) in enumerate(
                ranked[: config.TOP_N], start=1
            )
        ]
        return _response(Outcome.RESULTS, parsed=parsed, notes=notes, results=results)
    alternatives = _alternatives(parsed, violations)
    if alternatives:
        return _response(
            Outcome.ALTERNATIVES, parsed=parsed, notes=notes, results=alternatives
        )
    return _response(
        Outcome.NO_MATCH,
        message=_no_match_message(violations),
        parsed=parsed,
        notes=notes,
    )
