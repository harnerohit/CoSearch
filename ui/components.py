import streamlit as st
import html
import textwrap
from src import config
from src.schemas import ParsedQuery, ResultItem, BudgetBasis
from src.filters import budget_price, party_size_for

def _clean(text: str) -> str:
    """Escape HTML and collapse newlines so markdown doesn't break."""
    return html.escape(text.replace('\n', ' ').replace('\r', ''))

def render_message(text: str, msg_type: str = "info") -> None:
    valid_classes = {"info": "msg-info", "warning": "msg-warning", "error": "msg-error"}
    css_class = valid_classes.get(msg_type, "msg-info")
    st.markdown(f'<div class="msg-box {css_class}">{_clean(text)}</div>', unsafe_allow_html=True)

def render_parsed_query(parsed: ParsedQuery) -> None:
    html_str = '<div class="parsed-query-box">'
    html_str += '<h4 style="margin-top: 0; color: #495057;">What I understood</h4>'
    html_str += '<div class="chip-container">'
    
    # Hard constraints
    if parsed.location:
        html_str += f'<span class="chip chip-hard">📍 {_clean(parsed.location)}</span>'
    if parsed.space_type:
        html_str += f'<span class="chip chip-hard">🏢 {parsed.space_type.value.replace("_", " ").title()}</span>'
    if parsed.party_size:
        html_str += f'<span class="chip chip-hard">👥 {parsed.party_size} People</span>'
    if parsed.date:
        html_str += f'<span class="chip chip-hard">📅 {parsed.date.isoformat()}</span>'
    if parsed.time_window:
        html_str += f'<span class="chip chip-hard">⏰ {parsed.time_window.start} - {parsed.time_window.end}</span>'
    if parsed.budget:
        basis_str = "Total/hr" if parsed.budget.basis == BudgetBasis.TOTAL_PER_HOUR else "Per person/hr"
        html_str += f'<span class="chip chip-hard">💰 ₹{parsed.budget.amount} {basis_str}</span>'
        
    # Soft constraints
    if parsed.soft.quiet:
        html_str += '<span class="chip chip-soft">🔊 Quiet</span>'
    if parsed.soft.min_wifi == "fast":
        html_str += '<span class="chip chip-soft">📶 Fast WiFi</span>'
    for am in parsed.soft.amenities:
        html_str += f'<span class="chip chip-soft">✨ {am.value.replace("_", " ").title()}</span>'
        
    # Unmatched preferences
    if parsed.unmatched_preferences:
        for um in parsed.unmatched_preferences:
            html_str += f'<span class="chip chip-unmatched">❓ {_clean(um)}</span>'
            
    html_str += '</div></div>'
    st.markdown(html_str, unsafe_allow_html=True)
    
    if parsed.unmatched_preferences:
        st.info("Note: The items in red couldn't be matched to standard amenities.")

def render_result_card(item: ResultItem, parsed: ParsedQuery | None, is_alternative: bool = False) -> None:
    listing = item.listing
    
    # Header: Rank Badge, Title, Rank (for alternatives if needed, but badge has rank)
    header_html = textwrap.dedent(f"""
<div class="result-card-header">
<div>
<span class="rank-badge">#{item.rank}</span>
<span class="card-title">{_clean(listing.name)}</span>
</div>
<div class="price-block">
₹{listing.price_per_hour}<span class="price-unit"> / hr</span>
</div>
</div>
    """)
    
    # Subtitle info: space type, area, capacity
    subtitle_parts = [
        listing.space_type.value.replace("_", " ").title(),
        _clean(listing.area),
        f"Up to {listing.capacity} people"
    ]
    subtitle = " • ".join(subtitle_parts)
    
    # Ratings and amenities
    rating_str = f"⭐ {listing.rating} ({listing.review_count})" if listing.rating else "No reviews"
    noise_str = f"🔊 {listing.noise_level.value.title()}"
    wifi_str = f"📶 {listing.wifi_mbps} Mbps"
    
    metadata_html = f"""
<div class="metadata-row">
<span>{rating_str}</span>
<span>{noise_str}</span>
<span>{wifi_str}</span>
</div>
    """
    
    amenities_html = '<div class="chip-container">'
    for am in listing.amenities:
        amenities_html += f'<span class="chip chip-amenity">{am.value.replace("_", " ").title()}</span>'
    amenities_html += '</div>'
    
    # Explanation with template badge
    explanation = _clean(item.explanation) if item.explanation else "Matches request."
    badge_html = '<span class="template-badge">Template</span>' if item.explanation_source == "template" else ''
    
    # Per-person price if applicable
    pp_price_html = ""
    if parsed and parsed.party_size:
        size = party_size_for(parsed)
        pp_price = budget_price(listing, size, BudgetBasis.PER_PERSON_PER_HOUR)
        pp_price_html = f"<div style='font-size: 0.9em; color: #6c757d; font-weight: 500;'>₹{pp_price:.0f} per person / hr</div>"
    
    # Missed constraints if alternative
    missed_html = ""
    if is_alternative and "missed" in item.facts:
        missed = [f"<code>{_clean(m)}</code>" for m in item.facts["missed"]]
        if missed:
            missed_html = f"<div style='margin-top: 12px; color: #842029; font-size: 0.95em;'><strong>Missed:</strong> {', '.join(missed)}</div>"
    
    # Put it all together
    card_html = textwrap.dedent(f"""
<div class="result-card">
{header_html}
<div style="font-size: 0.95em; color: #495057; margin-bottom: 4px; font-weight: 500;">{subtitle}</div>
{pp_price_html}
{metadata_html}
{amenities_html}
<div style="margin-top: 16px; line-height: 1.5; color: #212529;">
{explanation} {badge_html}
</div>
{missed_html}
</div>
    """)
    st.markdown(card_html.replace('\n', ''), unsafe_allow_html=True)



