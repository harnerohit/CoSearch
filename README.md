# CoSearch

CoSearch is an AI-powered natural-language search platform for a coworking marketplace. Users can type plain-language requests (e.g., "quiet place for 4 people in Bandra tomorrow afternoon, under 600 per person per hour, with a whiteboard") and the system interprets hard constraints and soft preferences to return the best-matching, fully grounded results.

## Features

- **Natural-Language Parsing:** Understands intent, groups, times, budgets, locations, and soft preferences without complex form UI.
- **Hard/Soft Constraint Handling:** Differentiates between hard constraints (capacity, location, budget, availability) and soft preferences (noise level, Wi-Fi speed, amenities).
- **Deterministic Filtering and Ranking:** Enforces constraints mathematically via pure Python code, and ranks using fit, trust (Bayesian average), and price.
- **Search Outcomes:** Automatically decides between `RESULTS`, `ALTERNATIVES` (relaxing permitted constraints while holding strict limits like capacity), `CLARIFY` (when required fields are missing or location is unsupported), or `NO_MATCH`.
- **Grounded Explanations:** Generates natural-language trade-off explanations that are independently verified by a code-based validator. Uses exactly one retry followed by a deterministic template fallback on failure.
- **Results and Map UI:** A clean Streamlit interface displaying top matches and their coordinates.
- **Synthetic Listing Dataset:** Includes exactly 40 varied synthetic coworking spaces spanning 8 Mumbai areas.

## Architecture

```text
user query
   │
   ▼
[parser.py]    LLM    query → ParsedQuery (hard constraints, soft prefs, ambiguities)
   │                  
   ▼
[pipeline.py]  code   decides outcome: CLARIFY / RESULTS / ALTERNATIVES / NO_MATCH
   │
   ├─ [filters.py]   code   hard-constraint check per listing, with violation sizes
   ├─ [ranker.py]    code   score = fit + trust + price, deterministic
   ├─ [geo.py]       code   haversine distance
   ▼
[explainer.py] LLM    top results + code-computed facts → 1-2 sentence explanations
   │
   ▼
[validator.py] code   rejects any explanation containing facts not in the listing
   │                  (retry once, then deterministic template fallback)
   ▼
[app.py / ui/] Streamlit: parsed-request panel, result cards, numbered map
```

- **LLM vs Code Split:** The LLM is strictly used to parse the initial messy natural language into structured formats, and phrase computed trade-offs into natural prose. 
- **Deterministic Logic:** Code does all the filtering, ranking, distance computing, availability checking, and outcome deciding. 
- **No Hallucinated Listings:** The LLM never decides which listings are valid. It never looks at the database itself to filter. It only formats what the code allows.

## Local Setup

### 1. Requirements
Ensure you have Python 3.12 installed.

### 2. Installation
Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the project root:
```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
```

### 4. Running the Application
Start the Streamlit UI:
```bash
streamlit run app.py
```

## Testing

Run the full pytest suite (120 tests):
```bash
python -m pytest
```

## Evaluation

Run the end-to-end evaluation:
```bash
python eval/run_eval.py
```
The curated 20-query evaluation produced:
- 20/20 expected outcomes
- 20/20 parse correctness
- 0 hard-constraint violations among RESULTS
- 0 fabrication failures

*(Note: This result applies to the evaluated query set only.)*

## Streamlit Community Cloud Deployment

1. Push this repository to GitHub.
2. Log into Streamlit Community Cloud and click "New app".
3. Select this repository and branch. Set the main file path to `app.py`.
4. Before deploying, go to **Advanced Settings -> Secrets** and paste the production credentials:
```toml
LLM_API_KEY = "your_api_key_here"
LLM_BASE_URL = "https://api.groq.com/openai/v1"
LLM_MODEL = "openai/gpt-oss-20b"
```
5. Click **Deploy**.

## Note on Synthetic Data

All 40 listings provided in `data/listings.json` are entirely synthetic and generated for demonstration purposes. Location coordinates are strictly approximate representations of actual Mumbai areas (e.g. Bandra, BKC, Powai) generated around central coordinates.

## Limitations

- **Availability is Static:** The platform currently uses recurring weekly static schedules rather than live booking checks.
- **Coverage:** Only 8 specific Mumbai areas are currently searchable.
- **Strictly Data-Driven:** The system relies entirely on the provided vocabulary in `src/config.py` and does not guess unstructured features or invent listings outside of the JSON dataset.
