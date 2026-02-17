"""
外部API連携（Yahoo! Open Local Platform、天気、Google Places（フォールバック））
"""
import os
import requests
import math
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# API使用回数管理をインポート
try:
    from app.utils.api_usage_tracker import record_api_call
    API_USAGE_TRACKING = True
except ImportError:
    API_USAGE_TRACKING = False

# Yahoo! Open Local Platform API
YAHOO_APP_ID = os.getenv("YAHOO_APP_ID")
YAHOO_CLIENT_ID = os.getenv("YAHOO_CLIENT_ID")
YAHOO_CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET")
AFFILIATE_YAHOO_TRAVEL = os.getenv("AFFILIATE_YAHOO_TRAVEL", "")

# 従来のAPI（フォールバック用）
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


def get_place_details(place_name: str, latitude: float = None, longitude: float = None) -> Optional[Dict[str, Any]]:
    """Yahoo!ローカルサーチAPIから店舗情報を取得"""
    # Yahoo! APIを優先使用
    if YAHOO_APP_ID:
        try:
            results = get_yahoo_local_search(place_name, latitude, longitude)
            if results and len(results) > 0:
                place = results[0]
                return {
                    "name": place.get("name", place_name),
                    "address": place.get("address", ""),
                    "phone": place.get("tel", ""),
                    "category": place.get("category", ""),
                    "latitude": place.get("latitude"),
                    "longitude": place.get("longitude"),
                }
        except Exception as e:
            print(f"Yahoo!ローカルサーチAPIエラー: {e}")
    
    # フォールバック: Google Places API（設定されている場合）
    if GOOGLE_PLACES_API_KEY and latitude and longitude:
        try:
            # Place Search
            search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
            params = {
                "input": place_name,
                "inputtype": "textquery",
                "locationbias": f"circle:1000@{latitude},{longitude}",
                "fields": "place_id",
                "key": GOOGLE_PLACES_API_KEY,
            }
            
            response = requests.get(search_url, params=params, timeout=5)
            data = response.json()
            
            if data.get("status") != "OK" or not data.get("candidates"):
                return None
            
            place_id = data["candidates"][0]["place_id"]
            
            # Place Details
            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                "place_id": place_id,
                "fields": "opening_hours,formatted_phone_number,website,rating,user_ratings_total",
                "key": GOOGLE_PLACES_API_KEY,
            }
            
            response = requests.get(details_url, params=params, timeout=5)
            data = response.json()
            
            if data.get("status") == "OK":
                result = data.get("result", {})
                return {
                    "opening_hours": result.get("opening_hours", {}).get("weekday_text", []),
                    "phone": result.get("formatted_phone_number"),
                    "website": result.get("website"),
                    "rating": result.get("rating"),
                    "reviews_count": result.get("user_ratings_total"),
                }
        except Exception as e:
            print(f"Google Places APIエラー: {e}")
    
    return None


def get_weather(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """天気情報を取得"""
    if not OPENWEATHER_API_KEY:
        return None
    
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "ja",
        }
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "temperature": data.get("main", {}).get("temp"),
                "description": data.get("weather", [{}])[0].get("description"),
                "icon": data.get("weather", [{}])[0].get("icon"),
                "humidity": data.get("main", {}).get("humidity"),
            }
    except Exception as e:
        print(f"Weather APIエラー: {e}")
    
    return None


def get_yahoo_local_search(query: str, latitude: float = None, longitude: float = None, radius: int = 2000) -> Optional[List[Dict[str, Any]]]:
    """Yahoo!ローカルサーチAPIで施設を検索"""
    if not YAHOO_APP_ID:
        return None
    
    success = False
    try:
        url = "https://map.yahooapis.jp/search/local/v1/LocalSearch"
        params = {
            "appid": YAHOO_APP_ID,
            "query": query,
            "results": 5,
            "output": "json",
        }
        
        if latitude and longitude:
            params["lat"] = latitude
            params["lon"] = longitude
            params["dist"] = radius
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data.get("ResultInfo", {}).get("Count", 0) > 0:
            features = data.get("Feature", [])
            results = []
            for feature in features:
                geometry = feature.get("Geometry", {})
                coordinates = geometry.get("Coordinates", "").split(",")
                if len(coordinates) >= 2:
                    results.append({
                        "name": feature.get("Name", ""),
                        "address": feature.get("Property", {}).get("Address", ""),
                        "latitude": float(coordinates[1]),
                        "longitude": float(coordinates[0]),
                        "tel": feature.get("Property", {}).get("Tel1", ""),
                        "category": feature.get("Property", {}).get("Genre", [{}])[0].get("Name", ""),
                    })
            success = True
            if API_USAGE_TRACKING:
                record_api_call("yahoo_local_search", "LocalSearch", success=True, metadata={"query": query, "results_count": len(results)})
            return results
    except Exception as e:
        print(f"Yahoo!ローカルサーチAPIエラー: {e}")
        if API_USAGE_TRACKING:
            record_api_call("yahoo_local_search", "LocalSearch", success=False, metadata={"error": str(e)})
    
    if API_USAGE_TRACKING and not success:
        record_api_call("yahoo_local_search", "LocalSearch", success=False)
    return None


def get_yahoo_geocode(address: str) -> Optional[Dict[str, Any]]:
    """Yahoo!ジオコーダーAPIで住所を緯度経度に変換"""
    if not YAHOO_APP_ID:
        return None
    
    success = False
    try:
        url = "https://map.yahooapis.jp/geocode/V1/geoCoder"
        params = {
            "appid": YAHOO_APP_ID,
            "query": address,
            "output": "json",
        }
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data.get("ResultInfo", {}).get("Count", 0) > 0:
            feature = data.get("Feature", [{}])[0]
            geometry = feature.get("Geometry", {})
            coordinates = geometry.get("Coordinates", "").split(",")
            if len(coordinates) >= 2:
                result = {
                    "latitude": float(coordinates[1]),
                    "longitude": float(coordinates[0]),
                    "address": feature.get("Property", {}).get("Address", ""),
                }
                success = True
                if API_USAGE_TRACKING:
                    record_api_call("yahoo_geocode", "geoCoder", success=True, metadata={"address": address})
                return result
    except Exception as e:
        print(f"Yahoo!ジオコーダーAPIエラー: {e}")
        if API_USAGE_TRACKING:
            record_api_call("yahoo_geocode", "geoCoder", success=False, metadata={"error": str(e)})
    
    if API_USAGE_TRACKING and not success:
        record_api_call("yahoo_geocode", "geoCoder", success=False)
    return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """2点間の距離を計算（ハーバーサイン公式）"""
    R = 6371  # 地球の半径（km）
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def estimate_travel_time(distance_km: float, mode: str) -> Dict[str, Any]:
    """距離から移動時間を推定"""
    # 移動手段ごとの平均速度（km/h）
    speeds = {
        "driving": 40,  # 車（市街地）
        "transit": 30,  # 公共交通機関
        "walking": 4,   # 徒歩
        "bicycling": 15  # 自転車
    }
    
    speed = speeds.get(mode, 40)
    hours = distance_km / speed
    minutes = int(hours * 60)
    
    if minutes < 60:
        duration_text = f"{minutes}分"
    else:
        h = minutes // 60
        m = minutes % 60
        duration_text = f"{h}時間{m}分" if m > 0 else f"{h}時間"
    
    return {
        "duration_seconds": int(minutes * 60),
        "duration_text": duration_text,
        "distance_meters": int(distance_km * 1000),
        "distance_text": f"{distance_km:.1f}km" if distance_km >= 1 else f"{int(distance_km * 1000)}m",
    }


def get_yahoo_directions(origin: tuple, destination: tuple, mode: str = "driving") -> Optional[Dict[str, Any]]:
    """Yahoo!マップを使用したルート情報取得（距離計算と時間推定）"""
    if not YAHOO_APP_ID:
        return None
    
    try:
        # 2点間の直線距離を計算
        distance_km = calculate_distance(origin[0], origin[1], destination[0], destination[1])
        
        # 移動時間を推定
        route_info = estimate_travel_time(distance_km, mode)
        
        # Yahoo!マップのルート検索URLを生成
        # Yahoo!マップでは直接ルート検索URLが提供されていないため、
        # 2点間の地図表示とナビゲーションリンクを生成
        origin_lat, origin_lon = origin[0], origin[1]
        dest_lat, dest_lon = destination[0], destination[1]
        
        # Yahoo!マップの地図表示URL（2点間を表示）
        maps_url = f"https://map.yahoo.co.jp/maps?lat={origin_lat}&lon={origin_lon}&zoom=12"
        
        # ナビゲーションリンク（Yahoo!カーナビ）
        nav_url = f"https://navi.yahoo.co.jp/route?lat1={origin_lat}&lon1={origin_lon}&lat2={dest_lat}&lon2={dest_lon}"
        
        route_info["maps_url"] = maps_url
        route_info["nav_url"] = nav_url
        route_info["distance_km"] = distance_km
        
        return route_info
    except Exception as e:
        print(f"Yahoo!ルート取得エラー: {e}")
    
    return None


def get_directions(origin: tuple, destination: tuple, mode: str = "driving") -> Optional[Dict[str, Any]]:
    """ルート検索（Yahoo! Open Local Platform使用）"""
    # Yahoo! APIを優先使用
    result = get_yahoo_directions(origin, destination, mode)
    if result:
        return result
    
    # フォールバック: Google Maps API（設定されている場合）
    if GOOGLE_MAPS_API_KEY:
        try:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": f"{origin[0]},{origin[1]}",
                "destination": f"{destination[0]},{destination[1]}",
                "mode": mode,
                "language": "ja",
                "key": GOOGLE_MAPS_API_KEY,
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data.get("status") == "OK" and data.get("routes"):
                route = data["routes"][0]["legs"][0]
                return {
                    "duration_seconds": route.get("duration", {}).get("value"),
                    "duration_text": route.get("duration", {}).get("text"),
                    "distance_meters": route.get("distance", {}).get("value"),
                    "distance_text": route.get("distance", {}).get("text"),
                }
        except Exception as e:
            print(f"Google Directions APIエラー: {e}")
    
    return None

