import os
import streamlit as st
from src import config
from src.schemas import Outcome, SearchResponse
from src.pipeline import search
from src.data_loader import load_listings
from ui.styles import get_styles
from ui.components import render_parsed_query, render_result_card, render_message
from ui.map_view import render_map

# Load secrets to os.environ at startup
def init_secrets():
    for key in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]:
        try:
            if key in st.secrets:
                os.environ.setdefault(key, st.secrets[key])
        except FileNotFoundError:
            pass

# Cache the dataset
@st.cache_data
def get_cached_listings():
    return load_listings()

def init_session_state():
    if "search_count" not in st.session_state:
        st.session_state.search_count = 0
    if "last_response" not in st.session_state:
        st.session_state.last_response = None
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""

def run_search(query: str):
    if not query.strip():
        return
    
    # Limit check
    if st.session_state.search_count >= config.SESSION_SEARCH_LIMIT:
        st.session_state.last_response = SearchResponse(
            outcome=Outcome.CLARIFY,
            message=config.UI_LIMIT_MESSAGE
        )
        return
        
    # Check for API keys BEFORE search
    if not all(os.environ.get(k) for k in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]):
        st.session_state.last_response = SearchResponse(
            outcome=Outcome.CLARIFY,
            message=config.UI_MISSING_KEY_MESSAGE
        )
        return
        
    # Run the actual search
    st.session_state.search_count += 1
    with st.spinner("Searching..."):
        try:
            response = search(query)
            st.session_state.last_response = response
        except Exception:
            # Catching generic unhandled exceptions as a final safety net
            st.session_state.last_response = SearchResponse(
                outcome=Outcome.CLARIFY,
                message=config.MSG_LLM_ERROR
            )

def main():
    st.set_page_config(page_title="CoSearch", layout="wide")
    init_secrets()
    init_session_state()
    get_cached_listings() # Warm up the cache
    
    st.markdown(get_styles(), unsafe_allow_html=True)
    
    st.title("CoSearch")
    st.write("Natural-language search for coworking spaces in Mumbai.")
    
    # Example buttons
    st.write("Try an example:")
    cols = st.columns(4)
    for i, ex_query in enumerate(config.UI_EXAMPLE_QUERIES):
        if cols[i].button(ex_query, key=f"ex_{i}"):
            st.session_state.search_query = ex_query
            run_search(ex_query)
            
    # Search Bar
    query = st.text_input("What are you looking for?", key="search_query")
    if st.button("Search", type="primary"):
        run_search(query)
        
    # Render Output
    response = st.session_state.last_response
    if response:
        st.markdown("---")
        
        try:
            # Parsed query panel
            if response.parsed_query:
                render_parsed_query(response.parsed_query)
                
            # Clarify / No Match
            if response.outcome in (Outcome.CLARIFY, Outcome.NO_MATCH):
                render_message(response.message or "No match found.")
                
            # Results / Alternatives
            if response.outcome in (Outcome.RESULTS, Outcome.ALTERNATIVES):
                if response.outcome == Outcome.ALTERNATIVES:
                    render_message(response.message or config.UI_ALT_BANNER)
                
                tab1, tab2 = st.tabs(["Results", "Map"])
                with tab1:
                    is_alt = (response.outcome == Outcome.ALTERNATIVES)
                    for item in response.results:
                        render_result_card(item, response.parsed_query, is_alternative=is_alt)
                with tab2:
                    render_map(response.results)
                    
            # Notes
            if response.notes:
                for note in response.notes:
                    st.info(note)
        except Exception as e:
            import logging
            logging.error(f"Render exception: {e}", exc_info=True)
            render_message(config.UI_RENDER_ERROR_MESSAGE)
                
    st.markdown("---")
    st.markdown(f"<div style='text-align: center; color: #6c757d;'>{config.UI_FOOTER}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
