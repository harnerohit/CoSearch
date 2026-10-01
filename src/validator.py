import re
import logging
from src.schemas import Listing, ResultItem
from src.facts import extract_numbers
from src import config

logger = logging.getLogger(__name__)

def validate_explanation(
    explanation: str, 
    listing: Listing, 
    allowed_numbers: set[float], 
    missed_amenities: set[str],
    all_results: list[ResultItem]
) -> tuple[bool, str]:
    
    text = re.sub(r"^\s*\d+[.)]\s", "", explanation)
    numbers_found = extract_numbers(text)
    for num_val in numbers_found:
        if not any(abs(num_val - allowed) < 1e-5 for allowed in allowed_numbers):
            reason = f"Number {num_val} not in allowed set."
            logger.debug(reason)
            return False, reason
            
    text_lower = text.lower()
    for canonical, synonyms in config.AMENITY_SYNONYMS.items():
        terms_to_check = [canonical.replace('_', ' ')] + list(synonyms)
        for term in terms_to_check:
            pattern = r"\b" + re.escape(term) + r"\b"
            matches = list(re.finditer(pattern, text_lower))
            if matches:
                has_amenity = any(a.name.lower() == canonical for a in listing.amenities)
                if has_amenity:
                    continue
                
                if canonical not in missed_amenities:
                    reason = f"Mentions unowned and unrequested amenity '{term}'."
                    logger.debug(reason)
                    return False, reason
                    
                for match in matches:
                    start_idx = match.start()
                    sentence_start = max(
                        text_lower.rfind('.', 0, start_idx),
                        text_lower.rfind('!', 0, start_idx),
                        text_lower.rfind('?', 0, start_idx)
                    )
                    preceding_text = text_lower[sentence_start+1:start_idx]
                    
                    preceding_words = [w.strip(".,!?;:()[]\"'") for w in preceding_text.split()]
                    last_3 = preceding_words[-3:]
                    
                    has_negation = False
                    for cue in ["no", "without", "lacks", "missing", "not"]:
                        if cue in last_3:
                            has_negation = True
                            break
                    if not has_negation:
                        text_last_3 = " ".join(last_3)
                        if "doesn't have" in text_last_3 or "doesnt have" in text_last_3:
                            has_negation = True
                            
                    if not has_negation:
                        reason = f"Mentions missed amenity '{term}' without preceding negation."
                        logger.debug(reason)
                        return False, reason

    for other in all_results:
        if other.listing.id == listing.id:
            continue
        other_name = other.listing.name.lower()
        if other_name in text_lower:
            reason = f"Mentions another listing's name: {other.listing.name}"
            logger.debug(reason)
            return False, reason

    listing_facts = next(r.facts for r in all_results if r.listing.id == listing.id)
    all_facts = listing_facts.get("matched", []) + listing_facts.get("missed", []) + listing_facts.get("tradeoffs", [])
    
    has_budget_violation = any(t.startswith("budget_over=") for t in all_facts)
    has_budget_near = any(t.startswith("price_near_budget=") for t in all_facts)
    has_budget_met = any(t.startswith("budget=") for t in all_facts)
    
    for phrase in config.BUDGET_OVER_PHRASES:
        if phrase in text_lower and not has_budget_violation:
            reason = f"Mentions budget violation ('{phrase}') without supporting facts."
            logger.debug(reason)
            return False, reason
            
    for phrase in config.BUDGET_NEAR_PHRASES:
        if phrase in text_lower:
            if not has_budget_near or has_budget_violation:
                reason = f"Mentions near budget ('{phrase}') but facts don't support it or there is a violation."
                logger.debug(reason)
                return False, reason

    for phrase in config.BUDGET_UNDER_PHRASES:
        if phrase in text_lower and not has_budget_met:
            reason = f"Mentions budget met ('{phrase}') without supporting facts."
            logger.debug(reason)
            return False, reason

    for level, words in config.NOISE_SYNONYMS.items():
        if level != listing.noise_level.value:
            for word in words:
                if re.search(r"\b" + re.escape(word) + r"\b", text_lower):
                    reason = f"Mentions noise word '{word}' which conflicts with listing noise level '{listing.noise_level.value}'."
                    logger.debug(reason)
                    return False, reason

    return True, "Passed"
