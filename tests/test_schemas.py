"""Step 2: valid and invalid Listing and ParsedQuery objects."""

import pytest
from pydantic import ValidationError

from src.schemas import Listing, ParsedQuery

VALID_LISTING = {
    "id": "L001",
    "name": "Test Hub",
    "space_type": "hot_desk",
    "area": "Bandra",
    "address": "12 Test Road",
    "lat": 19.0600,
    "lng": 72.8300,
    "capacity": 4,
    "price_per_hour": 500,
    "noise_level": "quiet",
    "wifi_mbps": 120,
    "amenities": ["whiteboard"],
    "rating": 4.5,
    "review_count": 12,
    "availability": [{"weekday": 0, "start": "09:00", "end": "18:00"}],
}

VALID_PARSED_QUERY = {
    "location": "Bandra",
    "party_size": 4,
    "budget": {"amount": 600, "basis": "per_person_per_hour"},
    "date": "2026-10-02",
    "time_window": {"start": "12:00", "end": "17:00"},
    "soft": {"quiet": True, "min_wifi": "fast", "amenities": ["whiteboard"]},
}


def test_valid_listing_constructs() -> None:
    """A well-formed listing keeps every field, coercing strings to enums."""
    listing = Listing(**VALID_LISTING)
    assert listing.area == "Bandra"
    assert listing.amenities[0].value == "whiteboard"
    assert listing.availability[0].weekday == 0


def test_listing_rejects_bad_amenity() -> None:
    """An amenity outside config.AMENITIES is rejected."""
    with pytest.raises(ValidationError):
        Listing(**{**VALID_LISTING, "amenities": ["pool"]})


def test_listing_rejects_bad_time_format() -> None:
    """Availability times must be 24-hour HH:MM."""
    with pytest.raises(ValidationError):
        Listing(
            **{
                **VALID_LISTING,
                "availability": [{"weekday": 0, "start": "9am", "end": "18:00"}],
            }
        )


def test_listing_missing_required_field() -> None:
    """A listing without a required field (rating) is rejected."""
    incomplete = {key: value for key, value in VALID_LISTING.items() if key != "rating"}
    with pytest.raises(ValidationError):
        Listing(**incomplete)


def test_valid_parsed_query_constructs() -> None:
    """A well-formed parsed query keeps hard and soft parts intact."""
    parsed = ParsedQuery(**VALID_PARSED_QUERY)
    assert parsed.party_size == 4
    assert parsed.budget.amount == 600
    assert parsed.soft.quiet is True


def test_parsed_query_rejects_bad_amenity() -> None:
    """A soft amenity outside config.AMENITIES is rejected."""
    with pytest.raises(ValidationError):
        ParsedQuery(**{**VALID_PARSED_QUERY, "soft": {"amenities": ["pool"]}})


def test_parsed_query_rejects_bad_time_format() -> None:
    """A time window must be 24-hour HH:MM with end after start."""
    with pytest.raises(ValidationError):
        ParsedQuery(time_window={"start": "9am", "end": "17:00"})
    with pytest.raises(ValidationError):
        ParsedQuery(time_window={"start": "17:00", "end": "12:00"})


def test_parsed_query_nested_missing_field() -> None:
    """A budget without its basis is rejected."""
    with pytest.raises(ValidationError):
        ParsedQuery(budget={"amount": 600})
