import streamlit as st
import html
import textwrap
from src import config
from src.schemas import ParsedQuery, ResultItem, BudgetBasis
from src.filters import budget_price, party_size_for

def _clean(text: str) -> str:
    """Escape HTML and collapse newlines so markdown doesn't break."""
    return html.escape(text.replace('\n', ' ').replace('\r', ''))

def render_message(text: str) -> None:
    st.markdown(f'<div class="message-box">{_clean(text)}</div>', unsafe_allow_html=True)

def render_parsed_query(parsed: ParsedQuery) -> None:
    st.markdown("### What I understood")
    
    html_str = '<div class="chip-container">'
    
    # Hard constraints
    if parsed.location:
        html_str += f'<span class="chip chip-hard">Area: {_clean(parsed.location)}</span>'
    if parsed.space_type:
        html_str += f'<span class="chip chip-hard">Type: {parsed.space_type.value}</span>'
    if parsed.party_size:
        html_str += f'<span class="chip chip-hard">People: {parsed.party_size}</span>'
    if parsed.date:
        html_str += f'<span class="chip chip-hard">Date: {parsed.date.isoformat()}</span>'
    if parsed.time_window:
        html_str += f'<span class="chip chip-hard">Time: {parsed.time_window.start} - {parsed.time_window.end}</span>'
    if parsed.budget:
        html_str += f'<span class="chip chip-hard">Budget: ₹{parsed.budget.amount} ({parsed.budget.basis.value})</span>'
        
    # Soft constraints
    if parsed.soft.quiet:
        html_str += '<span class="chip chip-soft">Quiet</span>'
    if parsed.soft.min_wifi == "fast":
        html_str += '<span class="chip chip-soft">Fast WiFi</span>'
    for am in parsed.soft.amenities:
        html_str += f'<span class="chip chip-soft">{am.value.replace("_", " ").title()}</span>'
        
    # Unmatched preferences
    if parsed.unmatched_preferences:
        for um in parsed.unmatched_preferences:
            html_str += f'<span class="chip chip-unmatched">{_clean(um)}</span>'
            
    html_str += '</div>'
    st.markdown(html_str, unsafe_allow_html=True)
    
    if parsed.unmatched_preferences:
        st.info("Note: The items in red couldn't be matched to standard amenities.")

def render_result_card(item: ResultItem, parsed: ParsedQuery | None, is_alternative: bool = False) -> None:
    if is_alternative:
        st.markdown(f'<div class="alt-banner">{config.UI_ALT_BANNER}</div>', unsafe_allow_html=True)
        
    listing = item.listing
    
    # Header: Rank Badge, Title, Rank (for alternatives if needed, but badge has rank)
    header_html = textwrap.dedent(f"""
<div class="result-card-header">
<div>
<span class="rank-badge">#{item.rank}</span>
<span class="card-title">{_clean(listing.name)}</span>
</div>
<div>
<strong>₹{listing.price_per_hour}</strong> / hr
</div>
</div>
    """)
    
    # Subtitle info: space type, area, capacity
    subtitle_parts = [
        listing.space_type.value.replace("_", " ").title(),
        _clean(listing.area),
        f"Up to {listing.capacity} people"
    ]
    subtitle = " | ".join(subtitle_parts)
    
    # Ratings and amenities
    rating_str = f"⭐ {listing.rating} ({listing.review_count} reviews)" if listing.rating else "No reviews"
    noise_str = f"🔊 {listing.noise_level.value.title()}"
    wifi_str = f"📶 {listing.wifi_mbps} Mbps"
    
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
        pp_price_html = f"<div style='font-size: 0.9em; color: #6c757d;'>₹{pp_price:.0f} per person / hr</div>"
    
    # Missed constraints if alternative
    missed_html = ""
    if is_alternative and "missed" in item.facts:
        missed = [f"<code>{_clean(m)}</code>" for m in item.facts["missed"]]
        if missed:
            missed_html = f"<div style='margin-top: 8px; color: #842029;'><strong>Missed:</strong> {', '.join(missed)}</div>"
    
    # Put it all together
    card_html = textwrap.dedent(f"""
<div class="result-card">
{header_html}
<div style="font-size: 0.9em; color: #6c757d; margin-bottom: 8px;">{subtitle}</div>
{pp_price_html}
<div style="margin-top: 8px; font-size: 0.9em;">
{rating_str} &nbsp;|&nbsp; {noise_str} &nbsp;|&nbsp; {wifi_str}
</div>
{amenities_html}
<div style="margin-top: 12px;">
{explanation} {badge_html}
</div>
{missed_html}
</div>
    """)
    st.markdown(card_html.replace('\n', ''), unsafe_allow_html=True)
