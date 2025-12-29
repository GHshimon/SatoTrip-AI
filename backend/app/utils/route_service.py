"""
ルート情報取得サービス
OSRM、Google Maps Directions APIなどを使用してルート情報を取得
"""
import requests
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings
from app.utils.error_handler import log_error


def get_route_from_osrm(
    coordinates: List[Tuple[float, float]],
    profile: str = "driving"
) -> Optional[Dict[str, Any]]:
    """
    OSRMを使用してルート情報を取得
    
    Args:
        coordinates: [(lat, lng), ...] の形式の座標リスト
        profile: ルーティングプロファイル（driving, walking, cycling）
    
    Returns:
        ルート情報（geometry, distance, duration）またはNone
    """
    if len(coordinates) < 2:
        return None
    
    try:
        # 座標を文字列に変換（lng,lat;lng,lat;...）
        coords_str = ";".join([f"{lng},{lat}" for lat, lng in coordinates])
        
        url = f"https://router.project-osrm.org/route/v1/{profile}/{coords_str}"
        params = {
            "overview": "full",
            "geometries": "geojson",
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                geometry = route.get("geometry", {}).get("coordinates", [])
                
                # [[lng, lat], ...] を [[lat, lng], ...] に変換
                route_coords = [[coord[1], coord[0]] for coord in geometry]
                
                # 距離と時間を計算
                distance = 0
                duration = 0
                if route.get("legs"):
                    for leg in route["legs"]:
                        distance += leg.get("distance", 0)
                        duration += leg.get("duration", 0)
                
                return {
                    "geometry": route_coords,
                    "distance_meters": distance,
                    "distance_km": distance / 1000,
                    "duration_seconds": duration,
                    "duration_minutes": duration / 60,
                    "source": "osrm"
                }
    except Exception as e:
        log_error("OSRM_ROUTE_ERROR", f"OSRMルート取得エラー: {str(e)}", {"coordinates_count": len(coordinates)})
    
    return None


def get_route_from_google_maps(
    origin: Tuple[float, float],
    destination: Tuple[float, float],
    waypoints: Optional[List[Tuple[float, float]]] = None,
    mode: str = "driving"
) -> Optional[Dict[str, Any]]:
    """
    Google Maps Directions APIを使用してルート情報を取得
    
    Args:
        origin: (lat, lng) の形式の出発地
        destination: (lat, lng) の形式の目的地
        waypoints: 経由地のリスト（オプション）
        mode: 移動手段（driving, walking, bicycling, transit）
    
    Returns:
        ルート情報（geometry, distance, duration）またはNone
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        return None
    
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "mode": mode,
            "language": "ja",
            "key": settings.GOOGLE_MAPS_API_KEY,
        }
        
        if waypoints:
            waypoints_str = "|".join([f"{lat},{lng}" for lat, lng in waypoints])
            params["waypoints"] = waypoints_str
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK" and data.get("routes"):
                route = data["routes"][0]["legs"][0]
                
                # ポリラインをデコード（簡易版、実際にはpolylineライブラリを使用）
                # ここでは簡易的に返す
                return {
                    "distance_meters": route.get("distance", {}).get("value", 0),
                    "distance_km": route.get("distance", {}).get("value", 0) / 1000,
                    "duration_seconds": route.get("duration", {}).get("value", 0),
                    "duration_minutes": route.get("duration", {}).get("value", 0) / 60,
                    "source": "google_maps"
                }
    except Exception as e:
        log_error("GOOGLE_MAPS_ROUTE_ERROR", f"Google Mapsルート取得エラー: {str(e)}")
    
    return None


def get_route_info(
    coordinates: List[Tuple[float, float]],
    profile: str = "driving"
) -> Optional[Dict[str, Any]]:
    """
    ルート情報を取得（OSRM優先、フォールバックでGoogle Maps）
    
    Args:
        coordinates: [(lat, lng), ...] の形式の座標リスト
        profile: ルーティングプロファイル
    
    Returns:
        ルート情報またはNone
    """
    # OSRMを優先
    route_info = get_route_from_osrm(coordinates, profile)
    if route_info:
        return route_info
    
    # フォールバック: Google Maps（2点間のみ）
    if len(coordinates) == 2 and settings.GOOGLE_MAPS_API_KEY:
        route_info = get_route_from_google_maps(coordinates[0], coordinates[1], mode=profile)
        if route_info:
            return route_info
    
    return None

