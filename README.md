DRAFT, HUMAN TO REWRITE IN OWN WORDS

# CoSearch

CoSearch is an AI-powered natural-language search platform for a coworking marketplace. Users can type plain-language requests (e.g., "quiet place for 4 people in Bandra tomorrow afternoon, under 600 per person per hour, with a whiteboard") and the system interprets hard constraints and soft preferences to return the best-matching, fully grounded results.

<!-- App Screenshot placeholder: add screenshot.png to the repository root to display here -->
![App Screenshot Placeholder](screenshot.png)

## Features
- **Natural Language Parsing**: Understands intent, groups, times, budgets, locations, and soft preferences without complex form UI.
- **Strict Hard Constraints**: Enforces budgets, availability, capacity, and location accurately via pure code, significantly reducing AI hallucination for critical facts.
- **Smart Ranking & Fallback**: Ranks listings based on fit, trust, and price. Gracefully relaxes only the constraints permitted by the system rules to show the closest alternatives (ALTERNATIVES) if an exact match isn't found, while preserving hard constraints that must never be relaxed (including capacity and explicit space type), or prompts for clarification (CLARIFY).
- **Grounded AI Explanations**: Generates natural-language trade-off explanations strictly validated against mathematical constraints.

## Architecture

`	ext
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
`

## Local Setup

### 1. Requirements
Ensure you have Python 3.12 installed.

### 2. Installation
Create a virtual environment and install dependencies:
`ash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
`

### 3. Environment Variables
Create a .env file in the project root:
`env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
`

### 4. Running the Application
Start the Streamlit UI:
`ash
streamlit run app.py
`

## Testing and Evaluation

**Run Pytests (120 tests):**
`ash
python -m pytest
`

**Run End-to-End Evaluation:**
`ash
python eval/run_eval.py
`
This runs exactly 20 queries (12 normal, 8 messy/adversarial) against the real pipeline and generates an evaluation report in eval/results.md and eval/results.csv.

## Streamlit Community Cloud Deployment
1. Push this repository to GitHub.
2. Log into Streamlit Community Cloud and click "New app".
3. Select this repository and branch. Set the main file path to pp.py.
4. Before deploying, go to **Advanced Settings -> Secrets** and paste the production credentials:
`	oml
LLM_API_KEY = "your_api_key_here"
LLM_BASE_URL = "https://api.groq.com/openai/v1"
LLM_MODEL = "openai/gpt-oss-20b"
`
5. Click **Deploy**.

## Note on Synthetic Data
All 40 listings provided in data/listings.json are entirely synthetic and generated for demonstration purposes. Location coordinates are strictly approximate representations of actual Mumbai areas (e.g. Bandra, BKC, Powai) generated around central coordinates.

## Limitations
- **Availability is Static:** The platform currently uses recurring weekly static schedules rather than live booking checks.
- **Coverage:** Only 8 specific Mumbai areas are currently searchable.
- **Strictly Data-Driven:** The system relies entirely on the provided vocabulary in src/config.py and does not guess unstructured features or invent listings outside of the JSON dataset.
