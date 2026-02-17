"""
Geocoding Utility
"""
import requests
import logging
from typing import Optional, Tuple, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

def get_coordinates(address: str) -> Optional[Dict[str, float]]:
    """
    住所または場所名から緯度経度を取得する
    
    Args:
        address: 住所または場所名
        
    Returns:
        {"lat": float, "lng": float} または None
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY is not set. Skipping geocoding.")
        return None
        
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address,
            "key": settings.GOOGLE_MAPS_API_KEY,
            "language": "ja"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data["status"] == "OK" and data["results"]:
            location = data["results"][0]["geometry"]["location"]
            return {
                "lat": location["lat"],
                "lng": location["lng"]
            }
        else:
            logger.warning(f"Geocoding failed for '{address}': {data.get('status')}")
            return None
            
    except Exception as e:
        logger.error(f"Error during geocoding for '{address}': {str(e)}")
        return None
