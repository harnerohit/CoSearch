"""Step 4: alias-aware area resolution and haversine sanity."""

import pytest

from src import config
from src.geo import area_center, haversine_km, resolve_area


def test_area_center_returns_config_coordinates() -> None:
    """area_center reads the single coordinates source in config."""
    assert area_center("Bandra") == config.AREAS["Bandra"]


def test_resolve_area_is_case_insensitive() -> None:
    """Any casing of a covered area resolves to the canonical name."""
    assert resolve_area("bandra") == "Bandra"
    assert resolve_area("LOWER PAREL") == "Lower Parel"
    assert resolve_area("  Bkc  ") == "BKC"


def test_resolve_area_uses_aliases() -> None:
    """Configured aliases resolve to their canonical area."""
    assert resolve_area("bkc") == "BKC"
    assert resolve_area("bandra kurla complex") == "BKC"
    assert resolve_area("Bandra West") == "Bandra"
    assert resolve_area("andheri west") == "Andheri"
    assert resolve_area("andheri east") == "Andheri"


def test_resolve_area_strips_city_and_punctuation() -> None:
    """'Bandra, Mumbai' and 'Bandra.' both resolve; the city alone does not."""
    assert resolve_area("Bandra, Mumbai") == "Bandra"
    assert resolve_area("Bandra.") == "Bandra"
    assert resolve_area("Mumbai") is None


def test_resolve_area_unknown_returns_none() -> None:
    """Out-of-coverage places resolve to None instead of being guessed."""
    assert resolve_area("Pune") is None
    assert resolve_area("Delhi") is None
    assert resolve_area("") is None
    assert resolve_area(None) is None


def test_haversine_zero_for_identical_points() -> None:
    """A point to itself is exactly zero."""
    assert haversine_km(19.0596, 72.8295, 19.0596, 72.8295) == 0.0


def test_haversine_bandra_to_andheri_is_a_few_km() -> None:
    """Real-area sanity: Bandra and Andheri are a few kilometres apart."""
    distance = haversine_km(*config.AREAS["Bandra"], *config.AREAS["Andheri"])
    assert 5.0 < distance < 9.0


def test_haversine_is_symmetric() -> None:
    """Swapping the endpoints does not change the distance."""
    powai, vashi = config.AREAS["Powai"], config.AREAS["Vashi"]
    forward = haversine_km(*powai, *vashi)
    backward = haversine_km(*vashi, *powai)
    assert forward == pytest.approx(backward)
