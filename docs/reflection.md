# Reflection: Risks and Mitigations

As an AI-driven platform operating in a real-world commercial setting, CoSearch faces structural risks that require deliberate mitigations. This reflection details three primary risk areas, distinguishing between current implementations, current limitations, and future mitigations.

## 1. Hallucination and Grounding

Large Language Models (LLMs) can generate unsupported facts, such as inventing amenities or misstating prices.

**Current Implementation:** In this project, the LLM is explicitly separated from hard filtering and ranking decisions. Code strictly computes the listing facts. The `validator.py` module then checks the LLM-generated explanations against allowed facts. If validation fails, the system retries once and then falls back to a deterministic code-generated template. During Step 11, our independent evaluation recomputed grounding facts and reported 0 fabrication failures across the curated 20-query evaluation set. 

**Current Limitation:** While the 20-query evaluation reported 0 failures, this does not prove zero hallucinations for all possible future inputs.

**Residual Risk:** The true residual risk is that the validator is rule-based. It may miss unsupported stylistic or paraphrased claims that fall outside its current specific rule checks.

## 2. Ranking Bias

Ranking algorithms inherently introduce biases based on the formulas used. 

**Current Implementation:** 
- The `price_fit` component favors listings that are cheaper relative to the user's budget.
- Bayesian trust gives more weight to established review histories compared to very small review counts.
- Capacity does not receive a ranking bonus; it acts purely as a hard constraint filter.
- Nothing in the current ranking logic explicitly rewards expensive or premium listings.
- There are no paid placements or commission-based ranking boosts.

**Current Limitation:** The 20-query evaluation did not measure ranking fairness; it only tested constraint enforcement.

**Future Mitigation:** Fairness auditing should be implemented as a future mitigation to monitor the distribution of exposure, especially ensuring newer listings receive appropriate visibility against established competition.

## 3. Stale Availability

**Current Implementation & Limitation:** The current dataset uses static, weekly recurring availability windows. This is fundamentally different from real-time booking availability. A listing could realistically become unavailable after the static schedule claims it is available. The current prototype does not maintain live booking state, meaning this risk is acknowledged as a structural limitation of the demonstration.

**Future Mitigation:**
To mitigate this in a production system, future implementation should include:
- Live availability checks executed at search and booking time.
- Freshness timestamps on cached data to inform users.
- Cautious or optimistic availability wording (e.g., *"Usually available"*) when appropriate.
