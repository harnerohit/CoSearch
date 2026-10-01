DRAFT, HUMAN TO REWRITE IN OWN WORDS

# Design Note: Architecture and Scale

## Overall Approach & Philosophy
CoSearch embraces a strict split between generative AI (LLMs) and deterministic code.
- **LLM Responsibility:** Translating messy natural language into structured formats (Parsing) and phrasing computed trade-offs into natural prose (Explaining).
- **Code Responsibility:** Filtering, ranking, metric normalization, limit enforcement, and determining search outcomes (`RESULTS`, `ALTERNATIVES`, `CLARIFY`, `NO_MATCH`).

By assigning math, filtering, and constraint enforcement to code, we provide deterministic mathematical correctness for pricing, party sizes, and geospatial calculations—areas where LLMs can struggle.

## Hard vs Soft Constraints
- **Hard Constraints:** Area/Location, Capacity, Total/Per-Person Budget, Time/Date Availability, and Space Type (if explicitly stated). If a listing fails any hard constraint, it is unconditionally removed from standard `RESULTS`.
- **Soft Preferences:** Noise level, Wifi speed, and specific Amenities (e.g. whiteboard, coffee machine). These affect the ranking score (`fit`) but never hide a listing.

## Ranking System
The ranker uses a weighted formula to generate a normalized 0-to-1 score. The base weights are:
`Score = (0.45 × Soft Fit) + (0.30 × Trust) + (0.25 × Price Fit)`

- **Fit:** The average of the noise score, the Wi-Fi fraction (wifi/100, capped at 1.0), and a 1-or-0 score for each requested amenity.
- **Trust:** A Bayesian average `(C×m + n×r) / (C + n)` where `C=20` and `m` is the dataset mean rating. Using the verified dataset mean `m=4.1385`, a listing with `n=1` and `r=5.0` yields a trust score of 0.836, which mathematically loses to a proven listing with `n=200` and `r=4.7` yielding a trust score of 0.930.
- **Price:** Normalizes how far under budget a listing is. 
- **Renormalization:** If the user provides no soft preferences or no budget, that respective term is dropped and the remaining weights are proportionally renormalized.
- **No Sponsored Boosts:** The ranking logic operates organically based purely on user preference and proven quality. No paid boosts or hidden commission logic influences the sorting.

## Grounding and Validator Design
To mitigate the risk of LLM hallucinations during explanation generation:
1. `explainer.py` receives computed mathematical facts, matched/missed features, and explicitly allowed numerical limits (e.g., budget size, capacity limits).
2. `validator.py` independently verifies the generated string against those numbers and amenity sets.
3. If validation fails, a fallback deterministic template (e.g., *"Fits your budget and capacity; trade-off: it lacks a whiteboard"*) is deployed after exactly one retry.

## Swappable Provider and Plain Python
Python application logic uses the standard library/Pydantic where appropriate, with Streamlit for UI, Folium/streamlit-folium for maps, the OpenAI-compatible client for LLM calls, and generic LLM environment variables (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`) for provider configuration.
- **Why no Frameworks?** LangChain, LangGraph, and other agent frameworks introduce opacity, dependency bloat, and unexpected retry logic. Using plain Python provides complete audibility and predictable latency.
- **Why Groq?** Groq endpoints offer high tokens-per-second, which is well-suited to keeping user-facing search queries under typical web latency expectations.

## Future Scaling: 100,000+ Listings
While currently loading 40 synthetic listings from a JSON file, scaling to 100k+ requires a fundamental architecture shift. Currently:
- `load_listings()` loads the full JSON dataset.
- `check_listing()` is applied linearly across all listings.
- `rank()` sorts the candidates in memory.
- Only the top 5 `RESULTS` or top 3 `ALTERNATIVES` are explained and mapped.

The main scaling changes should therefore be:
1. **Database & Spatial Indexing:** Pre-filtering on geographic boxes, hard capacity limits, and pricing.
2. **Database-side Sorting:** Moving filtering and ranking logic to the database.
3. **Embeddings & Hybrid Search:** Soft preferences would move from exact matching to vector search to accommodate variations in amenity descriptions across thousands of diverse locations.
4. **LLM Reranking & Caching:** The LLM would evaluate and rerank only the top 20–50 post-filtered results to maintain latency. Parse outputs would be aggressively cached.
5. **Batching & Rate Limiting:** High-volume traffic requires request batching and enforced API rate limit management.
6. **Live Systems:** Integration of a real-time availability service rather than static blocks.
7. **Continuous Evaluation:** Moving beyond synthetic queries to offline evaluations run on logged real user queries.
