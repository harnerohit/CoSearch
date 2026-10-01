import sys
import os
sys.path.insert(0, os.path.abspath('.'))
import csv
import json
import time
import pandas as pd
from pathlib import Path
from src.pipeline import search
from src.schemas import Outcome, ResultItem
from src.validator import validate_explanation
from src.facts import build_display_data, compute_facts
from src.filters import check_listing

def run_evaluation():
    queries_file = Path('eval/test_queries.csv')
    if not queries_file.exists():
        print("Queries file not found")
        return
        
    results = []
    
    with open(queries_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row['id']
            category = row['category']
            qtext = row['query']
            expected_outcome = row['expected_outcome']
            expected_json = json.loads(row['expected_json'])
            
            print(f"Running {qid}: {qtext[:50]}...")
            
            start_t = time.time()
            response = search(qtext)
            latency = time.time() - start_t
            
            outcome_correct = (response.outcome.name == expected_outcome)
            
            # Check parse fields (case insensitive for strings)
            parse_correct = True
            if response.parsed_query:
                parsed_dict = response.parsed_query.model_dump(exclude_none=True)
                for k, v in expected_json.items():
                    val = parsed_dict.get(k)
                    if isinstance(val, str) and isinstance(v, str):
                        if val.lower() != v.lower():
                            parse_correct = False
                    elif isinstance(val, bool) or isinstance(val, int):
                        if val != v:
                            parse_correct = False
                    elif hasattr(val, 'value'): # Enum
                        if val.value.lower() != str(v).lower():
                            parse_correct = False
            else:
                if expected_json: 
                    parse_correct = False
                    
            hard_violations = 0
            fabrication_failed = 0
            sources = []
            
            if response.outcome == Outcome.RESULTS:
                for item in response.results:
                    sources.append(item.explanation_source or "unknown")
                    # Hard constraints violation check
                    listing = item.listing
                    pq = response.parsed_query
                    if pq:
                        if pq.location and pq.location.lower() != listing.area.lower():
                            hard_violations += 1
                        if pq.party_size and listing.capacity < pq.party_size:
                            hard_violations += 1
                        if pq.space_type and listing.space_type.value != pq.space_type.value:
                            hard_violations += 1
                    
                    # Fabrication check completely independent from item.facts
                    is_valid = True
                    if pq:
                        violation = check_listing(listing, pq)
                        recomputed_facts = compute_facts(listing, pq, violation)
                        disp = build_display_data(listing, pq, recomputed_facts, item.rank, False)
                        is_valid, reason = validate_explanation(item.explanation, listing, disp["allowed_numbers"], disp["missed_amenities"], response.results)
                    if not is_valid:
                        fabrication_failed += 1

            results.append({
                "id": qid,
                "category": category,
                "query": qtext,
                "expected_outcome": expected_outcome,
                "actual_outcome": response.outcome.name,
                "outcome_correct": outcome_correct,
                "parse_correct": parse_correct,
                "hard_violations": hard_violations,
                "fabrication_failed": fabrication_failed,
                "explanation_sources": ",".join(sources) if sources else "none",
                "latency_s": round(latency, 2),
                "notes": row['notes']
            })
            
            time.sleep(3.0)
            
    df = pd.DataFrame(results)
    df.to_csv('eval/results.csv', index=False)
    
    cols = df.columns.tolist()
    header = "| " + " | ".join(cols) + " |"
    separator = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(val) for val in row.values) + " |")
    md_table = "\n".join([header, separator] + rows)

    md_lines = [
        "# DRAFT, HUMAN TO REVIEW\n\n",
        "## Evaluation Results\n\n",
        "### Summary Table\n\n",
        md_table + "\n\n",
        "### Failures\n\n"
    ]
    
    failures = df[(~df['outcome_correct']) | (~df['parse_correct']) | (df['hard_violations'] > 0) | (df['fabrication_failed'] > 0)]
    if failures.empty:
        md_lines.append("No failures found!\n")
    else:
        for _, row in failures.iterrows():
            md_lines.append(f"#### Query: {row['id']} ({row['category']})\n")
            md_lines.append(f"- **Query:** {row['query']}\n")
            md_lines.append(f"- **Expected Outcome:** {row['expected_outcome']}, **Actual:** {row['actual_outcome']}\n")
            md_lines.append(f"- **Outcome Correct:** {row['outcome_correct']}\n")
            md_lines.append(f"- **Parse Correct:** {row['parse_correct']}\n")
            md_lines.append(f"- **Hard Violations:** {row['hard_violations']}\n")
            md_lines.append(f"- **Fabrication Failures:** {row['fabrication_failed']}\n")
            md_lines.append(f"\n**Why it failed:**\n")
            if not row['outcome_correct']:
                md_lines.append(f"The LLM returned {row['actual_outcome']} instead of the expected {row['expected_outcome']}. ")
            if not row['parse_correct']:
                md_lines.append(f"The LLM failed to accurately extract constraints matching expected JSON. ")
            if row['fabrication_failed'] > 0:
                md_lines.append(f"The LLM hallucinated an amenity or fact. ")
            md_lines.append(f"\n\n**Proposed fix:** Review LLM parsing instructions or fix expected outputs.\n\n")
            
    with open('eval/results.md', 'w', encoding='utf-8') as f:
        f.writelines(md_lines)
        
    print("\nEvaluation complete. Wrote results.csv and results.md")
    print(df[['id', 'outcome_correct', 'parse_correct', 'hard_violations', 'fabrication_failed']].to_string())

if __name__ == '__main__':
    run_evaluation()

