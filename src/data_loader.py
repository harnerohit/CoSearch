"""Load and validate data/listings.json (the only module that reads the data file)."""

import json
from pathlib import Path

from src.schemas import Listing

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "listings.json"


def load_listings() -> list[Listing]:
    """Read listings.json and validate every record through the Listing model."""
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [Listing.model_validate(record) for record in records]
