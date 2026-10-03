import streamlit as st
import folium
from streamlit_folium import st_folium
from src import config
from src.schemas import ResultItem

def render_map(results: list[ResultItem]) -> None:
    # Use default center if no results
    center = config.DEFAULT_MAP_CENTER
    zoom = 12
    if results:
        # Calculate average of all result coordinates
        avg_lat = sum(r.listing.lat for r in results) / len(results)
        avg_lng = sum(r.listing.lng for r in results) / len(results)
        center = (avg_lat, avg_lng)
        
        if len(results) == 1:
            zoom = 16
        else:
            lats = [r.listing.lat for r in results]
            lngs = [r.listing.lng for r in results]
            max_span = max(max(lats) - min(lats), max(lngs) - min(lngs))
            
            if max_span == 0:
                zoom = 16
            elif max_span < 0.02:
                zoom = 14
            elif max_span < 0.06:
                zoom = 13
            elif max_span < 0.15:
                zoom = 11
            else:
                zoom = 10
        
    m = folium.Map(location=center, zoom_start=zoom)
    
    if results:
        for item in results:
            lat, lng = item.listing.lat, item.listing.lng
            
            popup_text = f"<b>{item.listing.name}</b><br>₹{item.listing.price_per_hour}/hr"
            
            folium.Marker(
                [lat, lng],
                popup=popup_text,
                tooltip=item.listing.name,
                icon=folium.Icon(color="blue", icon=str(item.rank), prefix="fa")
            ).add_to(m)
            
    st_folium(m, use_container_width=True, height=500, returned_objects=[])
