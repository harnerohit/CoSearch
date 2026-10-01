import pytest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.schemas import SearchResponse, Outcome, ParsedQuery, ResultItem, Budget, BudgetBasis, SoftPreferences, SpaceType, TimeWindow
import os
import datetime
from src.data_loader import load_listings

@pytest.fixture
def dummy_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test_key")
    monkeypatch.setenv("LLM_BASE_URL", "http://test")
    monkeypatch.setenv("LLM_MODEL", "test_model")

def test_ui_renders_all_outcomes(dummy_env):
    listings = load_listings()
    base_listing = listings[0]
    
    outcomes_to_test = [
        Outcome.CLARIFY,
        Outcome.NO_MATCH,
        Outcome.RESULTS,
        Outcome.ALTERNATIVES
    ]
    
    parsed = ParsedQuery(
        location="Bandra",
        party_size=4,
        date=datetime.date(2026, 10, 2),
        budget=Budget(amount=500, basis=BudgetBasis.PER_PERSON_PER_HOUR),
        time_window=TimeWindow(start="12:00", end="17:00"),
        space_type=SpaceType.HOT_DESK,
        soft=SoftPreferences(quiet=True, min_wifi="fast", amenities=[]),
        unmatched_preferences=["pet friendly"]
    )
    
    results = [
        ResultItem(
            rank=1,
            listing=base_listing,
            score=0.9,
            facts={"matched": ["area"], "missed": ["amenity=whiteboard"]},
            explanation="Good fit.",
            explanation_source="template"
        )
    ]
    
    with patch("src.pipeline.search") as mock_search:
        for outcome in outcomes_to_test:
            mock_search.return_value = SearchResponse(
                outcome=outcome,
                parsed_query=parsed if outcome != Outcome.CLARIFY else None,
                results=results if outcome in (Outcome.RESULTS, Outcome.ALTERNATIVES) else [],
                message="Mock message" if outcome in (Outcome.CLARIFY, Outcome.NO_MATCH) else None,
                notes=["Mock note"]
            )
            
            at = AppTest.from_file("../app.py")
            at.run()
            
            # Click a search button or input text
            # The example buttons have keys "ex_0", "ex_1", etc. We can just click the first one.
            at.button(key="ex_0").click().run()
            
            # Assert no unhandled exceptions occurred in the Streamlit runner
            assert not at.exception
            
            # If ALTERNATIVES, verify the banner appears
            if outcome == Outcome.ALTERNATIVES:
                assert "No exact match. Closest options:" in at.markdown[-2].value or any("Closest options" in m.value for m in at.markdown)

def test_ui_html_formatting_and_escaping(dummy_env):
    listings = load_listings()
    base_listing = listings[0]
    
    # Inject malicious values
    base_listing.name = "<script>alert(1)</script>"
    
    parsed = ParsedQuery(
        location="Bandra",
        party_size=1,
        date=datetime.date(2026, 10, 2),
        budget=Budget(amount=500, basis=BudgetBasis.PER_PERSON_PER_HOUR),
        time_window=TimeWindow(start="12:00", end="17:00"),
        space_type=SpaceType.HOT_DESK,
        soft=SoftPreferences(quiet=True, min_wifi="fast", amenities=[]),
        unmatched_preferences=["<script>alert(1)</script>"]
    )
    
    results = [
        ResultItem(
            rank=1,
            listing=base_listing,
            score=0.9,
            facts={"matched": ["area"]},
            explanation="Line 1.\n\n<script>alert(1)</script>",
            explanation_source="llm"
        )
    ]
    
    with patch("src.pipeline.search") as mock_search:
        for outcome in [Outcome.RESULTS, Outcome.ALTERNATIVES]:
            mock_search.return_value = SearchResponse(
                outcome=outcome,
                parsed_query=parsed,
                results=results
            )
            
            at = AppTest.from_file("../app.py")
            at.run()
            at.button(key="ex_0").click().run()
            
            assert not at.exception
            
            html_output = ""
            for mkd in at.markdown:
                html_output += mkd.value + "\n"
                
            # Assert missing <script> and presence of &lt;script&gt;
            assert "<script>" not in html_output, f"Found unescaped <script> tag for outcome {outcome}"
            assert "&lt;script&gt;" in html_output, f"Missing escaped &lt;script&gt; tag for outcome {outcome}"
            
            # Assert newline collapsing explicitly
            assert "Line 1.\n\n" not in html_output, "Newline was not collapsed!"
            assert "Line 1.  &lt;script&gt;alert(1)&lt;/script&gt;" in html_output, "Collapsed text not found in output!"
            
            # Check for 4-space indented lines in HTML output
            for mkd in at.markdown:
                val = mkd.value
                if "result-card" in val and "<style>" not in val:
                    for line in val.split("\n"):
                        assert not line.startswith("    "), f"Found 4-space indented line which markdown parses as code: '{line}'"
                        
def test_ui_no_blank_lines_in_html(dummy_env):
    listings = load_listings()
    base_listing = listings[0]
    
    parsed = ParsedQuery(
        location="Bandra",
        party_size=1,
        date=datetime.date(2026, 10, 2),
        budget=Budget(amount=500, basis=BudgetBasis.PER_PERSON_PER_HOUR),
        time_window=TimeWindow(start="12:00", end="17:00"),
        space_type=SpaceType.HOT_DESK,
        soft=SoftPreferences(quiet=True, min_wifi="fast", amenities=[]),
        unmatched_preferences=[]
    )
    
    # Empty explanation to trigger potential blank lines
    results = [
        ResultItem(
            rank=1,
            listing=base_listing,
            score=0.9,
            facts={"matched": ["area"]},
            explanation="",
            explanation_source="template"
        )
    ]
    
    with patch("src.pipeline.search") as mock_search:
        mock_search.return_value = SearchResponse(
            outcome=Outcome.RESULTS,
            parsed_query=parsed,
            results=results
        )
        
        at = AppTest.from_file("../app.py")
        at.run()
        at.button(key="ex_0").click().run()
        
        assert not at.exception
        
        for mkd in at.markdown:
            val = mkd.value
            if "result-card" in val and "<style>" not in val:
                # Assert no blank lines or lines with just spaces in the markdown block
                lines = val.split("\n")
                for i, line in enumerate(lines):
                    # In markdown, a blank line breaks the HTML block
                    assert line.strip() != "", f"Found blank line in HTML at line {i}: {repr(line)}"
