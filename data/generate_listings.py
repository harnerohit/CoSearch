"""Reproducible generator for data/listings.json (AGENTS.md Step 3, fixed seed)."""

import json
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

# Allow "python data/generate_listings.py" to import the src package from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.schemas import Listing

SEED = 42
OUT_PATH = Path(__file__).resolve().parent / "listings.json"

# Build parameters for the Step 3 distribution requirements; app code never reads these.
PRICE_RANGES = {
    "hot_desk": (80, 300),
    "private_cabin": (400, 2000),
    "meeting_room": (500, 3500),
}
# Per-person hourly rate bands: price = rate x capacity, area-skewed, clipped to PRICE_RANGES
# so every Section 7 range keeps holding while price scales with capacity.
RATE_RANGES = {
    "hot_desk": (80, 300),
    "private_cabin": (150, 320),
    "meeting_room": (110, 190),
}
HIGH_SKEW_FACTOR = 1.3  # BKC and Lower Parel skew higher.
LOW_SKEW_FACTOR = 0.75  # Vashi and Malad skew lower.
CAPACITY_RANGES = {"hot_desk": (1, 1), "private_cabin": (2, 8), "meeting_room": (4, 20)}
HIGH_SKEW_AREAS = frozenset({"BKC", "Lower Parel"})
LOW_SKEW_AREAS = frozenset({"Vashi", "Malad"})
# Generated listings per area; the 4 borderline Bandra cases are added on top (Bandra: 2+4=6).
GENERATED_BY_AREA = {
    "Bandra": 2,
    "Andheri": 6,
    "BKC": 6,
    "Powai": 5,
    "Lower Parel": 5,
    "Goregaon": 4,
    "Malad": 4,
    "Vashi": 4,
}
TYPE_POOL = ["hot_desk"] * 12 + ["private_cabin"] * 12 + ["meeting_room"] * 12
NOISE_POOL = ["quiet"] * 11 + ["moderate"] * 12 + ["lively"] * 13
WHITEBOARD_POOL = [True] * 13 + [False] * 23  # + 3 borderline = 16/40 whiteboards.
AIRCON_POOL = [True] * 32 + [False] * 4  # + 2 borderline = 34/40 listings (85%).
AVAILABILITY_POOL = (
    [("standard", None)] * 22
    + [("weekday_gap", day) for day in (0, 1, 2, 3, 4, 2)]
    + [("evening_only", None)] * 4
    + [("wide", None)] * 4
)
STREETS = (
    "Neem Lane", "Chiku Street", "Amaltas Marg", "Gulmohar Row", "Maple Terrace",
    "Willow Crescent", "Cobalt Walk", "Juniper Rise", "Pebble Court", "Kite Lane",
    "Clover Way", "Indigo Path",
)
NAME_PREFIXES = (
    "Willow", "Fern", "Ember", "Lantern", "Mosaic", "Cobalt", "Juniper", "Pebble",
    "Kite", "Anchor", "Clover", "Summit", "Banyan", "Neem", "Coral", "Quartz",
    "Onyx", "Marigold", "Saffron", "Indigo", "Pine", "Drift", "Halo", "Nook",
    "Loop", "Quill", "Terrace", "Beacon", "Cove", "Harbor", "Mint", "Opal",
    "Pixel", "Reed", "Sprout", "Terra",
)
NAME_SUFFIXES = ("Works", "Desk Co", "Studios", "Hub", "Corner", "Collective", "Loft", "Yard", "Room", "Den")

# The four deliberate Bandra borderline cases: each misses exactly one query criterion.
BORDERLINE_SPECS = (
    {"name": "Marigold Loft", "space_type": "meeting_room", "price": 2500, "noise": "quiet",
     "wifi": 150, "amenities": ["whiteboard", "projector", "video_conferencing", "coffee_machine", "air_conditioning"],
     "rating": 4.3, "reviews": 45, "availability": "standard", "expected_miss": "budget"},
    {"name": "Neem Corner", "space_type": "private_cabin", "price": 2000, "noise": "moderate",
     "wifi": 140, "amenities": ["whiteboard", "printer", "coffee_machine"],
     "rating": 4.1, "reviews": 120, "availability": "standard", "expected_miss": "noise"},
    {"name": "Saffron Yard", "space_type": "private_cabin", "price": 1900, "noise": "quiet",
     "wifi": 220, "amenities": ["projector", "printer", "monitor", "coffee_machine"],
     "rating": 4.6, "reviews": 88, "availability": "standard", "expected_miss": "whiteboard"},
    {"name": "Lantern Room", "space_type": "meeting_room", "price": 2200, "noise": "quiet",
     "wifi": 150, "amenities": ["whiteboard", "projector", "air_conditioning", "coffee_machine"],
     "rating": 4.4, "reviews": 210, "availability": "evening_only", "expected_miss": "afternoon"},
)
BORDERLINE_OFFSETS = ((0.004, -0.003), (-0.005, 0.002), (0.002, 0.006), (-0.003, -0.004))
ZERO_REVIEW_SLOT = 7  # Index within the 36 generated listings.
LOW_REVIEW_SLOTS = frozenset({13, 21, 30})


def _availability_windows(name: str, gap_day: int | None) -> list[dict]:
    """Build the weekly recurring windows for one availability pattern."""
    if name == "standard":
        days, start, end = range(0, 6), "09:00", "18:00"
    elif name == "evening_only":
        days, start, end = range(0, 5), "17:00", "21:00"
    elif name == "wide":
        days, start, end = range(0, 7), "09:00", "21:00"
    else:  # weekday_gap: standard hours, but closed on one weekday.
        days = [day for day in range(0, 6) if day != gap_day]
        start, end = "09:00", "18:00"
    return [{"weekday": day, "start": start, "end": end} for day in days]


def _price(rng: random.Random, area: str, space_type: str, capacity: int) -> int:
    """Price = per-person rate x capacity, area-skewed, clipped to the Section 7 type range."""
    low, high = PRICE_RANGES[space_type]
    rate_low, rate_high = RATE_RANGES[space_type]
    rate = rng.randint(rate_low, rate_high)
    if area in HIGH_SKEW_AREAS:
        rate = round(rate * HIGH_SKEW_FACTOR)
    elif area in LOW_SKEW_AREAS:
        rate = round(rate * LOW_SKEW_FACTOR)
    return min(high, max(low, rate * capacity))


def _unique_name(rng: random.Random, used: set[str]) -> str:
    """Fictional, unique listing name from the prefix/suffix pools."""
    while True:
        name = f"{rng.choice(NAME_PREFIXES)} {rng.choice(NAME_SUFFIXES)}"
        if name not in used:
            used.add(name)
            return name


def _build_borderline() -> list[dict]:
    """The four Bandra borderline records, fully explicit (no RNG, stable across runs)."""
    centre_lat, centre_lng = config.AREAS["Bandra"]
    records = []
    for spec, (lat_off, lng_off) in zip(BORDERLINE_SPECS, BORDERLINE_OFFSETS, strict=True):
        records.append(
            {
                "name": spec["name"],
                "space_type": spec["space_type"],
                "area": "Bandra",
                "address": f"{5 + len(records) * 7} Palm Row, Bandra",
                "lat": round(centre_lat + lat_off, 4),
                "lng": round(centre_lng + lng_off, 4),
                "capacity": 4,
                "price_per_hour": spec["price"],
                "noise_level": spec["noise"],
                "wifi_mbps": spec["wifi"],
                "amenities": spec["amenities"],
                "rating": spec["rating"],
                "review_count": spec["reviews"],
                "availability": _availability_windows(spec["availability"], None),
            }
        )
    return records


def _build_generated(rng: random.Random, used_names: set[str]) -> list[dict]:
    """The other 36 listings, drawn from shuffled pools so every distribution target is met."""
    pools = {
        "space_type": list(TYPE_POOL),
        "noise": list(NOISE_POOL),
        # 14 below 100, 11 at 100-199, 11 at 200+ here; +3/+1 from borderline = 14/14/12.
        "wifi": [rng.randint(20, 99) for _ in range(14)]
        + [rng.randint(100, 199) for _ in range(11)]
        + [rng.randint(200, 500) for _ in range(11)],
        "whiteboard": list(WHITEBOARD_POOL),
        "aircon": list(AIRCON_POOL),
        "availability": list(AVAILABILITY_POOL),
    }
    for pool in pools.values():
        rng.shuffle(pool)

    other_amenities = [
        name for name in config.AMENITIES if name not in ("whiteboard", "air_conditioning")
    ]
    records = []
    for area, count in GENERATED_BY_AREA.items():
        for _ in range(count):
            index = len(records)
            space_type = pools["space_type"][index]
            low, high = CAPACITY_RANGES[space_type]
            if index == ZERO_REVIEW_SLOT:
                rating, review_count = None, 0
            elif index in LOW_REVIEW_SLOTS:
                rating, review_count = round(rng.uniform(3.2, 4.9), 1), rng.randint(1, 9)
            else:
                rating, review_count = round(rng.uniform(3.2, 4.9), 1), rng.randint(10, 400)
            forced = []
            if pools["whiteboard"][index]:
                forced.append("whiteboard")
            if pools["aircon"][index]:
                forced.append("air_conditioning")
            amenities = forced + rng.sample(other_amenities, rng.randint(1, 5))
            centre_lat, centre_lng = config.AREAS[area]
            pattern, gap_day = pools["availability"][index]
            capacity = rng.randint(low, high)
            records.append(
                {
                    "name": _unique_name(rng, used_names),
                    "space_type": space_type,
                    "area": area,
                    "address": f"{rng.randint(1, 120)} {rng.choice(STREETS)}, {area}",
                    "lat": round(centre_lat + rng.uniform(-0.009, 0.009), 4),
                    "lng": round(centre_lng + rng.uniform(-0.009, 0.009), 4),
                    "capacity": capacity,
                    "price_per_hour": _price(rng, area, space_type, capacity),
                    "noise_level": pools["noise"][index],
                    "wifi_mbps": pools["wifi"][index],
                    "amenities": amenities,
                    "rating": rating,
                    "review_count": review_count,
                    "availability": _availability_windows(pattern, gap_day),
                }
            )
    return records


def _afternoon_covered(availability: list) -> bool:
    """True if some Friday window covers the whole 12:00-17:00 afternoon."""
    return any(
        window.weekday == 4 and window.start <= "12:00" and window.end >= "17:00"
        for window in availability
    )


def _check(listings: list[Listing]) -> None:
    """Assert every Step 3 distribution requirement; raise on the first miss."""
    assert len(listings) == 40, f"expected 40 listings, got {len(listings)}"
    areas = Counter(item.area for item in listings)
    assert all(areas[area] >= 3 for area in config.AREAS), dict(areas)
    assert all(areas[area] >= 6 for area in ("Bandra", "Andheri", "BKC")), dict(areas)
    types = Counter(item.space_type.value for item in listings)
    assert types == {"hot_desk": 12, "private_cabin": 14, "meeting_room": 14}, dict(types)
    noise = Counter(item.noise_level.value for item in listings)
    assert noise["quiet"] >= 10 and noise["moderate"] >= 10 and noise["lively"] >= 8, dict(noise)
    assert sum(item.wifi_mbps < 100 for item in listings) >= 8
    assert sum(item.wifi_mbps >= 200 for item in listings) >= 8
    assert sum("whiteboard" in [a.value for a in item.amenities] for item in listings) == 16
    assert sum(item.review_count < 10 for item in listings) >= 3
    assert sum(item.review_count == 0 for item in listings) >= 1
    weekdays = set(range(0, 5))
    gaps = [item.name for item in listings if weekdays - {w.weekday for w in item.availability}]
    assert len(gaps) >= 5, gaps
    aircon = sum("air_conditioning" in [a.value for a in item.amenities] for item in listings)
    assert aircon == 34, aircon
    buckets = (
        sum(item.wifi_mbps < 100 for item in listings),
        sum(100 <= item.wifi_mbps < 200 for item in listings),
        sum(item.wifi_mbps >= 200 for item in listings),
    )
    assert buckets == (14, 14, 12), buckets
    assert min(item.price_per_hour / item.capacity for item in listings) >= 50
    expected = {spec["name"]: spec["expected_miss"] for spec in BORDERLINE_SPECS}
    for item in listings[:4]:
        misses = []
        if item.price_per_hour > 600 * 4:
            misses.append("budget")
        if item.noise_level.value != "quiet":
            misses.append("noise")
        if "whiteboard" not in [a.value for a in item.amenities]:
            misses.append("whiteboard")
        if not _afternoon_covered(item.availability):
            misses.append("afternoon")
        assert misses == [expected[item.name]], f"{item.name}: misses {misses}"


def _summary(listings: list[Listing]) -> None:
    """Print the distribution summary required by Step 3."""
    print(f"Generated {len(listings)} listings (seed {SEED}) -> {OUT_PATH}")
    areas = Counter(item.area for item in listings)
    print("By area:     " + "  ".join(f"{area}={areas[area]}" for area in config.AREAS))
    types = Counter(item.space_type.value for item in listings)
    print("By type:     " + "  ".join(f"{name}={types[name]}" for name in sorted(types)))
    noise = Counter(item.noise_level.value for item in listings)
    print("By noise:    " + "  ".join(f"{name}={noise[name]}" for name in ("quiet", "moderate", "lively")))
    for space_type in ("hot_desk", "private_cabin", "meeting_room"):
        prices = [item.price_per_hour for item in listings if item.space_type.value == space_type]
        print(
            f"Price {space_type:<13} min={min(prices)}  median={statistics.median(prices):g}  max={max(prices)}"
        )
    print("Price per person at full capacity (price_per_hour / capacity, INR/hour):")
    for space_type in ("hot_desk", "private_cabin", "meeting_room"):
        per_person = [
            item.price_per_hour / item.capacity
            for item in listings
            if item.space_type.value == space_type
        ]
        print(
            f"  {space_type:<14} min={min(per_person):.1f}  "
            f"median={statistics.median(per_person):.1f}  max={max(per_person):.1f}"
        )
    cheap = [item for item in listings if item.price_per_hour / item.capacity < 50]
    if cheap:
        for item in cheap:
            per_person = item.price_per_hour / item.capacity
            print(
                f"  UNDER 50: {item.id} {item.name} ({item.space_type.value}, "
                f"capacity {item.capacity}) {item.price_per_hour}/hr = {per_person:.1f}/person"
            )
    else:
        print("  Listings under 50 INR per person at full capacity: none")
    slow = sum(item.wifi_mbps < 100 for item in listings)
    mid = sum(100 <= item.wifi_mbps < 200 for item in listings)
    fast = sum(item.wifi_mbps >= 200 for item in listings)
    print(f"Wifi buckets: <100={slow}  100-199={mid}  >=200={fast}")
    aircon = sum("air_conditioning" in [a.value for a in item.amenities] for item in listings)
    print(f"air_conditioning coverage: {aircon}/40 listings (target 34 = 85%)")
    amenities = Counter(a.value for item in listings for a in item.amenities)
    frequencies = "  ".join(f"{name}={count}" for name, count in sorted(amenities.items(), key=lambda x: (-x[1], x[0])))
    print(f"Amenity frequencies: {frequencies}")
    print("All distribution requirements satisfied; every record validated through Listing.")


def main() -> None:
    """Build, validate, and write data/listings.json, then print the summary."""
    rng = random.Random(SEED)
    used_names = {spec["name"] for spec in BORDERLINE_SPECS}
    records = _build_borderline() + _build_generated(rng, used_names)
    for index, record in enumerate(records, start=1):
        record["id"] = f"L{index:03d}"
    listings = [Listing.model_validate(record) for record in records]
    _check(listings)
    OUT_PATH.write_text(
        json.dumps([item.model_dump(mode="json") for item in listings], indent=2) + "\n",
        encoding="utf-8",
    )
    _summary(listings)


if __name__ == "__main__":
    main()
