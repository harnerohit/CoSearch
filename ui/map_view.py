import streamlit as st
import folium
from streamlit_folium import st_folium
from src import config
from src.schemas import ResultItem

def render_map(results: list[ResultItem]) -> None:
    # Use default center if no results
    center = config.DEFAULT_MAP_CENTER
    if results:
        # Calculate average of all result coordinates
        avg_lat = sum(r.listing.lat for r in results) / len(results)
        avg_lng = sum(r.listing.lng for r in results) / len(results)
        center = (avg_lat, avg_lng)
        
    m = folium.Map(location=center, zoom_start=12)
    
    if results:
        bounds = []
        for item in results:
            lat, lng = item.listing.lat, item.listing.lng
            bounds.append([lat, lng])
            
            popup_text = f"<b>{item.listing.name}</b><br>₹{item.listing.price_per_hour}/hr"
            
            folium.Marker(
                [lat, lng],
                popup=popup_text,
                tooltip=item.listing.name,
                icon=folium.Icon(color="blue", icon=str(item.rank), prefix="fa")
            ).add_to(m)
            
        if bounds:
            m.fit_bounds(bounds)
            
    st_folium(m, width=700, height=500, returned_objects=[])
