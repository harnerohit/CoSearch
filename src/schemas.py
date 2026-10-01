"""All Pydantic v2 data models (AGENTS.md Section 6)."""

import datetime
import re
from enum import Enum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src import config


class SpaceType(str, Enum):
    """Kind of bookable space (Section 6)."""

    HOT_DESK = "hot_desk"
    PRIVATE_CABIN = "private_cabin"
    MEETING_ROOM = "meeting_room"


class NoiseLevel(str, Enum):
    """Listing noise level (Section 6)."""

    QUIET = "quiet"
    MODERATE = "moderate"
    LIVELY = "lively"


class BudgetBasis(str, Enum):
    """How a stated budget should be interpreted (Section 6)."""

    PER_PERSON_PER_HOUR = "per_person_per_hour"
    TOTAL_PER_HOUR = "total_per_hour"


class Outcome(str, Enum):
    """Possible pipeline outcomes (Section 4)."""

    CLARIFY = "CLARIFY"
    RESULTS = "RESULTS"
    ALTERNATIVES = "ALTERNATIVES"
    NO_MATCH = "NO_MATCH"


# Amenity enum generated from the single vocabulary in config (Section 6):
# the only amenity strings that exist anywhere in the project.
Amenity = Enum(
    "Amenity",
    {name.upper(): name for name in config.AMENITIES},
    type=str,
)

_HHMM_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _validate_hhmm(value: str) -> str:
    """Return the time unchanged if it is a valid 24-hour HH:MM string."""
    if not _HHMM_PATTERN.match(value):
        raise ValueError(f"expected HH:MM on a 24-hour clock, got {value!r}")
    return value


def _ensure_end_after_start(start: str, end: str) -> None:
    """Raise if end is not later than start (both HH:MM strings)."""
    start_minutes = int(start[:2]) * 60 + int(start[3:])
    end_minutes = int(end[:2]) * 60 + int(end[3:])
    if end_minutes <= start_minutes:
        raise ValueError(f"end {end!r} must be after start {start!r}")


class TimeWindow(BaseModel):
    """A time window on a single day, 24-hour HH:MM."""

    model_config = ConfigDict(extra="forbid")

    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def _check_hhmm(cls, value: str) -> str:
        """Validate the HH:MM format."""
        return _validate_hhmm(value)

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        """Require end after start."""
        _ensure_end_after_start(self.start, self.end)
        return self


class AvailabilityWindow(BaseModel):
    """Weekly recurring opening window (Section 6): weekday 0=Monday..6=Sunday."""

    model_config = ConfigDict(extra="forbid")

    weekday: int = Field(ge=0, le=6)
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def _check_hhmm(cls, value: str) -> str:
        """Validate the HH:MM format."""
        return _validate_hhmm(value)

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        """Require end after start."""
        _ensure_end_after_start(self.start, self.end)
        return self


class Budget(BaseModel):
    """A hard budget with the basis the user stated (Section 6)."""

    model_config = ConfigDict(extra="forbid")

    amount: int = Field(gt=0)
    basis: BudgetBasis


class SoftPreferences(BaseModel):
    """Soft preferences: affect ranking only, never filtering (Section 6)."""

    model_config = ConfigDict(extra="forbid")

    quiet: bool = False
    min_wifi: Literal["fast"] | None = None
    amenities: list[Amenity] = Field(default_factory=list)


class Listing(BaseModel):
    """One coworking space unit; every user-facing fact comes from this data."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^L\d{3}$")
    name: str = Field(min_length=1)
    space_type: SpaceType
    area: str
    address: str = Field(min_length=1)
    lat: float
    lng: float
    capacity: int = Field(gt=0)
    price_per_hour: int = Field(gt=0)
    noise_level: NoiseLevel
    wifi_mbps: int = Field(gt=0)
    amenities: list[Amenity]
    rating: float | None = Field(ge=1, le=5)
    review_count: int = Field(ge=0)
    availability: list[AvailabilityWindow]

    @field_validator("area")
    @classmethod
    def _check_area(cls, value: str) -> str:
        """Require an area we cover."""
        if value not in config.AREAS:
            raise ValueError(f"unknown area {value!r}; covered: {', '.join(config.AREAS)}")
        return value

    @model_validator(mode="after")
    def _check_coordinates(self) -> Self:
        """Require lat/lng within MAX_COORD_OFFSET_DEG of the area centre."""
        centre_lat, centre_lng = config.AREAS[self.area]
        if (
            abs(self.lat - centre_lat) > config.MAX_COORD_OFFSET_DEG
            or abs(self.lng - centre_lng) > config.MAX_COORD_OFFSET_DEG
        ):
            raise ValueError(
                f"lat/lng must be within {config.MAX_COORD_OFFSET_DEG} degrees of the "
                f"{self.area} centre"
            )
        return self


class ParsedQuery(BaseModel):
    """LLM-parsed query: hard constraints, soft preferences, ambiguity flags (Section 6)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    location: str | None = None
    unrecognized_location: str | None = None
    party_size: int | None = Field(default=None, gt=0)
    budget: Budget | None = None
    date: datetime.date | None = None
    time_window: TimeWindow | None = None
    space_type: SpaceType | None = None
    soft: SoftPreferences = Field(default_factory=SoftPreferences)
    unmatched_preferences: list[str] = Field(default_factory=list)
    unsupported_budget_basis: bool = False

    @field_validator("location", "unrecognized_location")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        """Treat empty strings as 'not stated'."""
        return None if value == "" else value

    @model_validator(mode="after")
    def _exclusive_location(self) -> Self:
        """A location is either recognized or unrecognized, never both."""
        if self.location is not None and self.unrecognized_location is not None:
            raise ValueError("location and unrecognized_location are mutually exclusive")
        return self


class ResultItem(BaseModel):
    """One ranked result as the UI receives it (Section 6)."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    listing: Listing
    score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    facts: dict[str, Any] = Field(default_factory=dict)
    explanation: str | None = None
    explanation_source: Literal["llm", "template"] | None = None


class SearchResponse(BaseModel):
    """The pipeline's only output consumed by the UI (Section 6)."""

    model_config = ConfigDict(extra="forbid")

    outcome: Outcome
    parsed_query: ParsedQuery | None = None
    results: list[ResultItem] = Field(default_factory=list)
    message: str | None = None
    notes: list[str] = Field(default_factory=list)
