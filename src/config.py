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
    "andheri east": "Andheri",
    "malad west": "Malad",
}

# Great-circle radius used by geo.haversine_km.
EARTH_RADIUS_KM = 6371.0

# Listing lat/lng must be within this many degrees of the area centre (Section 6).
MAX_COORD_OFFSET_DEG = 0.01

# --- Time windows (Section 7); keys are the labels the parser prompt offers ---
TIME_WINDOWS: dict[str, tuple[str, str]] = {
    "morning": ("09:00", "12:00"),
    "afternoon": ("12:00", "17:00"),
    "evening": ("17:00", "21:00"),
    "full_day": ("09:00", "18:00"),
}

# All "today/tomorrow" logic uses this IANA timezone (Section 2; cloud servers run UTC).
TIMEZONE_NAME = "Asia/Kolkata"

# Availability passes if overlap >= min(MIN_BOOKING_HOURS, requested duration).
MIN_BOOKING_HOURS = 2

# --- Vocabulary (Sections 6-7): the only amenity strings allowed anywhere ---
AMENITIES: tuple[str, ...] = (
    "whiteboard",
    "projector",
    "video_conferencing",
    "printer",
    "monitor",
    "standing_desk",
    "coffee_machine",
    "phone_booth",
    "locker",
    "parking",
    "air_conditioning",
    "power_backup",
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

# parser.parse retries this many times on invalid JSON/schema before raising ParseError (Section 9).
PARSE_MAX_RETRIES = 1

# Facts (Step 5): tradeoff thresholds.
NEAR_BUDGET_MARGIN_PCT = 15.0  # price within this percent of the limit is a tradeoff.
LOW_REVIEW_LIMIT = 10  # fewer reviews than this is a tradeoff.

# --- LLM settings (Section 7) ---
LLM_TEMPERATURE = 0.0
LLM_TIMEOUT_SECONDS = 30.0
LLM_MAX_RETRIES = 2  # on timeout or rate limit, with LLM_BACKOFF_SECONDS between tries.
LLM_JSON_RETRIES = 1  # on invalid JSON or an empty answer.
LLM_BACKOFF_SECONDS = 2.0  # "short backoff"; exact value chosen here, review at Gate 2/3.
LLM_REASONING_EFFORT = "low"  # lowest value Groq accepts for gpt-oss (live-verified 2026-10-01).
LLM_MAX_TOKENS = 4096  # per-answer output cap; reasoning tokens count toward it.

# --- Step 8: pipeline messages (code templates; never LLM text) ---
# Percent -> fraction divisor: normalizes budget_over_pct for alternative ordering.
PERCENT_SCALE = 100.0

# Whole-city names: exact match (after strip+casefold) against the unrecognized location
# decides "which area?" instead of a coverage rejection; never a substring check.
CITY_NAMES: tuple[str, ...] = ("mumbai", "bombay")

MSG_EMPTY_QUERY = "Please type what you're looking for - e.g. a quiet desk in Bandra for 2 tomorrow afternoon."
MSG_LLM_ERROR = "Something went wrong reaching the AI service. Please try again in a moment."
MSG_PARSE_ERROR = "Something went wrong understanding your request. Please try again with different wording."
MSG_UNSUPPORTED_BUDGET = "I can't use a per-day or per-month budget. Please give an hourly budget, e.g. Rs. 600 per person per hour."
MSG_MISSING_INFO = "I need at least one of: an area, a group size, an hourly budget, or a date/time. We cover these Mumbai areas: {areas}."
MSG_COVERAGE = "I couldn't place \"{area}\" - I can only search these Mumbai areas: {areas}."
MSG_CITY_NO_AREA = "Which area of Mumbai? I can search: {areas}."
MSG_NO_MATCH = "No space matches every requirement. The main blockers: {reasons}."
NOTE_DEFAULT_PARTY_SIZE = "No group size given; assuming 1 person for per-person pricing."

# Per-constraint advice rendered into MSG_NO_MATCH (key = Violations category).
NO_MATCH_LOOSEN: dict[str, str] = {
    "location": "try another covered area",
    "capacity": "try a smaller group",
    "budget": "try a higher budget",
    "time": "try another date or time",
    "space_type": "try a different space type: hot desk, private cabin, or meeting room",
}

# --- Step 9: Explainer and Validator ---
AMENITY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "whiteboard": ("board", "marker board"),
    "projector": ("beamer", "screen projection"),
    "video_conferencing": ("zoom", "skype", "vc", "camera"),
    "printer": ("printing",),
    "monitor": ("screen", "display", "external monitor"),
    "standing_desk": ("standup desk", "standing"),
    "coffee_machine": ("coffee", "espresso", "cafe"),
    "phone_booth": ("booth", "call room", "private booth"),
    "locker": ("storage", "safe"),
    "parking": ("car park", "garage"),
    "air_conditioning": ("ac", "a/c", "aircon"),
    "power_backup": ("generator", "ups", "backup"),
    "pool": ("swimming pool",),
    "gym": ("fitness",)
}


BUDGET_OVER_PHRASES = ["over budget", "above budget", "exceeds budget"]
BUDGET_UNDER_PHRASES = ["under budget", "within budget", "meets budget", "on budget"]
BUDGET_NEAR_PHRASES = ["near budget", "close to budget", "close to the budget limit", "near the budget limit"]

NOISE_SYNONYMS = {
    "quiet": ["quiet", "silent", "peaceful", "calm"],
    "moderate": ["moderate", "normal", "average"],
    "lively": ["lively", "noisy", "bustling", "vibrant", "active"]
}
