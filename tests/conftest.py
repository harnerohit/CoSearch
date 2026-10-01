"""Shared fixtures (Section 5): the Listing factory used by several test modules."""

from collections.abc import Callable

import pytest

from src.schemas import Listing


@pytest.fixture
def make_listing() -> Callable[..., Listing]:
    """Build a Listing with realistic defaults; tests override one field at a time."""

    def build(**overrides: object) -> Listing:
        record: dict[str, object] = {
            "id": "L001",
            "name": "Test Loft",
            "space_type": "meeting_room",
            "area": "Bandra",
            "address": "1 Test Lane, Bandra",
            "lat": 19.0596,
            "lng": 72.8295,
            "capacity": 4,
            "price_per_hour": 2400,
            "noise_level": "quiet",
            "wifi_mbps": 150,
            "amenities": ["whiteboard"],
            "rating": 4.2,
            "review_count": 50,
            "availability": [
                {"weekday": day, "start": "09:00", "end": "18:00"} for day in range(7)
            ],
        }
        record.update(overrides)
        return Listing.model_validate(record)

    return build
