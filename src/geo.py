"""Geography: haversine distance, area centres, alias-aware area resolution (Section 4)."""

import math

from src import config


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres between two lat/lng points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lng / 2) ** 2
    )
    return 2 * config.EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def area_center(area: str) -> tuple[float, float]:
    """Centre coordinates of a covered area (config.AREAS is the single source)."""
    return config.AREAS[area]


def resolve_area(text: str | None) -> str | None:
    """Canonical covered area for user text (case, alias, punctuation aware), else None."""
    if text is None:
        return None
    normalized = " ".join(text.casefold().replace(",", " ").split()).strip(" .")
    if normalized.endswith(" mumbai"):
        normalized = normalized[: -len(" mumbai")].strip()
    for area in config.AREAS:
        if normalized == area.casefold():
            return area
    aliases = {key.casefold(): value for key, value in config.AREA_ALIASES.items()}
    return aliases.get(normalized)
