DRAFT, HUMAN TO REWRITE IN OWN WORDS

# Reflection: Risks and Mitigations

As an AI-driven platform operating in a real-world commercial setting, CoSearch faces structural risks that require deliberate mitigations.

## 1. Hallucination and Grounding
**The Risk:** Large Language Models invent details. In a coworking marketplace, inventing a "rooftop pool" or hallucinating a "₹200/hr" price when the space costs ₹2000/hr breaches user trust and can incur legal or commercial liabilities.
**Current Mitigation:** Our platform implements a strict separation of concerns. The LLM handles text translation, while Python handles mathematical logic and facts. The final output is independently verified by `validator.py` which scans the generated response against a list of allowed numerical values and valid amenities. If a hallucination is detected, the system retries once and then defaults to a deterministic code template.
**Residual Risk:** The current validator is rigid. Stylistic hallucinations or odd phrasing (e.g., describing a noisy room as "vibrant") might slip past numerical/amenity filters. It can also produce robotic-sounding fallbacks when the LLM repeatedly fails.

## 2. Ranking Bias
**The Risk:** Organic ranking systems inherently produce biases based on how their formulas value user data and historical records.
**Current Bias:** 
- **Price Fit Bias:** The `price_fit` term strictly favors cheaper listings relative to the user's budget. Nothing explicitly favors expensive listings.
- **Bayesian Trust Bias:** We use a Bayesian average initialized with a confidence weight (`C=20`) anchored to the dataset mean (`m`). This strictly favors established listings with many reviews over newly added spaces.
- **Capacity limitation:** Capacity does not receive a ranking bonus; it is treated purely as a hard constraint.
- **No Paid Placements:** The ranking is strictly organic.
**Future Mitigation:** Ongoing fairness auditing should be implemented to ensure the distribution of impressions remains healthy for new market entrants.

## 3. Stale Availability
**The Risk:** The platform currently relies on static weekly recurring availability blocks (e.g., "Mondays 9-5"). In a real marketplace, a room might be organically booked by another user five minutes prior, leading the AI to recommend a space that is physically unavailable.
**Current Mitigation / Limitation:** This is acknowledged as a structural limitation of the current demonstration data structure.
**Future Mitigation:** 
- Implementing live availability checks executed at the final rendering or booking stage.
- Using optimistic UI labels (e.g., *"Usually available at this time"* rather than *"Available"*).
- Attaching API freshness timestamps to cached data to warn users when availability data might be slightly stale.
