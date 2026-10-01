"""All project constants: areas, vocabularies, thresholds, weights, limits (AGENTS.md Sections 6-7)."""

# --- Coverage: Mumbai areas and approximate centre coordinates (Section 7) ---
AREAS: dict[str, tuple[float, float]] = {
    "Bandra": (19.0596, 72.8295),
    "Andheri": (19.1197, 72.8468),
    "Powai": (19.1176, 72.9060),
    "BKC": (19.0690, 72.8700),
    "Lower Parel": (19.0000, 72.8300),
    "Goregaon": (19.1663, 72.8526),
    "Malad": (19.1874, 72.8484),
    "Vashi": (19.0771, 72.9986),
}

# Case-insensitive aliases -> canonical area name (used by geo.resolve_area).
AREA_ALIASES: dict[str, str] = {
    "bkc": "BKC",
    "bandra kurla complex": "BKC",
    "bandra kurla": "BKC",
    "bandra west": "Bandra",
    "andheri west": "Andheri",
    "malad west": "Malad",
}

# Listing lat/lng must be within this many degrees of the area centre (Section 6).
MAX_COORD_OFFSET_DEG = 0.01

# --- Time windows (Section 7); keys are the labels the parser prompt offers ---
TIME_WINDOWS: dict[str, tuple[str, str]] = {
    "morning": ("09:00", "12:00"),
    "afternoon": ("12:00", "17:00"),
    "evening": ("17:00", "21:00"),
    "full_day": ("09:00", "18:00"),
}

# Availability passes if overlap >= min(MIN_BOOKING_HOURS, requested duration).
MIN_BOOKING_HOURS = 2

# --- Vocabulary (Sections 6-7): the only amenity strings allowed anywhere ---
AMENITIES: tuple[str, ...] = (
    "whiteboard",
    "projector",
    "printer",
    "monitor",
    "standing_desk",
    "coffee_machine",
    "phone_booth",
    "locker",
    "parking",
    "air_conditioning",
)

# "Fast" wifi threshold for soft preferences (Section 7).
FAST_WIFI_MBPS = 100

# Budget rule: party size assumed when the user did not state one (Section 7).
DEFAULT_PARTY_SIZE = 1

# --- Ranking (Section 7) ---
W_FIT = 0.45
W_TRUST = 0.30
W_PRICE = 0.25
NOISE_SCORES: dict[str, float] = {"quiet": 1.0, "moderate": 0.5, "lively": 0.0}
TRUST_C = 20  # Bayesian average prior: pseudo-review count C (Section 7).
RATING_MAX = 5.0  # Trust is the Bayesian average divided by this.

# --- Limits (Section 7) ---
TOP_N = 5
ALT_MAX = 3
ALT_MAX_DISTANCE_KM = 8
MAX_QUERY_CHARS = 300
SESSION_SEARCH_LIMIT = 20

# --- LLM settings (Section 7) ---
LLM_TEMPERATURE = 0.0
LLM_TIMEOUT_SECONDS = 30.0
LLM_MAX_RETRIES = 2  # on timeout or rate limit, with LLM_BACKOFF_SECONDS between tries.
LLM_JSON_RETRIES = 1  # on invalid JSON or an empty answer.
LLM_BACKOFF_SECONDS = 2.0  # "short backoff"; exact value chosen here, review at Gate 2/3.
