"""Structured per-result facts: matched, missed, tradeoffs (plain tokens, never prose)."""

import re
from src import config
from src.filters import budget_price, party_size_for
from src.schemas import Listing, NoiseLevel, ParsedQuery, Violations

def extract_numbers(text: str) -> list[float]:
    """Extract all numbers from text after removing commas."""
    text_no_commas = text.replace(",", "")
    return [float(match) for match in re.findall(r"\d+(?:\.\d+)?", text_no_commas)]

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
            if price >= limit * (1 - config.NEAR_BUDGET_MARGIN_PCT / 100):
                tradeoffs.append(f"price_near_budget={price:g}/{limit}")
        else:
            token = f"budget_over={violations.budget_over_pct:.1f}%"
            missed.append(token)
            tradeoffs.append(token)
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

def build_display_data(listing: Listing, parsed: ParsedQuery, facts: FactDict, rank: int, is_alternative: bool) -> dict:
    """Format facts into readable strings and extract allowed numbers for the validator."""
    allowed_numbers = set()
    allowed_numbers.add(float(listing.capacity))
    allowed_numbers.add(float(listing.price_per_hour))
    allowed_numbers.add(float(listing.wifi_mbps))
    allowed_numbers.add(float(listing.review_count))
    if listing.rating is not None:
        allowed_numbers.add(float(listing.rating))
    
    party_size = parsed.party_size if parsed.party_size is not None else config.DEFAULT_PARTY_SIZE
    pp_price = round(listing.price_per_hour / party_size)
    allowed_numbers.add(float(pp_price))
    
    if parsed.budget is not None:
        allowed_numbers.add(float(parsed.budget.amount))

    for token_list in facts.values():
        for token in token_list:
            for num in extract_numbers(token):
                allowed_numbers.add(num)

    def to_readable(token: str) -> str:
        if token.startswith("area="): return "area"
        if token.startswith("location_km="):
            val = float(token.split('=')[1])
            allowed_numbers.add(round(val, 1))
            return f"{val:.1f} km away"
        if token.startswith("capacity="): 
            # e.g. "capacity=8>=2"
            cap, req = map(int, token.split('=', 1)[1].split('>='))
            if cap >= req * 2 and cap > req + 2:
                allowed_numbers.add(float(cap))
                return f"capacity (holds {cap}, larger than needed)"
            return "capacity"
        if token.startswith("capacity_short="): return f"too small by {token.split('=')[1]} people"
        if token.startswith("budget="): return "within budget"
        if token.startswith("budget_over="):
            val = float(token.split('=')[1].replace('%', ''))
            allowed_numbers.add(round(val))
            return f"{val:.0f}% over budget"
        if token.startswith("price_near_budget="): return "near budget limit"
        if token.startswith("availability="): return "availability"
        if token.startswith("availability_short="): return f"short by {token.split('=')[1]}"
        if token.startswith("space_type="): return "space type"
        if token.startswith("space_type_mismatch="): return f"is a {listing.space_type.value}"
        if token.startswith("noise="): return f"{listing.noise_level.value}"
        if token.startswith("wifi="): return f"{listing.wifi_mbps} Mbps wifi"
        if token.startswith("amenity="): 
            am = token.split('=')[1].replace("_", " ")
            return am if token in facts["matched"] else f"has no {am}"
        if token.startswith("low_reviews="): return f"has only {token.split('=')[1]} reviews"
        return token

    readable_matched = [to_readable(t) for t in facts.get("matched", [])]
    readable_missed = [to_readable(t) for t in facts.get("missed", [])]
    # deduplicate trade-offs from missed
    readable_tradeoffs = [to_readable(t) for t in facts.get("tradeoffs", []) if t not in facts.get("missed", [])]
    
    def join_with_and(items: list[str]) -> str:
        if not items: return ""
        if len(items) == 1: return items[0]
        return ", ".join(items[:-1]) + " and " + items[-1]
        
    combined_missed_tradeoffs = readable_missed + readable_tradeoffs

    if is_alternative:
        if combined_missed_tradeoffs:
            template_string = f"Closest option, but it is {join_with_and(combined_missed_tradeoffs)}."
        else:
            template_string = "Closest option."
    else:
        parts = []
        if readable_matched:
            parts.append(f"Fits your {join_with_and(readable_matched)}")
        
        if combined_missed_tradeoffs:
            prefix = "trade-offs: it" if len(combined_missed_tradeoffs) > 1 else "trade-off: it"
            if not parts:
                parts.append(f"{prefix.capitalize()} {join_with_and(combined_missed_tradeoffs)}")
            else:
                parts.append(f"{prefix} {join_with_and(combined_missed_tradeoffs)}")
                
        template_string = "; ".join(parts) + "." if parts else "Matches request."

    missed_amenities = set()
    for t in facts.get("missed", []):
        if t.startswith("amenity="):
            missed_amenities.add(t.split('=')[1])

    return {
        "allowed_numbers": allowed_numbers,
        "missed_amenities": missed_amenities,
        "readable_facts": {
            "matched": readable_matched,
            "missed": readable_missed,
            "tradeoffs": readable_tradeoffs
        },
        "per_person_price": pp_price,
        "template_string": template_string
    }
